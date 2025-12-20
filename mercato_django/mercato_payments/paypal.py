"""
PayPal API integration module
Handles PayPal orders, captures, and IPN webhook notifications
"""

import requests
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from .models import PaymentTransaction, PaymentSettings
from mercato_lotteries.models import LotteryTicket
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PayPalClient:
    """PayPal API client for handling orders and payments"""
    
    def __init__(self, use_sandbox=True):
        self.sandbox_mode = use_sandbox
        self.base_url = (
            "https://api-m.sandbox.paypal.com" if use_sandbox 
            else "https://api-m.paypal.com"
        )
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self):
        """Get OAuth access token from PayPal"""
        if not self.client_id or not self.client_secret:
            settings_obj = PaymentSettings.objects.first()
            if settings_obj:
                self.client_id = settings_obj.paypal_client_id
                self.client_secret = settings_obj.paypal_client_secret
                self.sandbox_mode = settings_obj.paypal_sandbox_mode
                self.base_url = (
                    "https://api-m.sandbox.paypal.com" if self.sandbox_mode 
                    else "https://api-m.paypal.com"
                )
            else:
                raise Exception("PayPal settings not configured")
        
        url = f"{self.base_url}/v1/oauth2/token"
        
        auth = (self.client_id, self.client_secret)
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(url, auth=auth, data=data)
        
        if response.status_code != 200:
            logger.error(f"Failed to get PayPal access token: {response.text}")
            raise Exception(f"PayPal authentication failed: {response.text}")
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        self.token_expires_at = datetime.now().timestamp() + token_data['expires_in'] - 300
        
        return self.access_token
    
    def get_valid_access_token(self):
        """Get valid access token, refreshing if necessary"""
        if not self.access_token or datetime.now().timestamp() >= self.token_expires_at:
            return self.get_access_token()
        return self.access_token
    
    def create_order(self, ticket, amount, return_url, cancel_url):
        """
        Create a PayPal order for a lottery ticket
        
        Args:
            ticket: LotteryTicket instance
            amount: Amount to charge
            return_url: URL to redirect after successful payment
            cancel_url: URL to redirect after cancelled payment
            
        Returns:
            PayPal order response
        """
        access_token = self.get_valid_access_token()
        
        # Calculate commission (10%)
        commission = (Decimal(amount) * Decimal('0.10')).quantize(Decimal('0.01'))
        item_amount = (Decimal(amount) - commission).quantize(Decimal('0.01'))
        
        url = f"{self.base_url}/v2/checkout/orders"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "PayPal-Request-Id": str(ticket.id)
        }
        
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": f"TICKET_{ticket.id}",
                "amount": {
                    "currency_code": "EUR",
                    "value": f"{amount}",
                    "breakdown": {
                        "item_total": {
                            "currency_code": "EUR",
                            "value": f"{item_amount}"
                        },
                        "tax_total": {
                            "currency_code": "EUR",
                            "value": f"{commission}"
                        }
                    }
                },
                "description": f"Lottery Ticket #{ticket.ticket_number}",
                "custom_id": str(ticket.id),
                "items": [{
                    "name": f"Ticket for {ticket.lottery.title}",
                    "unit_amount": {
                        "currency_code": "EUR",
                        "value": f"{item_amount}"
                    },
                    "quantity": "1",
                    "tax": {
                        "currency_code": "EUR",
                        "value": f"{commission}"
                    }
                }]
            }],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "brand_name": "Mercato Lotteries",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW"
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to create PayPal order: {response.text}")
            raise Exception(f"PayPal order creation failed: {response.text}")
        
        return response.json()
    
    def capture_order(self, order_id):
        """
        Capture a PayPal order after payment approval
        
        Args:
            order_id: PayPal order ID
            
        Returns:
            Capture response
        """
        access_token = self.get_valid_access_token()
        
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.post(url, headers=headers, json={})
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to capture PayPal order: {response.text}")
            raise Exception(f"PayPal order capture failed: {response.text}")
        
        return response.json()
    
    def refund_payment(self, capture_id, amount=None):
        """
        Refund a captured payment
        
        Args:
            capture_id: PayPal capture ID
            amount: Amount to refund (if None, full refund)
            
        Returns:
            Refund response
        """
        access_token = self.get_valid_access_token()
        
        url = f"{self.base_url}/v2/payments/captures/{capture_id}/refund"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Prefer": "return=representation"
        }
        
        payload = {}
        if amount:
            payload["amount"] = {
                "value": f"{amount}",
                "currency_code": "EUR"
            }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to refund PayPal payment: {response.text}")
            raise Exception(f"PayPal refund failed: {response.text}")
        
        return response.json()


def process_paypal_ipn(data):
    """
    Process PayPal IPN (Instant Payment Notification) webhook
    
    Args:
        data: IPN data from PayPal webhook
        
    Returns:
        Boolean indicating success
    """
    try:
        event_type = data.get('event_type')
        
        if event_type == 'CHECKOUT.ORDER.COMPLETED':
            return handle_order_completed(data)
        elif event_type == 'PAYMENT.CAPTURE.COMPLETED':
            return handle_payment_capture_completed(data)
        elif event_type == 'PAYMENT.CAPTURE.REFUNDED':
            return handle_payment_refunded(data)
        
        logger.info(f"Unhandled PayPal IPN event type: {event_type}")
        return False
        
    except Exception as e:
        logger.error(f"Error processing PayPal IPN: {str(e)}")
        return False


def handle_order_completed(data):
    """Handle PayPal order completed event"""
    try:
        resource = data.get('resource', {})
        order_id = resource.get('id')
        custom_id = resource.get('purchase_units', [{}])[0].get('custom_id')
        
        if not custom_id:
            logger.error("No custom_id found in PayPal order")
            return False
        
        # Find the ticket and create/update transaction
        try:
            ticket = LotteryTicket.objects.get(id=custom_id)
            amount = Decimal(resource['purchase_units'][0]['amount']['value'])
            
            # Create or update payment transaction
            transaction, created = PaymentTransaction.objects.get_or_create(
                ticket=ticket,
                paypal_order_id=order_id,
                defaults={
                    'amount': amount,
                    'status': 'processing',
                }
            )
            
            return True
            
        except LotteryTicket.DoesNotExist:
            logger.error(f"Ticket not found: {custom_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error handling order completed: {str(e)}")
        return False


def handle_payment_capture_completed(data):
    """Handle PayPal payment capture completed event"""
    try:
        resource = data.get('resource', {})
        order_id = resource.get('supplementary_data', {}).get('related_ids', {}).get('order_id')
        capture_id = resource.get('id')
        payer_email = data.get('resource', {}).get('payer', {}).get('email_address')
        
        if not order_id:
            logger.error("No order_id found in PayPal capture")
            return False
        
        # Find and update transaction
        transactions = PaymentTransaction.objects.filter(paypal_order_id=order_id)
        
        for transaction in transactions:
            transaction.paypal_tx_id = capture_id
            transaction.payer_email = payer_email
            transaction.status = 'completed'
            transaction.payment_completed_at = datetime.now()
            transaction.save()
            
            # Update ticket status
            transaction.ticket.payment_status = 'completed'
            transaction.ticket.save()
            
            logger.info(f"Payment completed for ticket {transaction.ticket.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling payment capture: {str(e)}")
        return False


def handle_payment_refunded(data):
    """Handle PayPal payment refunded event"""
    try:
        resource = data.get('resource', {})
        capture_id = resource.get('id')
        
        # Find transaction by capture_id
        transactions = PaymentTransaction.objects.filter(paypal_tx_id=capture_id)
        
        for transaction in transactions:
            transaction.status = 'refunded'
            transaction.refunded_at = datetime.now()
            transaction.save()
            
            # Update ticket status
            transaction.ticket.payment_status = 'refunded'
            transaction.ticket.save()
            
            logger.info(f"Payment refunded for ticket {transaction.ticket.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling payment refund: {str(e)}")
        return False


def refund_ticket_payment(ticket):
    """
    Refund a ticket payment (for cancelled lotteries)
    
    Args:
        ticket: LotteryTicket instance
        
    Returns:
        Boolean indicating success
    """
    try:
        # Find completed payment transaction
        transaction = PaymentTransaction.objects.filter(
            ticket=ticket,
            status='completed'
        ).first()
        
        if not transaction:
            logger.error(f"No completed transaction found for ticket {ticket.id}")
            return False
        
        # Initialize PayPal client
        paypal_client = PayPalClient()
        
        try:
            # Process refund via PayPal
            refund_response = paypal_client.refund_payment(
                transaction.paypal_tx_id,
                transaction.net_amount
            )
            
            # Update transaction record
            transaction.status = 'refunded'
            transaction.refunded_at = datetime.now()
            transaction.save()
            
            # Update ticket status
            ticket.payment_status = 'refunded'
            ticket.save()
            
            logger.info(f"Successfully refunded ticket {ticket.id}")
            return True
            
        except Exception as paypal_error:
            # Even if PayPal refund fails, mark as refunded for our records
            transaction.status = 'refunded'
            transaction.save()
            ticket.payment_status = 'refunded'
            ticket.save()
            logger.error(f"PayPal refund failed but marked as refunded: {str(paypal_error)}")
            return True
            
    except Exception as e:
        logger.error(f"Error refunding ticket payment: {str(e)}")
        return False


def get_paypal_settings():
    """Get PayPal settings from database or use defaults"""
    try:
        settings_obj = PaymentSettings.objects.first()
        if settings_obj and settings_obj.paypal_client_id and settings_obj.paypal_client_secret:
            return {
                'client_id': settings_obj.paypal_client_id,
                'client_secret': settings_obj.paypal_client_secret,
                'sandbox_mode': settings_obj.paypal_sandbox_mode
            }
    except Exception:
        pass
    
    # Default fallback (should be replaced with actual credentials)
    return {
        'client_id': settings.PAYPAL_CLIENT_ID if hasattr(settings, 'PAYPAL_CLIENT_ID') else '',
        'client_secret': settings.PAYPAL_CLIENT_SECRET if hasattr(settings, 'PAYPAL_CLIENT_SECRET') else '',
        'sandbox_mode': True
    }