#!/usr/bin/env python3

import sys
import re
from lxml import etree
from spellchecker import SpellChecker

def audit_inkscape_svg(file_path):
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()

    spell = SpellChecker()

    # Find all group elements regardless of namespace prefix using local-name()
    groups = root.xpath('//*[local-name()="g"]')
    
    missing_label_count = 0
    labels = []
    label_elements = {}

    print("=== 1. Groups Missing 'inkscape:label' ===")
    for i, g in enumerate(groups):
        # Inkscape stores labels under the inkscape namespace attribute
        label_val = g.get('{http://www.inkscape.org/namespaces/inkscape}label')
        g_id = g.get('id', f'unnamed-group-{i}')

        if not label_val:
            print(f"  - Group ID: {g_id} (Index: {i}) lacks an inkscape:label")
            missing_label_count += 1
        else:
            labels.append((label_val, g_id))
            if label_val not in label_elements:
                label_elements[label_val] = []
            label_elements[label_val].append(g_id)

    print(f"Total groups missing label: {missing_label_count}\n")

    print("=== 2. Duplicate Group Labels ===")
    duplicates_found = False
    for label, g_ids in label_elements.items():
        if len(g_ids) > 1:
            duplicates_found = True
            print(f"  - Label '{label}' is duplicated across group IDs: {', '.join(g_ids)}")
    if not duplicates_found:
        print("  - No duplicate labels found.\n")
    else:
        print()

    print("=== 3. Potential Spelling Errors in Labels ===")
    spelling_issues = False
    for label, g_id in labels:
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
            print(f"  - Label '{label}' (Group ID: {g_id}) contains potential typos: {list(misspelled)}")

    if not spelling_issues:
        print("  - No spelling issues detected in labels.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python audit_svg.py <path_to_svg>")
        sys.exit(1)
    audit_inkscape_svg(sys.argv[1])
