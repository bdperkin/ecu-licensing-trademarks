#!/usr/bin/env python3

import sys
import re
from lxml import etree
from spellchecker import SpellChecker

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

def audit_inkscape_svg(file_path):
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()

    spell = SpellChecker()

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

        misspelled = spell.unknown(tokens)
        if misspelled:
            spelling_issues = True
            print(f"  - Label '{label}' at path '{g_path}' contains potential typos: {list(misspelled)}")

    if not spelling_issues:
        print("  - No spelling issues detected in labels.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python audit_svg.py <path_to_svg>")
        sys.exit(1)
    audit_inkscape_svg(sys.argv[1])
