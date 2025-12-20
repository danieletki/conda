# PayPal Payment Integration for Mercato Lotteries

This document explains how to set up and use the PayPal payment integration system for the Mercato lottery marketplace.

## Overview

The payment system includes:
- PayPal API integration with Sandbox support for development
- Automatic 10% commission calculation on all transactions
- Payment transaction tracking with complete audit trail
- IPN (Instant Payment Notification) webhook handling
- Automatic ticket status updates after payment confirmation
- Refund management for cancelled lotteries
- Comprehensive payment dashboard and reporting

## Getting Started

### Prerequisites

1. Python 3.8+ 
2. Django 6.0+
3. PayPal Business Account (for production)
4. PayPal Developer Account (for sandbox testing)

### Installation

1. Clone the repository
2. Install requirements:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Create superuser (if not already created):
```bash
python manage.py createsuperuser
```

## PayPal Configuration

### Step 1: Set up PayPal Developer Account

1. Go to [PayPal Developer Dashboard](https://developer.paypal.com/)
2. Log in or create a PayPal account
3. Navigate to "Dashboard" > "My Apps & Credentials"

### Step 2: Create PayPal App

1. Under "REST API apps", click "Create App"
2. Enter app name (e.g., "MercatoLotteries")
3. Select app type: "Merchant"
4. Click "Create App"

### Step 3: Configure Payment Settings

Two ways to configure PayPal settings:

#### Option A: Via Django Admin

1. Log in to Django admin panel
2. Navigate to: **PayPal Integrazione > Payment settings**
3. Click "Add Payment Settings"
4. Configure the following:
   - **PayPal Client ID**: Paste from PayPal App
   - **PayPal Client Secret**: Paste from PayPal App
   - **PayPal Sandbox Mode**: Enable for development
   - **Currency**: EUR (default)
   - **Processing Time Hours**: 24 (default)
   - **Auto Refund Enabled**: False (default)

#### Option B: Via Settings

Add to your Django settings:

```python
# PayPal Settings
PAYPAL_CLIENT_ID = 'your_client_id_here'
PAYPAL_CLIENT_SECRET = 'your_client_secret_here'
PAYPAL_SANDBOX_MODE = True  # Set to False for production
```

### Step 4: Configure IPN Webhook

The system automatically handles PayPal IPN webhooks. No additional configuration needed. The webhook endpoint is:

```
https://yourdomain.com/payments/paypal/ipn/
```

You can test webhooks using tools like ngrok for local development:

```bash
ngrok http 8000
```

## Features

### 1. User Payment Flow

1. **Initiate Payment**
   - User selects a lottery ticket to purchase
   - System shows payment summary with 10% commission
   - User clicks "Pay with PayPal" button

2. **PayPal Checkout**
   - User is redirected to PayPal checkout
   - Amount shows ticket price with commission breakdown
   - User completes payment with PayPal

3. **Payment Confirmation**
   - User returns to Mercato site after payment
   - System automatically captures payment via PayPal API
   - Ticket status updated to "completed"
   - Transaction record created with commission details

4. **Dashboard Update**
   - User sees transaction in payment dashboard
   - Real-time status updates via IPN webhooks
   - Email notification sent (if configured)

### 2. Commission Calculation

- **Commission Rate**: 10% of ticket price
- **Automatic Calculation**: Commission calculated during transaction creation
- **Transparent Display**: Users see breakdown before payment
- **Net Amount**: Seller receives ticket price minus commission

Example for a €10 ticket:
- Ticket Price: €10.00
- Commission (10%): -€1.00
- PayPal Fee: -€0.35 (approximate)
- Net Amount: €8.65

### 3. Payment Dashboard

The payment dashboard provides:
- Transaction history with filters
- Status overview (pending, completed, refunded, failed)
- Revenue reports (admin view)
- Commission reports (admin view)
- Export functionality (CSV)

### 4. Automatic Ticket Updates

When payment is completed:
- Ticket `payment_status` changes to "completed"
- Lottery ticket inventory decreases
- Buyer receives confirmation
- Lottery progress updated

### 5. Refund Management

For cancelled lotteries or refund requests:
- Admin can process refunds via dashboard
- Full or partial refunds supported
- PayPal API handles refund processing
- Ticket status updated to "refunded"
- Transaction record marked as refunded

## Testing with PayPal Sandbox

### Creating Sandbox Accounts

1. In PayPal Developer Dashboard, go to "Sandbox > Accounts"
2. Create two sandbox accounts:
   - **Merchant Account** (for receiving payments)
   - **Buyer Account** (for making test payments)

### Running Tests

1. Start Django development server:
```bash
python manage.py runserver
```

2. Configure your settings with sandbox credentials
3. Create test lottery tickets
4. Complete test payments using sandbox buyer account

### Test Scenarios

1. **Successful Payment**: Complete transaction and verify commission calculation
2. **Cancelled Payment**: Test cancel flow and status updates
3. **Failed Payment**: Simulate payment failure handling
4. **Refund**: Test refund processing and ticket status
5. **IPN Webhook**: Verify webhook processing with ngrok

## API Endpoints

### User Endpoints

- `GET /payments/` - Payment dashboard
- `GET /payments/history/` - Payment history
- `GET /payments/transaction/<id>/` - Transaction details
- `GET /payments/process/<ticket_id>/` - Payment checkout page

### ajax endpoints

- `POST /payments/paypal/create-order/` - Create PayPal order
- `POST /payments/paypal/capture-order/` - Capture payment
- `GET /payments/paypal/success/<ticket_id>/` - Success handler
- `GET /payments/paypal/cancel/<ticket_id>/` - Cancel handler

### Webhook endpoint

- `POST /payments/paypal/ipn/` - PayPal IPN webhook (no authentication required)

## Security

- CSRF protection on all payment endpoints
- PayPal API authentication with OAuth 2.0
- Webhook signature verification (recommended)
- Payment amount validation
- User authorization checks
- Transaction status verification

## Troubleshooting

### Common Issues

1. **"PayPal settings not configured"**
   - Solution: Add PayPal credentials to Django admin or settings

2. **"Failed to create PayPal order"**
   - Check PayPal API credentials
   - Verify sandbox mode setting
   - Check ticket price is valid

3. **IPN not received**
   - Check webhook URL is publicly accessible
   - Use ngrok for local development testing
   - Verify PayPal sandbox settings

4. **Database errors**
   - Run migrations: `python manage.py migrate`
   - Check database connection settings

## Support

For issues or questions:
- Review logs in `logs/paypal.log`
- Check PayPal API status
- Verify webhook delivery in PayPal dashboard
- Test with sandbox first before production

---
## License

This payment integration is part of the Mercato lottery platform.