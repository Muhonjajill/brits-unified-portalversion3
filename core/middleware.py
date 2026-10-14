import time
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import JsonResponse

class InactivityTimeoutMiddleware:
    # URLs polled in the background; they must not count as user activity
    IGNORE_PREFIXES = ('/notifications/',)

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'INACTIVITY_TIMEOUT', 30 * 60)

    def __call__(self, request):
        if request.user.is_authenticated:
            now = time.time()
            last_activity = request.session.get('last_activity')

            if last_activity and (now - last_activity) > self.timeout:
                logout(request)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or \
                   'application/json' in request.headers.get('accept', ''):
                    return JsonResponse(
                        {'status': 'timeout', 'message': 'Session expired due to inactivity.'},
                        status=401,
                    )
                messages.warning(request, "You were logged out due to inactivity.")
                return redirect('login')

            if not request.path.startswith(self.IGNORE_PREFIXES):
                request.session['last_activity'] = now

        return self.get_response(request)