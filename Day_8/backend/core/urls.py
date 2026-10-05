from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

frontend_dir = settings.BASE_DIR.parent / 'frontend'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('products.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='dashboard-home'),
    # Support relative paths (e.g. href="style.css" or src="app.js") when served from root
    re_path(r'^(?P<path>.*\.(?:css|js|png|jpg|jpeg|gif|svg|ico|json))$', serve, {'document_root': frontend_dir}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=frontend_dir)
