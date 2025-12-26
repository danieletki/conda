#!/bin/bash
# Final verification script for split filter fix

echo "=========================================="
echo "Final Verification - Split Filter Fix"
echo "=========================================="
echo ""

# Check 1: No split filter usage
echo "✓ Check 1: Scanning for invalid |split filter usage..."
if grep -r "|\s*split" templates/ 2>/dev/null; then
    echo "  ❌ FAIL: Found split filter usage"
    exit 1
else
    echo "  ✅ PASS: No split filter found"
fi
echo ""

# Check 2: Template syntax validation
echo "✓ Check 2: Running template validation..."
python3 validate_templates.py > /tmp/validation_output.txt 2>&1
if grep -q "ALL VALIDATION CHECKS PASSED" /tmp/validation_output.txt; then
    echo "  ✅ PASS: Template validation successful"
else
    echo "  ❌ FAIL: Template validation failed"
    cat /tmp/validation_output.txt
    exit 1
fi
echo ""

# Check 3: Verify fixed templates exist
echo "✓ Check 3: Verifying template files exist..."
if [ -f "templates/accounts/seller_dashboard.html" ] && [ -f "templates/accounts/seller_lottery_detail.html" ]; then
    echo "  ✅ PASS: All template files present"
else
    echo "  ❌ FAIL: Template files missing"
    exit 1
fi
echo ""

# Check 4: Check for correct warning class
echo "✓ Check 4: Verifying alert-warning class usage..."
if grep -q "alert alert-warning" templates/accounts/seller_dashboard.html && \
   grep -q "alert alert-warning" templates/accounts/seller_lottery_detail.html; then
    echo "  ✅ PASS: Correct alert-warning class found"
else
    echo "  ❌ FAIL: alert-warning class not found"
    exit 1
fi
echo ""

# Check 5: Documentation exists
echo "✓ Check 5: Verifying documentation files..."
if [ -f "TEMPLATE_SPLIT_FILTER_FIX.md" ] && [ -f "SPLIT_FILTER_FIX_SUMMARY.md" ]; then
    echo "  ✅ PASS: Documentation files present"
else
    echo "  ❌ FAIL: Documentation files missing"
    exit 1
fi
echo ""

echo "=========================================="
echo "✅ ALL VERIFICATION CHECKS PASSED"
echo "=========================================="
echo ""
echo "The split filter fix is complete and validated."
echo "Templates are ready for production use."
exit 0
