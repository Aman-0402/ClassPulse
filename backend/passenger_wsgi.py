import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'classpulse.settings')

from django.core.wsgi import get_wsgi_application

_django_application = get_wsgi_application()


def application(environ, start_response):
    # cPanel's Setup Python App mounts this app at a path (e.g. "/api") via
    # PassengerBaseURI, which splits the URL into SCRIPT_NAME (the mount
    # point) + PATH_INFO (the remainder) per the WSGI spec. Django's own
    # urlconf resolves against PATH_INFO alone, but this app's urls.py
    # already hardcodes "api/" as part of its own routes (same convention
    # used in local dev, where there's no Passenger mount to split anything).
    # Left alone, a request to /api/student/login/ would arrive at Django as
    # PATH_INFO=/student/login/ — missing the "api/" it still expects — a
    # 404 with no obvious cause. Folding SCRIPT_NAME back into PATH_INFO
    # restores the exact full path Django sees locally, so urls.py, the
    # test suite, and local dev stay untouched.
    script_name = environ.get('SCRIPT_NAME', '')
    if script_name:
        environ['PATH_INFO'] = script_name + environ.get('PATH_INFO', '')
        environ['SCRIPT_NAME'] = ''
    return _django_application(environ, start_response)
