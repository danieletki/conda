from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('kyc-pending/', views.kyc_pending_list, name='kyc_pending'),
    path('kyc-approve/<uuid:document_id>/', views.kyc_approve, name='kyc_approve'),
    path('kyc-reject/<uuid:document_id>/', views.kyc_reject, name='kyc_reject'),
    path('lottery-moderation/', views.lottery_moderation_list, name='lottery_moderation'),
    path('lottery-approve/<int:lottery_id>/', views.lottery_approve, name='lottery_approve'),
    path('lottery-reject/<int:lottery_id>/', views.lottery_reject, name='lottery_reject'),
    path('payment-reports/', views.payment_reports, name='payment_reports'),
    path('disputes/', views.disputes_list, name='disputes'),
    path('export/<str:export_type>/', views.export_csv, name='export_csv'),
    path('banners/', views.banner_management, name='banner_management'),
    path('action-logs/', views.admin_action_logs, name='action_logs'),
]