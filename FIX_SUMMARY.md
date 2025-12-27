# Fix: VariableDoesNotExist - total_commission Missing

## Problem
The payments dashboard view (`/payments/`) was throwing a `VariableDoesNotExist` error when trying to access the `total_commission` variable in the template `payments/dashboard.html`.

**Error Message:**
```
VariableDoesNotExist at /payments/
Failed lookup for key [total_commission]
```

## Root Cause
The template `payments/dashboard.html` uses Django template fallback chains:
- Line 29: `{{ total_revenue|default:total_paid|default:"0.00" }}`
- Line 49: `{{ total_platform_commission|default:total_commission|default:"0.00" }}`

However, the dashboard view in `mercato_payments/views.py` was not providing all required variables in the context:

**Admin Context (before fix):**
- ✓ `total_revenue`
- ✓ `total_paid`
- ✓ `total_platform_commission`
- ✗ `total_commission` - **MISSING**

**Non-Admin Context (before fix):**
- ✗ `total_revenue` - **MISSING**
- ✓ `total_paid`
- ✓ `total_platform_commission`
- ✗ `total_commission` - **MISSING**

## Solution
Added the missing context variables to both admin and non-admin contexts in the `dashboard()` function.

### Changes Made
**File:** `mercato_payments/views.py`

**Admin Context (lines 50-60):**
```python
context = {
    'total_revenue': total_revenue,
    'total_paid': total_revenue,
    'total_platform_commission': total_platform_commission,
    'total_commission': total_platform_commission,  # ← ADDED
    'transaction_count': all_transactions.count(),
    'recent_transactions': all_transactions.select_related(
        'ticket', 'ticket__lottery', 'ticket__buyer'
    ).order_by('-created_at')[:20],
    'is_admin_view': True
}
```

**Non-Admin Context (lines 62-70):**
```python
context = {
    'total_paid': total_paid,
    'total_revenue': total_paid,  # ← ADDED
    'total_platform_commission': total_commission,
    'total_commission': total_commission,  # ← ADDED
    'transaction_count': user_transactions.count(),
    'recent_transactions': recent_transactions,
    'is_admin_view': False
}
```

## Verification
All template variables are now provided in the context:

**Admin Context (after fix):**
- ✓ `total_revenue` - Total revenue from all transactions
- ✓ `total_paid` - Same as total_revenue for admin view
- ✓ `total_platform_commission` - Total commission collected by platform
- ✓ `total_commission` - Same as total_platform_commission (for template fallback)
- ✓ `transaction_count`
- ✓ `recent_transactions`
- ✓ `is_admin_view`

**Non-Admin Context (after fix):**
- ✓ `total_paid` - Total amount paid by this user
- ✓ `total_revenue` - Same as total_paid for non-admin view (for template fallback)
- ✓ `total_platform_commission` - Commission paid by this user
- ✓ `total_commission` - Same as total_platform_commission (for template fallback)
- ✓ `transaction_count`
- ✓ `recent_transactions`
- ✓ `is_admin_view`

## Testing
The fix can be verified by:
1. Accessing `/payments/` as an admin user - should load without errors
2. Accessing `/payments/` as a regular user - should load without errors
3. Checking that all statistics cards display correct values
4. No `VariableDoesNotExist` errors in logs

## Impact
- **Files Modified:** 1 file (`mercato_payments/views.py`)
- **Lines Changed:** 2 lines added (one in each context block)
- **Breaking Changes:** None
- **Backward Compatibility:** Fully compatible (only adds missing variables)
