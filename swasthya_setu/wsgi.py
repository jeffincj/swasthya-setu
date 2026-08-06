"""
WSGI config for swasthya_setu project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swasthya_setu.settings')

application = get_wsgi_application()

# Explicit WhiteNoise wrapping - bypasses any ambiguity in middleware
# auto-detecting STATIC_ROOT, which was silently failing in some deploy
# environments. This directly tells WhiteNoise exactly where the collected
# static files live and what URL prefix serves them.
from whitenoise import WhiteNoise
from django.conf import settings

application = WhiteNoise(application, root=str(settings.STATIC_ROOT), prefix="static/")