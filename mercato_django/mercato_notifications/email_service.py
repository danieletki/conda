import logging
import time
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import EmailLog

logger = logging.getLogger(__name__)
User = get_user_model()


class EmailService:
    """
    Service class for handling email sending with retry logic and tracking
    """
    
    def __init__(self):
        self.retry_attempts = getattr(settings, 'EMAIL_RETRY_ATTEMPTS', 3)
        self.retry_delay = getattr(settings, 'EMAIL_RETRY_DELAY', 60)
    
    def render_template(self, template_name, context=None):
        """
        Render email template with context
        """
        from django.template.loader import get_template
        
        if context is None:
            context = {}
        
        # Add common context variables
        context.update({
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
            'current_year': timezone.now().year
        })
        
        try:
            template = get_template(f'emails/{template_name}.html')
            return template.render(context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            return f"<h1>Email Error</h1><p>Template rendering failed: {template_name}</p>"
    
    def send_email(self, template_name, recipient_email, subject, context=None, 
                   from_email=None, html_only=True, priority='normal', 
                   user=None):
        """
        Send email with tracking and retry logic
        
        Args:
            template_name: Name of the email template (without .html)
            recipient_email: Email address of recipient
            subject: Subject line
            context: Template context variables
            from_email: Sender email (defaults to settings.DEFAULT_FROM_EMAIL)
            html_only: Whether to send HTML only or also plain text
            priority: Email priority ('low', 'normal', 'high', 'urgent')
            user: User object (for tracking)
        """
        
        if context is None:
            context = {}
        
        # Use default from email if not specified
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        try:
            # Render HTML content
            html_content = self.render_template(template_name, context)
            
            # Create plain text version (basic)
            text_content = self._html_to_text(html_content)
            
            # Create email message
            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[recipient_email]
            )
            email_message.attach_alternative(html_content, "text/html")
            
            # Send with retry logic
            success = self._send_with_retry(email_message, recipient_email, subject)
            
            # Track the email
            self._track_email(
                recipient_email=recipient_email,
                subject=subject,
                status='sent' if success else 'failed',
                user=user,
                template_used=template_name,
                priority=priority,
                context_data=context
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {e}")
            
            # Track the failed email
            self._track_email(
                recipient_email=recipient_email,
                subject=subject,
                status='failed',
                user=user,
                template_used=template_name,
                priority=priority,
                error_message=str(e),
                context_data=context
            )
            
            return False
    
    def _send_with_retry(self, email_message, recipient_email, subject):
        """
        Send email with retry logic
        """
        for attempt in range(self.retry_attempts):
            try:
                result = email_message.send()
                
                if result > 0:
                    logger.info(f"Email sent successfully to {recipient_email}")
                    return True
                else:
                    raise Exception("Email send returned 0")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {recipient_email}: {e}")
                
                if attempt < self.retry_attempts - 1:
                    # Wait before retry
                    delay = self.retry_delay * (attempt + 1)  # Exponential backoff
                    logger.info(f"Retrying email to {recipient_email} in {delay} seconds")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.retry_attempts} attempts failed for {recipient_email}")
        
        return False
    
    def _track_email(self, recipient_email, subject, status, user=None, 
                     template_used=None, priority='normal',
                     error_message=None, external_message_id=None, context_data=None):
        """
        Track email in the EmailLog database
        """
        try:
            # Create or update EmailLog entry
            email_log = EmailLog.create_log_entry(
                template_name=template_used or 'custom',
                recipient_email=recipient_email,
                subject=subject,
                context_data=context_data or {},
                user=user,
                from_email=None,  # Will use default
                priority=priority
            )
            
            if status == 'sent':
                email_log.mark_as_sent()
            elif status == 'failed':
                email_log.mark_as_failed(error_message)
            elif status == 'delivered':
                email_log.mark_as_delivered()
            else:
                # Keep pending status
                email_log.save()
                
        except Exception as e:
            logger.error(f"Error tracking email for {recipient_email}: {e}")
    
    def _html_to_text(self, html_content):
        """
        Convert HTML to plain text (basic implementation)
        """
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Convert HTML entities
        text = text.replace(' ', ' ')
        text = text.replace('&', '&')
        text = text.replace('<', '<')
        text = text.replace('>', '>')
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text


# Convenience functions for specific email types
def send_registration_email(user):
    """Send welcome email to new user"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='registration',
        recipient_email=user.email,
        subject='Benvenuto su MercatoPro! 🎯',
        context={'user': user},
        user=user,
        priority='normal'
    )


def send_kyc_approved_email(user):
    """Send KYC approval notification"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='kyc_approved',
        recipient_email=user.email,
        subject='KYC Approvato! 🎉 Inizia a Creare le Tue Lotterie',
        context={'user': user},
        user=user,
        priority='high'
    )


def send_kyc_rejected_email(user, kyc_ticket_id=None):
    """Send KYC rejection notification"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='kyc_rejected',
        recipient_email=user.email,
        subject='KYC - Azione Richiesta 📋',
        context={'user': user, 'kyc_ticket_id': kyc_ticket_id},
        user=user,
        priority='high'
    )


def send_lottery_activated_email(lottery):
    """Send lottery activation notification to seller"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='lottery_activated',
        recipient_email=lottery.seller.email,
        subject=f'Lotteria Attivata: {lottery.title} 🎯',
        context={'lottery': lottery, 'seller': lottery.seller},
        user=lottery.seller,
        priority='normal'
    )


def send_ticket_purchased_email(ticket):
    """Send ticket purchase confirmation to buyer"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='ticket_purchased',
        recipient_email=ticket.buyer.email,
        subject=f'Biglietto Acquistato: {ticket.lottery.title} 🎫',
        context={
            'ticket': ticket,
            'lottery': ticket.lottery,
            'buyer': ticket.buyer
        },
        user=ticket.buyer,
        priority='normal'
    )


def send_lottery_won_email(ticket, winner, drawing):
    """Send lottery win notification to winner"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='lottery_won',
        recipient_email=winner.email,
        subject=f'🎉 HAI VINTO! {ticket.lottery.title}',
        context={
            'ticket': ticket,
            'lottery': ticket.lottery,
            'winner': winner,
            'drawing': drawing
        },
        user=winner,
        priority='urgent'
    )


def send_seller_winner_notification_email(lottery, winner, ticket, drawing):
    """Send winner details to seller"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='seller_winner_notification',
        recipient_email=lottery.seller.email,
        subject=f'Hai un Vincitore! {lottery.title} 🏆',
        context={
            'lottery': lottery,
            'seller': lottery.seller,
            'winner': winner,
            'ticket': ticket,
            'drawing': drawing
        },
        user=lottery.seller,
        priority='high'
    )


def send_lottery_lost_email(ticket, winner, drawing):
    """Send lottery result to non-winners (optional)"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='lottery_lost',
        recipient_email=ticket.buyer.email,
        subject=f'Estrazione Completata: {ticket.lottery.title}',
        context={
            'ticket': ticket,
            'lottery': ticket.lottery,
            'winner': winner,
            'drawing': drawing,
            'participant': ticket.buyer
        },
        user=ticket.buyer,
        priority='low'
    )


def send_expiration_reminder_email(user, lottery, time_remaining, notification_type):
    """Send lottery expiration reminder"""
    email_service = EmailService()
    
    return email_service.send_email(
        template_name='expiration_reminder',
        recipient_email=user.email,
        subject=f'Promemoria: {lottery.title} sta per scadere ⏰',
        context={
            'user': user,
            'lottery': lottery,
            'time_remaining': time_remaining,
            'notification_type': notification_type
        },
        user=user,
        priority='normal'
    )