#!/usr/bin/env python3
"""
Test script to verify the payments dashboard context variables
"""

import sys
import os

# Add Django project to path
sys.path.insert(0, '/home/engine/project/mercato_django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mercato_django.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from mercato_payments.views import dashboard
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

User = get_user_model()

def test_dashboard_context():
    """Test that dashboard view provides all required context variables"""
    
    print("Testing payments dashboard context variables...")
    print("-" * 60)
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/payments/')
    
    # Add session middleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    # Test with superuser
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("⚠️  No superuser found, creating one...")
            admin_user = User.objects.create_superuser(
                username='admin_test',
                email='admin@test.com',
                password='testpass123'
            )
        
        request.user = admin_user
        
        # Get the response
        from mercato_payments.views import dashboard as dashboard_view
        response = dashboard_view(request)
        
        # Check if response is successful
        if response.status_code == 200:
            print("✓ Dashboard view returns 200 OK for admin user")
            
            # Check context variables
            context = response.context_data if hasattr(response, 'context_data') else {}
            
            required_vars = [
                'total_revenue',
                'total_paid',
                'total_platform_commission',
                'total_commission',  # This is the key variable we added
                'transaction_count',
                'recent_transactions',
                'is_admin_view'
            ]
            
            print("\nChecking admin context variables:")
            for var in required_vars:
                if var in context:
                    print(f"✓ {var}: {context[var]}")
                else:
                    print(f"✗ {var}: MISSING!")
            
            # Verify is_admin_view is True
            if context.get('is_admin_view'):
                print("\n✓ is_admin_view is True for admin user")
            else:
                print("\n✗ is_admin_view should be True for admin user")
        else:
            print(f"✗ Dashboard view returned status code: {response.status_code}")
        
    except Exception as e:
        print(f"✗ Error testing admin view: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with regular user
    try:
        regular_user = User.objects.filter(is_superuser=False, is_staff=False).first()
        if not regular_user:
            print("\n⚠️  No regular user found, creating one...")
            regular_user = User.objects.create_user(
                username='regular_test',
                email='regular@test.com',
                password='testpass123'
            )
        
        request.user = regular_user
        response = dashboard_view(request)
        
        if response.status_code == 200:
            print("\n✓ Dashboard view returns 200 OK for regular user")
            
            context = response.context_data if hasattr(response, 'context_data') else {}
            
            required_vars = [
                'total_paid',
                'total_revenue',  # Should be same as total_paid for regular users
                'total_platform_commission',
                'total_commission',  # This is the key variable we added
                'transaction_count',
                'recent_transactions',
                'is_admin_view'
            ]
            
            print("\nChecking regular user context variables:")
            for var in required_vars:
                if var in context:
                    print(f"✓ {var}: {context[var]}")
                else:
                    print(f"✗ {var}: MISSING!")
            
            # Verify is_admin_view is False
            if not context.get('is_admin_view'):
                print("\n✓ is_admin_view is False for regular user")
            else:
                print("\n✗ is_admin_view should be False for regular user")
        else:
            print(f"✗ Dashboard view returned status code: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error testing regular user view: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test completed!")

if __name__ == '__main__':
    test_dashboard_context()
