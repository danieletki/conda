from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from mercato_accounts.views import home as home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('accounts/', include(('mercato_accounts.urls', 'accounts'), namespace='accounts')),
    path('lotteries/', include('mercato_lotteries.urls')),
    path('payments/', include('mercato_payments.urls')),
    path('notifications/', include('mercato_notifications.urls')),
    path('admin-panel/', include(('mercato_admin.urls', 'admin_panel'), namespace='admin_panel')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
