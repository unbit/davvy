import davvy
from davvy.base import WebDAV
from django.http import HttpResponseForbidden
from django.conf import settings

class CardDAV(WebDAV):

    collection_type = ['{DAV:}collection', '{urn:ietf:params:xml:ns:carddav}addressbook']
    dav_extensions = ['addressbook']

    def put(self, request, user, resource_name):
        if not request.META['CONTENT_TYPE'].startswith('text/vcard;') and request.META['CONTENT_TYPE'] != 'text/vcard':
            return HttpResponseForbidden()
        return super(CardDAV, self).put(request, user, resource_name)

def prop_dav_addressbook_home_set(dav, request, resource):
    current_user_principal = getattr(settings, 'DAVVY_ADDRESSBOOK_HOME_SET_BASE', None)
    if current_user_principal is not None:
        if isinstance(current_user_principal, list) or isinstance(current_user_principal, tuple):
            for base in current_user_principal:
                yield davvy.xml_node('{DAV:}href', base.rstrip('/') + '/' + request.user.username)
        else:
            yield davvy.xml_node('{DAV:}href', current_user_principal.rstrip('/') + '/' + request.user.username)
    

davvy.register_prop('{urn:ietf:params:xml:ns:carddav}addressbook-home-set', prop_dav_addressbook_home_set, davvy.exceptions.Forbidden)
