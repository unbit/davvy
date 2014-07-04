import davvy
from davvy.base import WebDAV
from django.http import HttpResponseForbidden
from django.conf import settings
from lxml import etree

class CalDAV(WebDAV):

    collection_type = ['{DAV:}collection', '{urn:ietf:params:xml:ns:caldav}calendar']
    dav_extensions = ['addressbook']

    def __init__(self, **kwargs):
        self.http_method_names += ['mkcalendar']
        super(CalDAV, self).__init__(**kwargs)
        

    def put(self, request, user, resource_name):
        if not request.META['CONTENT_TYPE'].startswith('text/calendar;') and request.META['CONTENT_TYPE'] != 'text/calendar':
            return HttpResponseForbidden()
        return super(CalDAV, self).put(request, user, resource_name)

    def mkcalendar(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name, create=True, collection=True, strict=True)

        try:
            dom = etree.fromstring(request.read())
        except:
            raise davvy.exceptions.BadRequest()

        for prop in dom.find('{DAV:}set').find('{DAV:}prop'):
            resource.set_prop(self, request, prop.tag, prop)

        return davvy.created(request)

def prop_dav_calendar_home_set(dav, request, resource):
    current_user_principal = getattr(settings, 'DAVVY_CALENDAR_HOME_SET_BASE', None)
    if current_user_principal is not None:
        if isinstance(current_user_principal, list) or isinstance(current_user_principal, tuple):
            for base in current_user_principal:
                yield davvy.xml_node('{DAV:}href', base.rstrip('/') + '/' + request.user.username)
        else:
            yield davvy.xml_node('{DAV:}href', current_user_principal.rstrip('/') + '/' + request.user.username)
    

davvy.register_prop('{urn:ietf:params:xml:ns:caldav}calendar-home-set', prop_dav_calendar_home_set, davvy.exceptions.Forbidden)
