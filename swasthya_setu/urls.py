"""
URL configuration for swasthya_setu project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('records.urls')),
]

# Serving media files (QR codes, patient photos, uploaded documents) directly
# via Django's serve() view, bypassing django.conf.urls.static.static() -
# that helper silently no-ops when DEBUG=False internally, regardless of any
# DEBUG check wrapped around it, which was the real cause of QR codes 404ing
# in production. Django's docs recommend a dedicated file server for real
# production - but for a hackathon prototype on Render's free tier, serving
# media through Django directly is the pragmatic choice here.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
