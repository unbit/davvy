from django.http import HttpResponse
from django.conf import settings
# from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
import base64

from davvy.base import WebDAV

import logging
logger = logging.getLogger(__name__)


class WellKnownDAV(WebDAV):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):

        user = None
        if 'REMOTE_USER' in request.META:
            user = User.objects.get(username=request.META['REMOTE_USER'])
        elif 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = base64.b64decode(auth[1]).split(':')
                    user = authenticate(username=uname, password=passwd)

        if (user and user.is_active):
            login(request, user)
            request.user = user

            try:
                response = super(WebDAV, self).dispatch(
                    request, user.username, "/", *args, **kwargs
                )
                dav_base = ['1']
                dav_base += getattr(settings, 'DAVVY_EXTENSIONS', [])
                response['Dav'] = ','.join(dav_base + self.dav_extensions)

                # current_user_principal = getattr(
                #     settings, 'DAVVY_CALENDAR_HOME_SET_BASE', None
                # )

                # def _dav_calendar_home_set(request):
                #     if current_user_principal is not None:
                #         if isinstance(current_user_principal, list) or isinstance(current_user_principal, tuple):
                #             for base in current_user_principal:
                #                 yield base.rstrip('/') + '/' + request.user.username + '/'
                #         else:
                #             yield current_user_principal.rstrip('/') + '/' + request.user.username + '/'

                # redirect_url = list(_dav_calendar_home_set(request))[0]
                # response = redirect(redirect_url, permanent=True)
            except Exception as e:
                logger.debug(e)
                code, phrase = e.status.split(' ', 1)
                response = HttpResponse(phrase, content_type='text/plain')
                response.status_code = int(code)
                response.reason_phrase = phrase

        else:
            response = HttpResponse('Unathorized', content_type='text/plain')
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic realm="davvy"'

        return response
