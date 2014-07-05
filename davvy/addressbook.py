import davvy
from davvy.base import WebDAV
from django.http import HttpResponseForbidden,HttpResponse
from django.conf import settings
from lxml import etree

class CardDAV(WebDAV):

    collection_type = ['{DAV:}collection', '{urn:ietf:params:xml:ns:carddav}addressbook']
    dav_extensions = ['addressbook']

    def __init__(self, **kwargs):
        self.http_method_names += ['report']
        super(CardDAV, self).__init__(**kwargs)

    def put(self, request, user, resource_name):
        if not request.META['CONTENT_TYPE'].startswith('text/vcard;') and request.META['CONTENT_TYPE'] != 'text/vcard':
            return HttpResponseForbidden()
        return super(CardDAV, self).put(request, user, resource_name)

    def _multiget_response(self, request, resource, href):
        # temp hack, we need to find a better solution
        multistatus_response = davvy.xml_node('{DAV:}response')
        multistatus_response_href = davvy.xml_node('{DAV:}href', href)
        multistatus_response.append(multistatus_response_href)
        # add properties
        multistatus_response_propstat = davvy.xml_node('{DAV:}propstat')
        multistatus_response_propstat_prop = davvy.xml_node('{DAV:}prop')
        multistatus_response_propstat.append(multistatus_response_propstat_prop)
        multistatus_response_propstat_prop_address_data = davvy.xml_node('{urn:ietf:params:xml:ns:carddav}address-data', resource.file.read())
        multistatus_response_propstat_prop.append(multistatus_response_propstat_prop_address_data)
        # contenttype
        multistatus_response_propstat_prop_get_contenttype = davvy.xml_node('{DAV:}contenttype', resource.content_type)
        multistatus_response_propstat_prop.append(multistatus_response_propstat_prop_get_contenttype)
        # add status
        multistatus_response_propstat_status = davvy.xml_node('{DAV:}status', request.META['SERVER_PROTOCOL'] + ' 200 OK')
        multistatus_response_propstat.append(multistatus_response_propstat_status)

        multistatus_response.append(multistatus_response_propstat)

        return multistatus_response
        


    def report(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name)

        try:
            dom = etree.fromstring(request.read())
        except:
            raise davvy.exceptions.BadRequest()

        print etree.tostring(dom, pretty_print=True)

        if dom.tag != '{urn:ietf:params:xml:ns:carddav}addressbook-multiget':
            raise davvy.exceptions.BadRequest()

        doc = etree.Element('{DAV:}multistatus')

        hrefs = dom.iterfind('{DAV:}href')
        for href in hrefs:
            resource = davvy.get_resource(request.user, self.root, href.text[len(request.path):])
            if not resource.collection:
                doc.append(self._multiget_response(request, resource, href.text))

        response = HttpResponse(etree.tostring(doc, pretty_print=True), content_type='text/xml; charset=utf-8')
        response.status_code = 207
        response.reason_phrase = 'Multi-Status'
        return response            

def prop_dav_addressbook_home_set(dav, request, resource):
    current_user_principal = getattr(settings, 'DAVVY_ADDRESSBOOK_HOME_SET_BASE', None)
    if current_user_principal is not None:
        if isinstance(current_user_principal, list) or isinstance(current_user_principal, tuple):
            for base in current_user_principal:
                yield davvy.xml_node('{DAV:}href', base.rstrip('/') + '/' + request.user.username)
        else:
            yield davvy.xml_node('{DAV:}href', current_user_principal.rstrip('/') + '/' + request.user.username)

def prop_dav_supported_report_set(dav, request, resource):
    supported_report = davvy.xml_node('{DAV:}supported-report')
    report = davvy.xml_node('{DAV:}report')
    supported_report.append(report)
    addressbook_multiget = davvy.xml_node('{urn:ietf:params:xml:ns:carddav}addressbook-multiget')
    report.append(addressbook_multiget)
    return supported_report

davvy.register_prop('{urn:ietf:params:xml:ns:carddav}addressbook-home-set', prop_dav_addressbook_home_set, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}supported-report-set', prop_dav_supported_report_set, davvy.exceptions.Forbidden)
