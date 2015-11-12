from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
import base64

import davvy
import davvy.exceptions
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
                    username, password = base64.b64decode(auth[1]).split(':')
                    user = authenticate(username=username, password=password)

        if user and user.is_active:
            login(request, user)
            request.user = user

            # choose the correct current-user-principal handler (calendars/address-books)
            if self.root == "calendars":
                from davvy.calendar import prop_dav_calendar_home_set as prop_dav_resource_home_set
            elif self.root == "addressbook001":
                from davvy.addressbook import prop_dav_addressbook_home_set as prop_dav_resource_home_set
            else:
                from davvy.base import prop_dav_current_user_principal as prop_dav_resource_home_set

            old_cup_prop = None
            if prop_dav_resource_home_set:
                # let's backup current-user-principal handler
                cup = '{DAV:}current-user-principal'
                old_cup_prop = davvy.retrieve_prop(
                    cup
                )

                # let's modify it
                davvy.register_prop(
                    cup,
                    prop_dav_resource_home_set,
                    davvy.exceptions.Forbidden)

            try:
                response = super(WebDAV, self).dispatch(
                    request, user.username, "/", *args, **kwargs
                )
                dav_base = ['1']
                dav_base += getattr(settings, 'DAVVY_EXTENSIONS', [])
                response['Dav'] = ','.join(dav_base + self.dav_extensions)
            except Exception as e:
                logger.debug(e)
                code, phrase = e.status.split(' ', 1)
                response = HttpResponse(phrase, content_type='text/plain')
                response.status_code = int(code)
                response.reason_phrase = phrase
            finally:
                if old_cup_prop:
                    # restore current-user-principal
                    davvy.register_prop(
                        *old_cup_prop
                    )

        else:
            response = HttpResponse('Unauthorized', content_type='text/plain')
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic realm="davvy"'

        return response
