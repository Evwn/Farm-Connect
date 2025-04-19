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

# PayPal Integration
class PayPalGateway:
    def __init__(self):
        # Configure PayPal with your API credentials
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.mode = settings.PAYPAL_MODE
        self.api_base_url = 'https://api.sandbox.paypal.com' if self.mode == 'sandbox' else 'https://api.paypal.com'
    
    def _get_access_token(self):
        """Get an access token from PayPal"""
        url = f"{self.api_base_url}/v1/oauth2/token"
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded_credentials}',
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            raise Exception(f"Failed to get PayPal access token: {response.text}")
    
    def create_payment(self, order, return_url, cancel_url):
        """Create a PayPal payment for an order"""
        access_token = self._get_access_token()
        
        url = f"{self.api_base_url}/v1/payments/payment"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        payment_data = {
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"{order.quantity}kg of {order.product.name}",
                        "sku": f"ORDER-{order.id}",
                        "price": str(order.total_price),
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(order.total_price),
                    "currency": "USD"
                },
                "description": f"Escrow payment for order #{order.id}"
            }]
        }
        
        response = requests.post(url, headers=headers, json=payment_data)
        if response.status_code == 201:
            payment = response.json()
            # Find the approval URL
            for link in payment['links']:
                if link['rel'] == 'approval_url':
                    return {
                        'success': True,
                        'payment_id': payment['id'],
                        'approval_url': link['href']
                    }
        
        return {
            'success': False,
            'error': response.text
        }
    
    def execute_payment(self, payment_id, payer_id):
        """Execute a PayPal payment after user approval"""
        access_token = self._get_access_token()
        
        url = f"{self.api_base_url}/v1/payments/payment/{payment_id}/execute"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        data = {
            "payer_id": payer_id
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            payment = response.json()
            return {
                'success': True,
                'transaction_id': payment['transactions'][0]['related_resources'][0]['sale']['id']
            }
        
        return {
            'success': False,
            'error': response.text
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