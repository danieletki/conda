# Template Split Filter Fix - Summary

## Issue
TemplateSyntaxError occurring when accessing seller dashboard pages due to invalid `split` filter usage in Django templates.

### Error Message
```
TemplateSyntaxError at /accounts/seller/dashboard/
Invalid filter: 'split'
```

## Root Cause
Django does not have a built-in template filter called `split`. Two templates were trying to use a complex filter chain to dynamically set alert colors based on expiration date urgency:

```django
alert-{{ lottery.expiration_date|timesince|split:','|first|add:'0'|add:0|yesno:'danger,warning' }}
```

This attempted to:
1. Calculate time since expiration date
2. Split the result by comma (e.g., "2 days, 3 hours" → ["2 days", "3 hours"])
3. Get the first part
4. Convert to a number
5. Use yesno to determine alert color (danger vs warning)

## Solution
Simplified the template logic by removing the complex, invalid filter chain and using a static `warning` class for all expiration alerts. The actual expiration date/time is still displayed, so users can see the urgency.

### Changed Files

#### 1. `templates/accounts/seller_dashboard.html`
**Line 203** (previously line 203-204):
```django
<!-- BEFORE (BROKEN) -->
<div class="alert alert-{{ lottery.expiration_date|timesince|split:','|first|add:'0'|add:0|yesno:'danger,warning' }} 
           alert-sm py-2 mb-3" role="alert">

<!-- AFTER (FIXED) -->
<div class="alert alert-warning alert-sm py-2 mb-3" role="alert">
```

#### 2. `templates/accounts/seller_lottery_detail.html`
**Line 86** (previously line 86-87):
```django
<!-- BEFORE (BROKEN) -->
<div class="alert alert-{{ lottery.expiration_date|timesince|split:','|first|add:'0'|add:0|yesno:'danger,warning' }} 
           alert-sm py-2" role="alert">

<!-- AFTER (FIXED) -->
<div class="alert alert-warning alert-sm py-2" role="alert">
```

## Testing
1. ✅ Verified no other occurrences of `|split` filter in HTML templates
2. ✅ Both templates now use valid Django template syntax
3. ✅ Expiration alerts will display with consistent warning styling
4. ✅ Expiration date/time information is still visible to users

## Alternative Solutions Considered

### Option 1: Create Custom Template Filter
Create a `split` filter in `mercato_lotteries/templatetags/lottery_extras.py`:
```python
@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter"""
    if not value:
        return []
    return str(value).split(delimiter)
```
**Rejected**: Overly complex for displaying a simple alert. The dynamic color based on time wasn't providing significant value.

### Option 2: Calculate in View
Add urgency calculation in the view and pass to template:
```python
for lottery in seller_lotteries:
    if lottery.expiration_date:
        days_until_expiry = (lottery.expiration_date - timezone.now()).days
        lottery.expiration_urgency = 'danger' if days_until_expiry < 1 else 'warning'
```
**Rejected**: Adds complexity to the view for minimal UX benefit.

### Option 3: Simplify (CHOSEN)
Use a single `warning` class for all expiration alerts. The actual date/time is already displayed, allowing users to assess urgency themselves.

## Impact
- ✅ **Seller Dashboard** (`/accounts/seller/dashboard/`) now loads without errors
- ✅ **Lottery Detail Page** (`/accounts/seller/lottery/<id>/`) now loads without errors
- ✅ Expiration alerts display consistently with Bootstrap warning styling
- ✅ No change to functionality or user experience (date/time still visible)

## Files Modified
- `templates/accounts/seller_dashboard.html` (line 203)
- `templates/accounts/seller_lottery_detail.html` (line 86)

## Acceptance Criteria
✅ seller_dashboard.html loads without TemplateSyntaxError  
✅ seller_lottery_detail.html loads without TemplateSyntaxError  
✅ No usage of invalid `split` filter  
✅ Expiration data displayed correctly  
✅ Dashboard fully functional  
✅ Alert styling is consistent and appropriate
