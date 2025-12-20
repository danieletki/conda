from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('mercato_accounts.urls')),
    path('lotteries/', include('mercato_lotteries.urls')),
    path('payments/', include('mercato_payments.urls')),
    path('notifications/', include('mercato_notifications.urls')),
    path('admin-panel/', include('mercato_admin.urls')),
    path('', RedirectView.as_view(url='/accounts/home/', permanent=False)),  # Redirect root to home
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)