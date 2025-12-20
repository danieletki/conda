# Seller Dashboard - Documentation

## Overview
The seller dashboard is the comprehensive management hub for lottery creators to manage their lotteries, track sales performance, view detailed analytics, and handle financial reports.

## Features

### 1. Seller Dashboard Main View
- **URL**: `/accounts/seller/dashboard/`
- **View**: `seller_dashboard` in `mercato_accounts/views.py`
- **Template**: `accounts/seller_dashboard.html`

Features:
- KYC status verification with alert/warning if not verified
- Statistics overview showing:
  - Total lotteries published
  - Total tickets sold across all lotteries
  - Total earnings (net revenue after commission)
  - KYC approval status
- Lottery filter buttons:
  - **All**: Shows all lotteries created by seller
  - **Active**: Lotteries with 'active' status
  - **Archived**: Lotteries with 'closed', 'completed', 'drawn' status
  - **Won**: Lotteries that have been completed with winners
- Lottery cards displaying:
  - Lottery title and status badge
  - Main image with responsive sizing
  - Description preview (20 words)
  - Progress bar showing tickets sold/items count
  - Revenue earned and tickets sold count
  - Expiration date with conditional coloring
  - Link to detailed lottery analytics
- Recent sales activity table showing:
  - Last 5 ticket sales
  - Purchase date/time
  - Lottery title
  - Buyer username
  - Amount paid
  - Payment status
- "Create New Lottery" button in header

### 2. Create New Lottery
- **URL**: `/accounts/seller/lottery/create/`
- **View**: `seller_create_lottery` in `mercato_accounts/views.py`
- **Template**: `accounts/seller_create_lottery.html`
- **Form**: `LotteryCreationForm` in `mercato_lotteries/forms.py`

Features:
- KYC verification check - redirects to KYC settings if not verified
- Lottery creation form with fields:
  - Title (required)
  - Description (required, textarea)
  - Item value in EUR (required)
  - Number of tickets to sell (required)
  - Expiration date (optional, datetime-local input)
  - Image 1 (required, main image)
  - Image 2 (optional)
  - Image 3 (optional)
  - Description fields for each image
- Automatic ticket price calculation (item_value ÷ items_count)
- Image compression using custom `CompressedImageField`
- Form validation requiring at least one image
- Responsive form layout with Bootstrap styling
- Help text explaining commission structure (10% platform fee)
- After creation, lottery starts in 'draft' status

### 3. Lottery Detail Analytics
- **URL**: `/accounts/seller/lottery/<id>/`
- **View**: `seller_lottery_detail` in `mercato_accounts/views.py`
- **Template**: `accounts/seller_lottery_detail.html`

Features:
- Complete lottery overview:
  - Title, description, and status
  - Main image display
  - Item value, tickets total/sold, ticket price
  - Progress bar with percentage
  - Expiration date alert
- Financial summary:
  - Total revenue (gross) from tickets sold
  - Commission amount (10% of gross)
  - Net earnings after commission
- Sales analytics chart created with Chart.js:
  - Daily tickets sold over time
  - Daily revenue over time
  - Dual-axis line chart (tickets and EUR)
  - Interactive tooltips with data details
- Buyers list table showing:
  - Purchase date/time for each ticket
  - Anonymized buyer usernames
  - Ticket numbers (unique identifiers)
  - Amount paid
  - Payment status badges
- Winner information (if lottery has been drawn):
  - Winner profile display
  - Winning ticket number
  - Drawing date/time
- "Download Report" button for CSV export
- Responsive layout with card components

### 4. Financial Reports
- **URL**: `/accounts/seller/reports/`
- **View**: `seller_reports` in `mercato_accounts/views.py`
- **Template**: `accounts/seller_reports.html`

Features:
- Summary statistics cards:
  - Gross revenue (total across all lotteries)
  - Total commissions paid
  - Net earnings (after commission)
  - Total tickets sold
- Commission breakdown donut chart:
  - Visual representation of 90% seller / 10% commission split
  - Interactive tooltips with amounts and percentages
- Performance metrics list:
  - Number of lotteries with sales
  - Average tickets sold per lottery
  - Average earnings per lottery
  - Average conversion rate
- Detailed lottery breakdown table:
  - Lottery title with click to detail
  - Creation date
  - Status
  - Tickets sold
  - Gross revenue
  - Commission amount
  - Net revenue
  - Action button to view details
- CSV report download:
  - Generates downloadable CSV file
  - Filename includes username and date
  - Contains summary section
  - Detailed breakdown by lottery
  - Totals and calculations included
- Performance improvement tips section

### 5. KYC Settings
- **URL**: `/accounts/seller/kyc/settings/`
- **View**: `seller_kyc_settings` in `mercato_accounts/views.py`
- **Template**: `accounts/seller_kyc_settings.html`

Features:
- Current KYC status display:
  - Verified: Green success alert with checkmark
  - Pending: Yellow warning alert with clock icon
  - Visual status indicator with badges
- Document upload form (if not verified):
  - Document type selection (ID card, passport, driving license)
  - Front document image upload (required)
  - Back document image upload (optional)
  - Proof of address upload (required)
  - Selfie with document upload (required)
  - Form validation for required fields
- KYC benefits sidebar:
  - Create unlimited lotteries
  - Faster payouts
  - Buyer trust and credibility
  - Advanced statistics access
  - Priority support
- Processing time information (24-48 hours)
- Support contact button
- Document requirements list
- Responsive form layout with image upload preview

## URL Routes

The following routes are available in `mercato_accounts/urls.py`:

```
/accounts/seller/dashboard/          -> seller_dashboard
/accounts/seller/lottery/create/     -> seller_create_lottery
/accounts/seller/lottery/<id>/       -> seller_lottery_detail
/accounts/seller/reports/            -> seller_reports
/accounts/seller/kyc/settings/       -> seller_kyc_settings
```

## Data Models Used

### CustomUser
- User authentication and verification
- `is_verified` field for KYC status
- Related to lotteries, tickets, payments

### Profile
- Additional user information
- Profile image, bio, address
- One-to-one with CustomUser

### Lottery
- Core lottery model
- Fields: title, description, item_value, ticket_price, status, images
- **CompressedImageField** for optimized image storage
- Relationships with seller (CustomUser) and tickets
- Calculate ticket price automatically
- Status validation based on KYC completion

### LotteryTicket
- Individual ticket purchases
- Links buyers to lotteries
- Generate unique ticket numbers
- Track payment_status (pending, completed, refunded)

### PaymentTransaction
- Detailed payment tracking with commission calculation
- **10% commission rate** applied automatically
- Links to tickets and payment records
- Tracks PayPal transaction details
- Calculate net_amount after commission

### WinnerDrawing
- Lottery drawing results
- Links winners to lotteries and winning tickets
- Status tracking (pending, completed, cancelled)

## Statistics Calculations

### Total Lotteries Created
```python
request.user.lotteries_as_seller.count()
```

### Total Tickets Sold
Counts completed tickets across all seller's lotteries:
```python
LotteryTicket.objects.filter(
    lottery__seller=request.user,
    payment_status='completed'
).count()
```

### Total Earnings (Net)
Sums net amounts from all completed payment transactions:
```python
Payment.objects.filter(
    payment_transactions__ticket__in=completed_tickets,
    status='completed'
).aggregate(
    total_net=Coalesce(Sum('payment_transactions__net_amount'), 0)
)
```

### Per-Lottery Revenue
Annotates lotteries with ticket sales and revenue:
```python
Lottery.objects.filter(seller=request.user).annotate(
    tickets_sold=Count('tickets', filter=Q(tickets__payment_status='completed')),
    gross_revenue=Sum('tickets__lottery__ticket_price', 
                     filter=Q(tickets__payment_status='completed'))
)
```

## Image Handling

The system uses custom `CompressedImageField` to store images as compressed BLOBs in the database:
- **Automatic compression** using Pillow
- **JPEG format** with 85% quality
- **Max dimensions**: 1024x1024 pixels
- **Base64 encoding** for display in templates
- **No file system storage** required
- Images stored in `image_1`, `image_2`, `image_3` fields
- Descriptions stored in corresponding description fields

## Commission Structure

**Standard commission: 10% of gross revenue**

Calculation examples:
- Lottery with €1000 item value, 100 tickets = €10 per ticket
- If 80 tickets sold: €800 gross revenue
- Commission: €800 × 10% = €80
- Seller earnings: €800 - €80 = €720

Commission is automatically calculated in `PaymentTransaction.save()` method and applied to all lottery ticket sales.

## KYC Verification Flow

1. **User Registration**: User creates account, `is_verified=False`
2. **Document Upload**: Seller navigates to KYC settings
3. **Document Submission**: Upload required documents (ID, proof of address, selfie)
4. **Admin Review**: Admin reviews submitted documents (shows as "In attesa")
5. **Approval/Rejection**: Admin approves/rejects verification
6. **Status Update**: `is_verified` set to True, seller can create lotteries
7. **Email Notification**: Automated emails sent for approval/rejection

## CSV Report Format

Generated CSV includes:

**Summary Section:**
- Report generation date
- Total gross revenue
- Total commissions
- Net earnings
- Total tickets sold
- Total lotteries created

**Detail Section:**
- Lottery title
- Creation date
- Status
- Tickets sold
- Gross revenue
- Commission amount
- Net revenue

## Chart Visualizations

Implemented using Chart.js:

### Sales Chart (Lottery Detail)
- **Type**: Dual-axis line chart
- **Data**: Daily tickets sold and daily revenue
- **Interactive**: Tooltips with values
- **Responsive**: Adapts to screen size

### Commission Chart (Reports)
- **Type**: Doughnut chart
- **Data**: Seller earnings (90%) vs Commission (10%)
- **Color-coded**: Green for earnings, yellow for commission
- **Tooltips**: Amounts and percentages

## Navigation Integration

The seller dashboard is fully integrated into the main navigation:
- Smart detection based on `user.lotteries_as_seller.exists()`
- Shows "Dashboard Venditore" as primary for sellers
- Shows "Dashboard Acquirente" as primary for buyers
- Includes links to:
  - Seller Dashboard
  - Create Lottery  
  - Financial Reports
  - KYC Settings
  - Buyer Dashboard (switch view)
  - Profile management
- Consistent dropdown structure for all user types

## Security Features

- **@login_required** on all seller views
- **KYC verification check** before lottery creation
- **Ownership verification** for lottery details (404 if not seller's lottery)
- **Form validation** preventing invalid data
- **Image type validation** (only images accepted)
- **Secure file uploads** with proper MIME type checking

## Responsive Design

All templates are fully responsive using Bootstrap 5:
- **Mobile-first** design approach
- **Grid system** adapts to screen sizes
- **Cards stack** vertically on mobile
- **Tables become scrollable** on small screens
- **Charts resize** with container
- **Navigation collapses** to hamburger menu
- **Font sizes adjust** for readability

## Future Enhancements

Potential improvements for future versions:
- Advanced analytics with date range filtering
- Multiple commission tiers based on sales volume
- Batch lottery operations (activate, close multiple)
- Lottery templates for quick creation
- Automated KYC document scanning
- Withdrawal request system
- Seller rating and review system
- Advanced reporting with graphs and trends
- Lottery promotion tools
- Inventory management for physical items
- Shipping tracking integration
- Multi-language support for international sellers
