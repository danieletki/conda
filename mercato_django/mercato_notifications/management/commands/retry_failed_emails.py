from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import logging

from mercato_notifications.models import EmailLog
from mercato_notifications.email_service import EmailService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retry failed emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of emails to retry'
        )
        parser.add_argument(
            '--older-than',
            type=int,
            default=24,
            help='Retry emails older than N hours'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting retry of failed emails...')
        )
        
        limit = options['limit']
        older_than_hours = options['older_than']
        
        # Get failed emails
        cutoff_time = timezone.now() - timedelta(hours=older_than_hours)
        
        failed_emails = EmailLog.objects.filter(
            status__in=['failed', 'retry'],
            retry_count__lt=models.F('max_retries'),
            created_at__lte=cutoff_time
        )[:limit]
        
        email_service = EmailService()
        retried_count = 0
        success_count = 0
        
        for email_log in failed_emails:
            self.stdout.write(f'Retrying email: {email_log.subject} -> {email_log.recipient_email}')
            
            if email_log.retry_email(email_service):
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Retry successful for {email_log.recipient_email}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Retry failed for {email_log.recipient_email}')
                )
            
            retried_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Retry Summary:'))
        self.stdout.write(f'Retried: {retried_count}')
        self.stdout.write(f'Successful: {success_count}')
        self.stdout.write(f'Failed: {retried_count - success_count}')
        
        if retried_count > 0:
            success_rate = (success_count / retried_count) * 100
            self.stdout.write(f'Success Rate: {success_rate:.1f}%')