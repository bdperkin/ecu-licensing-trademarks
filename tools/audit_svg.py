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

DEFAULT_DUPLICATES_LIST_NAMES = [
    "duplicates.txt",
    "duplicate_labels.txt",
    "ignore_duplicates.txt",
    "duplicates_ignore.txt",
    "duplicates",
    "duplicate_wordlist.txt",
]

def get_default_wordlist_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for name in DEFAULT_WORDLIST_NAMES:
        candidate = os.path.join(script_dir, name)
        if os.path.isfile(candidate):
            return candidate
    return None

def get_default_duplicates_list_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for name in DEFAULT_DUPLICATES_LIST_NAMES:
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
        return set(), []
    ignore_words = set()
    raw_word_entries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line not in raw_word_entries:
                    raw_word_entries.append(line)
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
    return ignore_words, raw_word_entries

def load_duplicates_list(file_path):
    if not file_path:
        return []
    ignore_duplicates = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line not in ignore_duplicates:
                    ignore_duplicates.append(line)
    except FileNotFoundError:
        print(f"Error: Duplicates list file not found: '{file_path}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading duplicates list file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    return ignore_duplicates

VALID_CHECKS = {
    'missing': {'missing', 'missing-labels', 'missing_labels', 'missing-label', 'missing_label', '1'},
    'duplicates': {'duplicate', 'duplicates', 'duplicate-labels', 'duplicate_labels', 'duplicate-label', 'duplicate_label', '2'},
    'spelling': {'spelling', 'spell', 'spellcheck', 'spell-check', 'spelling-errors', 'spelling_errors', 'typos', '3'},
    'empty': {'empty', 'empty-groups', 'empty_groups', 'empty-group', 'empty_group', 'zero', 'zero-objects', 'zero_objects', '4'},
    'single': {'single', 'single-object', 'single_object', 'single-objects', 'single_objects', 'single-child', 'single_child', 'single-child-groups', 'single-item', 'single_item', 'single-group', 'single_group', 'single-object-groups', '5'},
}
ALL_CHECKS = {'missing', 'duplicates', 'spelling', 'empty', 'single'}

def normalize_checks(checks):
    if checks is None:
        return set(ALL_CHECKS)
    if isinstance(checks, str):
        checks = [c.strip() for c in checks.replace(',', ' ').split() if c.strip()]
    selected = set()
    for raw in checks:
        if isinstance(raw, str) and ',' in raw:
            sub_items = [c.strip() for c in raw.split(',') if c.strip()]
        else:
            sub_items = [raw]
        for item in sub_items:
            key = str(item).lower().strip()
            if key == 'all':
                return set(ALL_CHECKS)
            found = False
            for canonical, aliases in VALID_CHECKS.items():
                if key == canonical or key in aliases:
                    selected.add(canonical)
                    found = True
                    break
            if not found:
                raise ValueError(
                    f"Unknown check: '{item}'. Valid options are: missing, duplicates, spelling, empty, single, all"
                )
    return selected if selected else set(ALL_CHECKS)

def is_single_alnum_label(label):
    if not label:
        return False
    s = label.strip()
    return len(s) == 1 and s.isalnum()

def audit_inkscape_svg(file_path, wordlist_path=None, duplicates_list_path=None, checks=None, show_stats=False, strict_duplicates=False):
    try:
        active_checks = normalize_checks(checks)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if wordlist_path is None and ("spelling" in active_checks or show_stats):
        wordlist_path = get_default_wordlist_path()

    if strict_duplicates:
        ignore_duplicate_names = []
    else:
        if duplicates_list_path is None and ("duplicates" in active_checks or show_stats):
            duplicates_list_path = get_default_duplicates_list_path()
        ignore_duplicate_names = load_duplicates_list(duplicates_list_path) if ("duplicates" in active_checks or show_stats) else []

    parser = etree.XMLParser(recover=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()

    # Find all group elements outside <defs> regardless of namespace prefix using local-name()
    groups = root.xpath('//*[local-name()="g"][not(ancestor::*[local-name()="defs"])]')
    
    missing_paths = []
    labels = []
    label_paths = {}
    empty_groups = []
    single_object_groups = []

    for g in groups:
        label_val = g.get('{http://www.inkscape.org/namespaces/inkscape}label')
        g_path = get_element_path(g)
        children = [c for c in g if isinstance(c.tag, str)]

        if not label_val:
            missing_paths.append(g_path)
        else:
            labels.append((label_val, g_path))
            if label_val not in label_paths:
                label_paths[label_val] = []
            label_paths[label_val].append(g_path)

        if len(children) == 0:
            if not is_single_alnum_label(label_val):
                empty_groups.append((g_path, label_val))
        elif len(children) == 1:
            if not is_single_alnum_label(label_val):
                child = children[0]
                child_tag = child.tag.split('}')[-1] if isinstance(child.tag, str) else 'node'
                child_id = child.get('id')
                child_label = child.get('{http://www.inkscape.org/namespaces/inkscape}label')
                child_desc_parts = [f"<{child_tag}"]
                if child_id:
                    child_desc_parts.append(f"id='{child_id}'")
                if child_label:
                    child_desc_parts.append(f"label='{child_label}'")
                child_desc = ' '.join(child_desc_parts) + '>'
                single_object_groups.append((g_path, label_val, child_desc))

    if "missing" in active_checks:
        print("=== 1. Groups Missing 'inkscape:label' ===")
        if missing_paths:
            for path in missing_paths:
                print(f"  - Path: {path}")
            print(f"Total groups missing label: {len(missing_paths)}\n")
        else:
            print("  - No groups missing labels found.\n")

    ignore_duplicate_set = set(ignore_duplicate_names)
    all_duplicate_labels = {lbl: paths for lbl, paths in label_paths.items() if len(paths) > 1}
    reported_duplicate_labels = {lbl: paths for lbl, paths in all_duplicate_labels.items() if lbl not in ignore_duplicate_set}
    reported_duplicate_groups_count = sum(len(paths) for paths in reported_duplicate_labels.values())
    unused_duplicate_names = [lbl for lbl in ignore_duplicate_names if lbl not in label_paths]

    if "duplicates" in active_checks:
        header = "=== 2. Duplicate Group Labels ==="
        if strict_duplicates:
            header = "=== 2. Duplicate Group Labels (Strict Mode) ==="
        print(header)
        if reported_duplicate_labels:
            for label, paths in reported_duplicate_labels.items():
                print(f"  - Label '{label}' ({len(paths)} occurrences) is duplicated across paths:")
                for path in paths:
                    print(f"    * {path}")
        else:
            print("  - No duplicate labels found.")

        if unused_duplicate_names and not strict_duplicates:
            print(f"  - Unused ignore duplicates ({len(unused_duplicate_names)} entries not found in SVG - flagged for removal):")
            for lbl in unused_duplicate_names:
                print(f"    * '{lbl}'")
        print()

    spelling_error_labels_count = 0
    unique_typos = set()
    ignore_words = set()
    raw_word_entries = []
    unused_ignore_words = []

    if "spelling" in active_checks or show_stats:
        ignore_words, raw_word_entries = load_wordlist(wordlist_path)
        all_svg_tokens = set()
        for label, g_path in labels:
            raw_tokens = re.split(r'[\s_\-]+', label)
            for token in raw_tokens:
                sub_tokens = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|\b)', token)
                if sub_tokens:
                    all_svg_tokens.update(t.lower() for t in sub_tokens if len(t) > 1)
                elif len(token) > 1 and token.isalpha():
                    all_svg_tokens.add(token.lower())
            for w in re.findall(r'\b[a-zA-Z]+\b', label.lower()):
                if len(w) > 1:
                    all_svg_tokens.add(w)

        for w_entry in raw_word_entries:
            tokens = [t.lower() for t in re.findall(r'[A-Za-z]+', w_entry) if len(t) > 1]
            if not any(t in all_svg_tokens for t in tokens) and w_entry.lower() not in all_svg_tokens:
                unused_ignore_words.append(w_entry)

    if "spelling" in active_checks:
        spell = SpellChecker()
        if ignore_words:
            spell.word_frequency.load_words(ignore_words)

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
                spelling_error_labels_count += 1
                unique_typos.update(misspelled)
                print(f"  - Label '{label}' at path '{g_path}' contains potential typos: {list(misspelled)}")

        if not spelling_issues:
            print("  - No spelling issues detected in labels.")

        if unused_ignore_words:
            print(f"  - Unused ignore words ({len(unused_ignore_words)} entries not found in SVG - flagged for removal):")
            for w_entry in unused_ignore_words:
                print(f"    * '{w_entry}'")
        print()

    if "empty" in active_checks:
        print("=== 4. Empty Groups (0 Objects) ===")
        if empty_groups:
            for path, label in empty_groups:
                if label:
                    print(f"  - Path: {path} (label: '{label}')")
                else:
                    print(f"  - Path: {path}")
            print(f"Total empty groups: {len(empty_groups)}\n")
        else:
            print("  - No empty groups found.\n")

    if "single" in active_checks:
        print("=== 5. Single-Object Groups (1 Object) ===")
        if single_object_groups:
            for path, label, child_desc in single_object_groups:
                if label:
                    print(f"  - Path: {path} (label: '{label}', child: {child_desc})")
                else:
                    print(f"  - Path: {path} (child: {child_desc})")
            print(f"Total single-object groups: {len(single_object_groups)}\n")
        else:
            print("  - No single-object groups found.\n")

    if show_stats:
        print("=== Audit Statistics ===")
        print(f"  - Total <g> elements: {len(groups)}")
        print(f"  - Groups with labels: {len(labels)}")
        if "missing" in active_checks:
            print(f"  - Groups missing labels: {len(missing_paths)}")
        if "duplicates" in active_checks:
            print(f"  - Unique label names: {len(label_paths)}")
            print(f"  - Duplicate label names: {len(reported_duplicate_labels)} (spanning {reported_duplicate_groups_count} groups)")
            if strict_duplicates:
                print(f"  - Duplicate ignore list: Disabled (strict mode)")
            elif ignore_duplicate_names:
                print(f"  - Ignored duplicate names loaded: {len(ignore_duplicate_names)}")
                print(f"  - Unused ignored duplicate names: {len(unused_duplicate_names)}")
        if "spelling" in active_checks:
            print(f"  - Labels with potential typos: {spelling_error_labels_count} ({len(unique_typos)} unique typo words)")
            if raw_word_entries:
                print(f"  - Ignored words loaded: {len(raw_word_entries)}")
                print(f"  - Unused ignored words: {len(unused_ignore_words)}")
        if "empty" in active_checks:
            print(f"  - Empty groups (0 objects): {len(empty_groups)}")
        if "single" in active_checks:
            print(f"  - Single-object groups (1 object): {len(single_object_groups)}")

def main():
    parser = argparse.ArgumentParser(description="Audit Inkscape SVG files for missing labels, duplicate labels, spelling errors, empty groups, and single-object groups.")
    parser.add_argument("svg_path", help="Path to the SVG file to audit")
    parser.add_argument("pos_wordlist", nargs="?", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "-w", "--wordlist", "-i", "--ignore-words", "--ignore-file", "--ignore",
        dest="wordlist_path",
        default=None,
        help="Path to a word list file containing strings/words to ignore during spell checking",
    )
    parser.add_argument(
        "-d", "--duplicates-list", "--ignore-duplicates", "--ignore-duplicate-labels", "--duplicates-file",
        dest="duplicates_list_path",
        default=None,
        help="Path to a file containing duplicate label names to ignore",
    )
    parser.add_argument(
        "--strict-duplicates", "--strict", "--strict-dups", "--no-ignore-duplicates",
        dest="strict_duplicates",
        action="store_true",
        help="Run duplicate checks in strict mode (do not ignore any duplicate labels)",
    )
    parser.add_argument(
        "-c", "--checks", "--check",
        dest="checks",
        nargs="+",
        default=None,
        metavar="CHECK",
        help="Checks to run: 'missing' (1), 'duplicates' (2), 'spelling' (3), 'empty' (4), 'single' (5), 'all' (default: all)",
    )
    parser.add_argument(
        "--missing", "--check-missing",
        dest="check_missing",
        action="store_true",
        help="Run check for groups missing labels",
    )
    parser.add_argument(
        "--duplicates", "--duplicate", "--check-duplicates",
        dest="check_duplicates",
        action="store_true",
        help="Run check for duplicate group labels",
    )
    parser.add_argument(
        "--spelling", "--spell", "--check-spelling",
        dest="check_spelling",
        action="store_true",
        help="Run check for potential spelling errors in labels",
    )
    parser.add_argument(
        "--empty", "--check-empty", "--empty-groups", "--check-empty-groups",
        dest="check_empty",
        action="store_true",
        help="Run check for empty groups (0 objects)",
    )
    parser.add_argument(
        "--single", "--check-single", "--single-object", "--check-single-object", "--single-child", "--check-single-child",
        dest="check_single",
        action="store_true",
        help="Run check for single-object groups (1 object)",
    )
    parser.add_argument(
        "-s", "--stats", "--statistics", "--summary",
        dest="show_stats",
        action="store_true",
        help="Report summary statistics at the end of the run",
    )
    args = parser.parse_args()

    selected_checks = []
    if args.checks:
        selected_checks.extend(args.checks)
    if args.check_missing:
        selected_checks.append("missing")
    if args.check_duplicates:
        selected_checks.append("duplicates")
    if args.check_spelling:
        selected_checks.append("spelling")
    if args.check_empty:
        selected_checks.append("empty")
    if args.check_single:
        selected_checks.append("single")

    checks = selected_checks if selected_checks else None
    wordlist = args.wordlist_path or args.pos_wordlist
    audit_inkscape_svg(
        args.svg_path,
        wordlist_path=wordlist,
        duplicates_list_path=args.duplicates_list_path,
        checks=checks,
        show_stats=args.show_stats,
        strict_duplicates=args.strict_duplicates,
    )

if __name__ == '__main__':
    main()
