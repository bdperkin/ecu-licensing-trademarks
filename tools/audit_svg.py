#!/usr/bin/env python3

import os
import sys
import re
import argparse
from lxml import etree
from spellchecker import SpellChecker

DEFAULT_WORDLIST_NAMES = [
    "wordlist.txt",
    "wordlist",
    "words.txt",
    "ignore_words.txt",
    "audit_wordlist.txt",
]

def get_default_wordlist_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for name in DEFAULT_WORDLIST_NAMES:
        candidate = os.path.join(script_dir, name)
        if os.path.isfile(candidate):
            return candidate
    return None

def get_element_path(elem):
    path_parts = []
    curr = elem
    while curr is not None:
        # Use the 'id' attribute if present, otherwise fallback to the tag name
        identifier = curr.get('id')
        if not identifier:
            tag_name = curr.tag.split('}')[-1] if isinstance(curr.tag, str) else 'node'
            identifier = f"<{tag_name}>"
        path_parts.insert(0, identifier)
        curr = curr.getparent()
    return '/'.join(path_parts)

def load_wordlist(file_path):
    if not file_path:
        return set()
    ignore_words = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Split line into tokens
                raw_tokens = re.split(r'[\s_\-]+', line)
                for token in raw_tokens:
                    sub_tokens = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|\b)', token)
                    if sub_tokens:
                        ignore_words.update(t.lower() for t in sub_tokens if len(t) > 1)
                    elif len(token) > 1 and token.isalpha():
                        ignore_words.add(token.lower())
                for w in re.findall(r'\b[a-zA-Z]+\b', line.lower()):
                    if len(w) > 1:
                        ignore_words.add(w)
    except FileNotFoundError:
        print(f"Error: Word list file not found: '{file_path}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading word list file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    return ignore_words

def audit_inkscape_svg(file_path, wordlist_path=None):
    if wordlist_path is None:
        wordlist_path = get_default_wordlist_path()

    parser = etree.XMLParser(recover=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()

    spell = SpellChecker()
    ignore_words = load_wordlist(wordlist_path)
    if ignore_words:
        spell.word_frequency.load_words(ignore_words)

    # Find all group elements regardless of namespace prefix using local-name()
    groups = root.xpath('//*[local-name()="g"]')
    
    missing_label_count = 0
    labels = []
    label_paths = {}

    print("=== 1. Groups Missing 'inkscape:label' ===")
    for i, g in enumerate(groups):
        label_val = g.get('{http://www.inkscape.org/namespaces/inkscape}label')
        g_path = get_element_path(g)

        if not label_val:
            print(f"  - Path: {g_path}")
            missing_label_count += 1
        else:
            labels.append((label_val, g_path))
            if label_val not in label_paths:
                label_paths[label_val] = []
            label_paths[label_val].append(g_path)

    print(f"Total groups missing label: {missing_label_count}\n")

    print("=== 2. Duplicate Group Labels ===")
    duplicates_found = False
    for label, paths in label_paths.items():
        if len(paths) > 1:
            duplicates_found = True
            print(f"  - Label '{label}' is duplicated across paths:")
            for path in paths:
                print(f"    * {path}")
    if not duplicates_found:
        print("  - No duplicate labels found.\n")
    else:
        print()

    print("=== 3. Potential Spelling Errors in Labels ===")
    spelling_issues = False
    for label, g_path in labels:
        # Tokenize by whitespace, underscores, hyphens, and handle camelCase
        raw_tokens = re.split(r'[\s_\-]+', label)
        tokens = []
        for token in raw_tokens:
            sub_tokens = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|\b)', token)
            if sub_tokens:
                tokens.extend([t.lower() for t in sub_tokens if len(t) > 1])
            elif len(token) > 1 and token.isalpha():
                tokens.append(token.lower())

        misspelled = [w for w in spell.unknown(tokens) if w not in ignore_words]
        if misspelled:
            spelling_issues = True
            print(f"  - Label '{label}' at path '{g_path}' contains potential typos: {list(misspelled)}")

    if not spelling_issues:
        print("  - No spelling issues detected in labels.")

def main():
    parser = argparse.ArgumentParser(description="Audit Inkscape SVG files for missing labels, duplicate labels, and spelling errors.")
    parser.add_argument("svg_path", help="Path to the SVG file to audit")
    parser.add_argument("pos_wordlist", nargs="?", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "-w", "--wordlist", "-i", "--ignore-words", "--ignore-file", "--ignore",
        dest="wordlist_path",
        default=None,
        help="Path to a word list file containing strings/words to ignore during spell checking",
    )
    args = parser.parse_args()
    wordlist = args.wordlist_path or args.pos_wordlist
    audit_inkscape_svg(args.svg_path, wordlist)

if __name__ == '__main__':
    main()
