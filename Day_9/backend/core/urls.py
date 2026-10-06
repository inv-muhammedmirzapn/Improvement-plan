from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

frontend_dist = settings.BASE_DIR.parent / 'frontend' / 'dist'
frontend_dir = frontend_dist if frontend_dist.exists() else (settings.BASE_DIR.parent / 'frontend')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('products.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='dashboard-home'),
    re_path(r'^(?P<path>.*\.(?:css|js|png|jpg|jpeg|gif|svg|ico|json|woff2?))$', serve, {'document_root': frontend_dir}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=frontend_dir)
