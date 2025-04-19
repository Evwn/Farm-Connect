# FarmConnect

FarmConnect is a web-based marketplace that connects farmers directly with buyers, facilitating the sale of agricultural products with secure escrow payment processing.

## Installation Guide

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Git (optional, for cloning the repository)

### Step-by-Step Installation

1. **Clone or download the repository**
   ```bash
   git clone https://github.com/Evwn/Farm-Connect
   cd farmconnect
   ```

2. **Create and activate a virtual environment**
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```
   DEBUG=True
   SECRET_KEY=your_secret_key_here
   DATABASE_URL=sqlite:///db.sqlite3
   
   # Payment Gateway Credentials
   PAYPAL_CLIENT_ID=your_paypal_client_id
   PAYPAL_CLIENT_SECRET=your_paypal_client_secret
   PAYSTACK_SECRET_KEY=your_paystack_secret_key
   SKRILL_MERCHANT_ID=your_skrill_merchant_id
   SKRILL_MERCHANT_EMAIL=your_skrill_merchant_email
   SKRILL_SECRET_WORD=your_skrill_secret_word
   ```

5. **Initialize the database**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a superuser (admin) account**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main application: http://localhost:8000
   - Admin interface: http://localhost:8000/admin

## User Roles and Functionalities

### Admin
- Manage user accounts (farmers and buyers)
- Monitor and manage all orders
- View and manage escrow transactions
- Resolve disputes between buyers and sellers
- Access detailed analytics and reports
- Manage product categories
- View and manage farm listings
- Monitor payment transactions

### Farmer (Seller)
- Create and manage farm profile
- Add and manage agricultural products
- Set product prices and stock quantities
- View and manage orders
- Update order status (Pending, Processing, Shipped, Completed)
- Release funds from escrow after order completion
- Respond to buyer disputes
- View sales history and analytics
- Manage farm location and details

### Buyer
- Browse available products
- View farm profiles and locations
- Place orders with secure escrow payment
- Choose payment methods (PayPal)
- Track order status
- Confirm order receipt (triggers 24-hour countdown for automatic fund release)
- File disputes if needed
- View order history
- Reorder previous purchases
- View payment status and history

## Key Features

- **Secure Escrow System**: Payments are held in escrow until order completion
- **Automated Fund Release**: Funds are automatically released after 24 hours of order confirmation
- **Multiple Payment Options**: Support for PayPal, Paystack, and Skrill
- **Dispute Resolution**: Built-in system for handling order disputes
- **Real-time Order Tracking**: Status updates and notifications
- **Farm Management**: Comprehensive tools for farmers to manage their products
- **Mobile Responsive**: Works seamlessly on all devices
