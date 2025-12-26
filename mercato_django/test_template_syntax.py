#!/usr/bin/env python3
"""
Template syntax validation script
Tests that modified templates can be parsed without syntax errors
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mercatopro.settings')
sys.path.insert(0, str(Path(__file__).parent))

try:
    django.setup()
except Exception as e:
    print(f"Warning: Could not setup Django fully: {e}")
    print("Attempting basic template syntax check...")

from django.template import Template, Context
from django.template.loader import get_template

def test_template_syntax(template_path):
    """Test if a template can be loaded and compiled"""
    try:
        template = get_template(template_path)
        print(f"✅ {template_path}: VALID")
        return True
    except Exception as e:
        print(f"❌ {template_path}: ERROR - {e}")
        return False

def main():
    print("=" * 60)
    print("Template Syntax Validation")
    print("=" * 60)
    print()
    
    templates_to_test = [
        'accounts/seller_dashboard.html',
        'accounts/seller_lottery_detail.html',
    ]
    
    all_valid = True
    for template_path in templates_to_test:
        if not test_template_syntax(template_path):
            all_valid = False
    
    print()
    print("=" * 60)
    if all_valid:
        print("✅ ALL TEMPLATES VALID")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TEMPLATES HAVE ERRORS")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
