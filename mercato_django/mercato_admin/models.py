from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class AdminActionLog(models.Model):
    """
    Log of all admin actions for auditing
    """
    ACTION_TYPES = [
        ('kyc_approve', 'Approvazione KYC'),
        ('kyc_reject', 'Rifiuto KYC'),
        ('lottery_approve', 'Approvazione Lotteria'),
        ('lottery_reject', 'Rifiuto Lotteria'),
        ('payment_refund', 'Rimborso Pagamento'),
        ('banner_create', 'Creazione Banner'),
        ('banner_update', 'Aggiornamento Banner'),
        ('banner_delete', 'Eliminazione Banner'),
        ('csv_export', 'Esportazione CSV'),
        ('system_setting', 'Modifica Impostazioni'),
        ('other', 'Altro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='admin_actions')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    action_description = models.TextField()
    related_model = models.CharField(max_length=100, blank=True)  # e.g., 'CustomUser', 'Lottery', 'Payment'
    related_id = models.CharField(max_length=100, blank=True)  # ID of the related object
    metadata = models.JSONField(default=dict, blank=True)  # Additional data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_action_type_display()} by {self.admin_user.username if self.admin_user else 'System'}"
    
    def get_action_type_color(self):
        """Get bootstrap color class for action type badge"""
        action_colors = {
            'kyc_approve': 'success',
            'kyc_reject': 'danger',
            'lottery_approve': 'success',
            'lottery_reject': 'warning',
            'payment_refund': 'info',
            'banner_create': 'primary',
            'banner_update': 'info',
            'banner_delete': 'danger',
            'csv_export': 'secondary',
            'system_setting': 'warning',
            'other': 'dark'
        }
        return action_colors.get(self.action_type, 'secondary')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin Action Log'
        verbose_name_plural = 'Admin Action Logs'


class SiteBanner(models.Model):
    """
    Site-wide banners and announcements
    """
    BANNER_TYPES = [
        ('info', 'Informazione'),
        ('success', 'Successo'),
        ('warning', 'Avviso'),
        ('error', 'Errore'),
        ('promotion', 'Promozione'),
    ]

    BANNER_POSITIONS = [
        ('top', 'Top'),
        ('bottom', 'Bottom'),
        ('modal', 'Modal'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    banner_type = models.CharField(max_length=20, choices=BANNER_TYPES, default='info')
    position = models.CharField(max_length=20, choices=BANNER_POSITIONS, default='top')
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    link_url = models.URLField(blank=True)
    link_text = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_banners')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Banner: {self.title} ({self.get_banner_type_display()})"
    
    def get_banner_type_color(self):
        """Get bootstrap color class for banner type badge"""
        banner_colors = {
            'info': 'info',
            'success': 'success',
            'warning': 'warning',
            'error': 'danger',
            'promotion': 'primary'
        }
        return banner_colors.get(self.banner_type, 'info')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Site Banner'
        verbose_name_plural = 'Site Banners'

    @property
    def is_currently_active(self):
        """Check if banner is currently active based on date range"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.end_date and self.end_date < now:
            return False
        return self.start_date <= now


class KYCDocument(models.Model):
    """
    KYC documents uploaded by users
    """
    DOCUMENT_TYPES = [
        ('id_card', 'Carta d\'Identità'),
        ('passport', 'Passaporto'),
        ('driver_license', 'Patente di Guida'),
        ('utility_bill', 'Bolla Utente'),
        ('other', 'Altro'),
    ]

    STATUS_CHOICES = [
        ('pending', 'In Attesa'),
        ('approved', 'Approvato'),
        ('rejected', 'Rifiutato'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='kyc_documents/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_kyc_documents')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"KYC Document: {self.get_document_type_display()} for {self.user.username}"

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'KYC Document'
        verbose_name_plural = 'KYC Documents'

    def approve(self, admin_user, notes=''):
        """Approve KYC document"""
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.notes = notes
        self.save()
        
        # Mark user as verified
        self.user.is_verified = True
        self.user.save()
        
        return True

    def reject(self, admin_user, rejection_reason, notes=''):
        """Reject KYC document"""
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = rejection_reason
        self.notes = notes
        self.save()
        
        return True