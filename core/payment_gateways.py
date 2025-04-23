import paypalrestsdk
import requests
import json
import hashlib
import hmac
import time
import base64
from django.conf import settings
from django.urls import reverse
import paystack
import logging
import os

logger = logging.getLogger(__name__)

# PayPal Integration
class PayPalGateway:
    def __init__(self):
        self.client_id = os.environ.get('PAYPAL_CLIENT_ID')
        self.client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')
        self.mode = os.environ.get('PAYPAL_MODE', 'sandbox')
        self.api_url = 'https://api.sandbox.paypal.com'
        self.site_url = os.environ.get('SITE_URL', 'http://localhost:8000')
        self.logger = logging.getLogger(__name__)
        logger.info(f"Initialized PayPal gateway in sandbox mode")
    
    def get_access_token(self):
        try:
            auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            headers = {
                'Authorization': f'Basic {auth}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            data = {'grant_type': 'client_credentials'}
            
            self.logger.info(f"Requesting PayPal access token from {self.api_url}/v1/oauth2/token")
            response = requests.post(f"{self.api_url}/v1/oauth2/token", headers=headers, data=data)
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting PayPal access token: {str(e)}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Response text: {e.response.text}")
            raise
    
    def create_payment(self, order, return_url=None, cancel_url=None):
        """Create a PayPal payment"""
        access_token = self.get_access_token()
        url = f"{self.api_url}/v2/checkout/orders"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        # Generate return and cancel URLs if not provided
        if not return_url:
            return_url = f"{self.site_url}/paypal/success/{order.id}/"
        if not cancel_url:
            cancel_url = f"{self.site_url}/paypal/cancel/{order.id}/"
        
        # Prepare payment data
        payment_data = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': str(order.id),
                'description': f'Order #{order.id} - {order.product.name}',
                'custom_id': str(order.id),
                'amount': {
                    'currency_code': 'USD',
                    'value': str(order.total_price)
                }
            }],
            'application_context': {
                'return_url': return_url,
                'cancel_url': cancel_url,
                'brand_name': 'FarmConnect',
                'landing_page': 'LOGIN',
                'user_action': 'PAY_NOW',
                'shipping_preference': 'NO_SHIPPING'
            }
        }
        
        try:
            logger.info(f"Creating PayPal payment for order {order.id}")
            logger.info(f"Return URL: {return_url}")
            logger.info(f"Cancel URL: {cancel_url}")
            response = requests.post(url, headers=headers, json=payment_data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"PayPal payment creation response: {result}")
            
            if result.get('status') == 'CREATED':
                # Get the approval URL from the response
                approval_url = next(link['href'] for link in result['links'] if link['rel'] == 'approve')
                logger.info(f"Payment created successfully. Approval URL: {approval_url}")
                return {
                    'success': True,
                    'payment_id': result['id'],
                    'approval_url': approval_url
                }
            else:
                logger.error(f"PayPal payment creation failed. Status: {result.get('status')}")
                return {
                    'success': False,
                    'error': f"Payment creation failed. Status: {result.get('status')}"
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal payment creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_payment(self, order_id):
        """Execute a PayPal payment"""
        access_token = self.get_access_token()
        url = f"{self.api_url}/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        try:
            logger.info(f"Executing PayPal payment for order {order_id}")
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            logger.info(f"PayPal payment execution response: {result}")
            
            if result.get('status') == 'COMPLETED':
                # Get the transaction ID from the first capture
                transaction_id = result['purchase_units'][0]['payments']['captures'][0]['id']
                logger.info(f"Payment completed successfully. Transaction ID: {transaction_id}")
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'status': result['status'],
                    'order_id': order_id
                }
            else:
                logger.error(f"PayPal payment not completed. Status: {result.get('status')}")
                return {
                    'success': False,
                    'error': f"Payment status: {result.get('status')}",
                    'order_id': order_id
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal payment execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id
            }

# Paystack Integration
class PaystackGateway:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
    
    def create_transaction(self, order, callback_url):
        """Create a Paystack transaction for an order"""
        try:
            url = "https://api.paystack.co/transaction/initialize"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            data = {
                'email': order.buyer.email,
                'amount': int(order.total_price * 100),  # Convert to cents
                'reference': f"ORDER-{order.id}-{int(time.time())}",
                'callback_url': callback_url,
                'metadata': {
                    'order_id': order.id,
                    'escrow_id': str(order.escrow_id)
                }
            }
            
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                if result['status']:
                    return {
                        'success': True,
                        'reference': result['data']['reference'],
                        'authorization_url': result['data']['authorization_url']
                    }
            
            return {
                'success': False,
                'error': response.text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_transaction(self, reference):
        """Verify a Paystack transaction"""
        try:
            url = f"https://api.paystack.co/transaction/verify/{reference}"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if result['status'] and result['data']['status'] == 'success':
                    return {
                        'success': True,
                        'transaction_id': result['data']['id'],
                        'status': result['data']['status']
                    }
            
            return {
                'success': False,
                'error': response.text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Skrill Integration
class SkrillGateway:
    def __init__(self):
        self.merchant_id = settings.SKRILL_MERCHANT_ID
        self.merchant_email = settings.SKRILL_MERCHANT_EMAIL
        self.secret_word = settings.SKRILL_SECRET_WORD
        self.api_url = "https://pay.skrill.com"
    
    def create_payment(self, order):
        """Create a Skrill payment for an order"""
        # Prepare payment data
        payment_data = {
            "pay_to_email": self.merchant_email,
            "transaction_id": f"ORDER-{order.id}-{int(time.time())}",
            "return_url": f"{settings.SITE_URL}{reverse('order_detail', kwargs={'order_id': order.id})}",
            "cancel_url": f"{settings.SITE_URL}{reverse('order_detail', kwargs={'order_id': order.id})}",
            "status_url": f"{settings.SITE_URL}{reverse('skrill_status')}",
            "language": "EN",
            "amount": str(order.total_price),
            "currency": "USD",
            "detail1_description": "Order ID",
            "detail1_text": str(order.id),
            "detail2_description": "Product",
            "detail2_text": f"{order.quantity}kg of {order.product.name}",
            "detail3_description": "Escrow ID",
            "detail3_text": str(order.escrow_id),
            "merchant_fields": "order_id,escrow_id",
            "order_id": str(order.id),
            "escrow_id": str(order.escrow_id)
        }
        
        # Generate signature
        signature = self._generate_signature(payment_data)
        payment_data["signature"] = signature
        
        # Return payment URL
        return {
            "success": True,
            "payment_url": f"{self.api_url}/app/payment.pl",
            "payment_data": payment_data
        }
    
    def verify_payment(self, data):
        """Verify a Skrill payment notification"""
        # Extract signature from data
        received_signature = data.get("signature", "")
        
        # Remove signature from data for verification
        data_for_verification = data.copy()
        if "signature" in data_for_verification:
            del data_for_verification["signature"]
        
        # Generate signature for verification
        calculated_signature = self._generate_signature(data_for_verification)
        
        # Compare signatures
        if received_signature == calculated_signature:
            return {
                "success": True,
                "transaction_id": data.get("transaction_id"),
                "status": data.get("status"),
                "order_id": data.get("order_id"),
                "escrow_id": data.get("escrow_id")
            }
        
        return {
            "success": False,
            "error": "Invalid signature"
        }
    
    def _generate_signature(self, data):
        """Generate a signature for Skrill payment data"""
        # Sort data by key
        sorted_data = sorted(data.items())
        
        # Create string to sign
        string_to_sign = ""
        for key, value in sorted_data:
            string_to_sign += f"{key}={value}&"
        
        # Add secret word
        string_to_sign += self.secret_word
        
        # Generate MD5 hash
        return hashlib.md5(string_to_sign.encode()).hexdigest() 