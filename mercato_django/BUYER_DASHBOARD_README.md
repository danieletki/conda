# Buyer Dashboard - Documentation

## Overview
The buyer dashboard is the main hub for customers to manage their lottery ticket purchases, view statistics, and manage their profile.

## Features

### 1. Dashboard Main View
- **URL**: `/accounts/buyer/dashboard/`
- **View**: `buyer_dashboard` in `mercato_accounts/views.py`
- **Template**: `accounts/buyer_dashboard.html`

Features:
- User profile card with profile picture and key information
- Statistics section showing:
  - Total tickets purchased
  - Total won tickets
  - Total amount spent
- Filter buttons to view tickets by status:
  - **All**: All purchased tickets
  - **Active**: Lotteries currently running
  - **Expired**: Lotteries that have ended
  - **Won**: Tickets that won prizes
  - **Lost**: Tickets from lotteries where user didn't win
- Ticket cards with:
  - Lottery title and description
  - Ticket number
  - Purchase date and time
  - Paid amount
  - Prize value
  - Current status indicator
  - Progress bar for active lotteries
  - Link to lottery details

### 2. Profile Edit
- **URL**: `/accounts/buyer/profile/edit/`
- **View**: `buyer_profile_edit` in `mercato_accounts/views.py`
- **Template**: `accounts/buyer_profile_edit.html`
- **Form**: `ProfileForm` and `UserSettingsForm` in `mercato_accounts/forms.py`

Editable fields:
- Profile image
- Biography
- Email address
- Phone number
- Date of birth
- Full address (street, city, state, postal code, country)

### 3. Change Password
- **URL**: `/accounts/buyer/change-password/`
- **View**: `buyer_change_password` in `mercato_accounts/views.py`
- **Template**: `accounts/change_password.html`
- **Form**: `CustomPasswordChangeForm` in `mercato_accounts/forms.py`

Features:
- Secure password change form
- Validates current password
- Ensures new password is different from current
- Shows password requirements
- Session maintained after password change

## URL Routes

The following routes are available in `mercato_accounts/urls.py`:

```
/accounts/buyer/dashboard/          -> buyer_dashboard
/accounts/buyer/profile/edit/        -> buyer_profile_edit
/accounts/buyer/change-password/     -> buyer_change_password
```

## Data Models Used

### CustomUser
- User authentication and basic information
- Extended fields: phone_number, date_of_birth, is_verified

### Profile
- Additional user profile data
- Links one-to-one with CustomUser
- Stores: profile_image, bio, address information

### LotteryTicket
- Represents a purchased lottery ticket
- Links buyer (CustomUser) to a specific lottery
- Status tracking: pending, payment_processing, payment_failed, completed, refunded

### Lottery
- The lottery itself
- Contains: title, description, item_value, ticket_price, status, expiration_date

### Payment
- Payment records
- Used to calculate total amount spent

### WinnerDrawing
- Winner drawing records
- Used to determine if a ticket won

## Statistics Calculation

### Total Tickets
Counts all completed payments for the user:
```python
LotteryTicket.objects.filter(buyer=user, payment_status='completed').count()
```

### Won Tickets
Counts completed winner drawings where user is the winner:
```python
WinnerDrawing.objects.filter(winner=user, status='completed').count()
```

### Total Spent
Sums all completed payments:
```python
Payment.objects.filter(user=user, status='completed').aggregate(
    total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
)
```

## Filter Logic

### Active Lotteries
Lotteries with no expiration date (null) OR expiration_date in the future, with status 'active' or 'closed'

### Expired Lotteries
Lotteries with expiration_date in the past OR status 'completed'

### Won Tickets
Only tickets from winning drawings (via WinnerDrawing model)

### Lost Tickets
Completed lottery tickets that are NOT in the winning drawings

## Styling

- Responsive design using Bootstrap 5
- Custom CSS with gradient headers
- Stat cards with colored indicators
- Filter buttons with active state styling
- Ticket cards with left border indicator
- Status badges with color coding:
  - Green for Active
  - Red for Expired
  - Blue for Won
  - Gray for Lost

## Navigation Integration

The buyer dashboard is integrated into the main navigation:
- Added "Dashboard" link in user dropdown menu
- Added "Modifica Profilo" (Edit Profile) link
- Added "Cambia Password" (Change Password) link

## Security

- All views require `@login_required` decorator
- Profile edits are only possible for the authenticated user
- Password changes validate current password
- Session is maintained after password change using `update_session_auth_hash()`

## Future Enhancements

Possible future improvements:
- Export purchase history as PDF
- Email notifications for lottery results
- Favorite lotteries wishlist
- Advanced filtering and sorting
- Prize payout status tracking
- Account deletion option
- Two-factor authentication
