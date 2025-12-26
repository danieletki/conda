#!/usr/bin/env python3
"""
Simple template validation - checks for invalid filter usage
"""
import re
from pathlib import Path

def check_template_for_split_filter(template_path):
    """Check if template contains invalid split filter usage"""
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check for |split usage
    split_pattern = r'\|\s*split'
    matches = re.findall(split_pattern, content)
    
    if matches:
        print(f"❌ {template_path}: Found {len(matches)} invalid |split filter(s)")
        # Show line numbers
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if re.search(split_pattern, line):
                print(f"   Line {i}: {line.strip()[:80]}")
        return False
    else:
        print(f"✅ {template_path}: No invalid split filters found")
        return True

def check_template_basic_syntax(template_path):
    """Check for basic template syntax issues"""
    with open(template_path, 'r') as f:
        content = f.read()
    
    issues = []
    
    # Check for unmatched {% %}
    open_tags = content.count('{%')
    close_tags = content.count('%}')
    if open_tags != close_tags:
        issues.append(f"Unmatched template tags: {open_tags} opening vs {close_tags} closing")
    
    # Check for unmatched {{ }}
    open_vars = content.count('{{')
    close_vars = content.count('}}')
    if open_vars != close_vars:
        issues.append(f"Unmatched variables: {open_vars} opening vs {close_vars} closing")
    
    if issues:
        print(f"⚠️  {template_path}: Potential syntax issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ {template_path}: Basic syntax check passed")
        return True

def main():
    print("=" * 70)
    print("Template Validation - Split Filter Fix")
    print("=" * 70)
    print()
    
    base_path = Path(__file__).parent
    templates = [
        base_path / 'templates/accounts/seller_dashboard.html',
        base_path / 'templates/accounts/seller_lottery_detail.html',
    ]
    
    all_valid = True
    
    print("1. Checking for invalid |split filter usage:")
    print("-" * 70)
    for template in templates:
        if not check_template_for_split_filter(template):
            all_valid = False
    
    print()
    print("2. Checking basic template syntax:")
    print("-" * 70)
    for template in templates:
        if not check_template_basic_syntax(template):
            all_valid = False
    
    print()
    print("=" * 70)
    if all_valid:
        print("✅ ALL VALIDATION CHECKS PASSED")
        print("=" * 70)
        print()
        print("Templates are ready for use. The TemplateSyntaxError should be resolved.")
        return 0
    else:
        print("❌ VALIDATION FAILED")
        print("=" * 70)
        print()
        print("Please fix the issues above before deploying.")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
