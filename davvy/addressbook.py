import davvy
from davvy.base import WebDAV
from django.http import HttpResponseForbidden,HttpResponse
from django.conf import settings
from lxml import etree

class CardDAV(WebDAV):

    collection_type = ['{urn:ietf:params:xml:ns:carddav}addressbook', '{DAV:}collection']
    dav_extensions = ['addressbook']

    def __init__(self, **kwargs):
        self.http_method_names += ['report']
        super(CardDAV, self).__init__(**kwargs)

    def put(self, request, user, resource_name):
        if not request.META['CONTENT_TYPE'].startswith('text/vcard;') and request.META['CONTENT_TYPE'] != 'text/vcard':
            return HttpResponseForbidden()
        return super(CardDAV, self).put(request, user, resource_name)

    def _multiget_response(self, request, resource, href):
        try:
            scheme = request.scheme
        except:
            scheme = request.META['wsgi.url_scheme']
        # temp hack, we need to find a better solution
        multistatus_response = davvy.xml_node('{DAV:}response')
        multistatus_response_href = davvy.xml_node('{DAV:}href', scheme + '://' + request.META['HTTP_HOST'] + href)
        multistatus_response.append(multistatus_response_href)
        # add properties
        multistatus_response_propstat = davvy.xml_node('{DAV:}propstat')
        multistatus_response_propstat_prop = davvy.xml_node('{DAV:}prop')
        multistatus_response_propstat.append(multistatus_response_propstat_prop)
        
        multistatus_response_propstat_prop_address_data = davvy.xml_node('{urn:ietf:params:xml:ns:carddav}address-data', ''.join(self.storage.retrieve(self, request, resource)))
        multistatus_response_propstat_prop.append(multistatus_response_propstat_prop_address_data)
        # contenttype
        multistatus_response_propstat_prop_get_contenttype = davvy.xml_node('{DAV:}getcontenttype', resource.content_type)
        multistatus_response_propstat_prop.append(multistatus_response_propstat_prop_get_contenttype)

        # contenttype
        multistatus_response_propstat_prop_getetag = davvy.xml_node('{DAV:}getetag', str(resource.updated_at.strftime('%s')))
        multistatus_response_propstat_prop.append(multistatus_response_propstat_prop_getetag)

        # add status
        multistatus_response_propstat_status = davvy.xml_node('{DAV:}status', request.META['SERVER_PROTOCOL'] + ' 200 OK')
        multistatus_response_propstat.append(multistatus_response_propstat_status)

        multistatus_response.append(multistatus_response_propstat)

        return multistatus_response
        


    def report(self, request, user, resource_name):
        resource = self.get_resource(request, user, resource_name)

        try:
            dom = etree.fromstring(request.read())
        except:
            raise davvy.exceptions.BadRequest()

        print etree.tostring(dom, pretty_print=True)

        doc = etree.Element('{DAV:}multistatus')

        if dom.tag == '{urn:ietf:params:xml:ns:carddav}addressbook-multiget':
            hrefs = dom.iterfind('{DAV:}href')
            for href in hrefs:
                resource = self.get_resource(request, user, href.text[len(request.path):])
                if not resource.collection:
                    doc.append(self._multiget_response(request, resource, href.text))

        elif dom.tag in ('{urn:ietf:params:xml:ns:carddav}addressbook-query', '{DAV:}sync-collection'):
            for child in resource.resource_set.all():
                doc.append(self._multiget_response(request, child, request.path.rstrip('/') + '/' + child.name)) 
        else:
            raise davvy.exceptions.BadRequest()

        print etree.tostring(doc, pretty_print=True)

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
    supported_reports = []

    supported_report = davvy.xml_node('{DAV:}supported-report')
    report = davvy.xml_node('{DAV:}report')
    supported_report.append(report)
    addressbook_multiget = davvy.xml_node('{urn:ietf:params:xml:ns:carddav}addressbook-multiget')
    report.append(addressbook_multiget)
    supported_reports.append(supported_report)

    supported_report = davvy.xml_node('{DAV:}supported-report')
    report = davvy.xml_node('{DAV:}report')
    supported_report.append(report)
    addressbook_query = davvy.xml_node('{urn:ietf:params:xml:ns:carddav}addressbook-query')
    report.append(addressbook_query)
    supported_reports.append(supported_report)

    supported_report = davvy.xml_node('{DAV:}supported-report')
    report = davvy.xml_node('{DAV:}report')
    supported_report.append(report)
    calendar_query = davvy.xml_node('{urn:ietf:params:xml:ns:caldav}calendar-query')
    report.append(calendar_query)
    supported_reports.append(supported_report)

    supported_report = davvy.xml_node('{DAV:}supported-report')
    report = davvy.xml_node('{DAV:}report')
    supported_report.append(report)
    calendar_multiget = davvy.xml_node('{urn:ietf:params:xml:ns:caldav}calendar-multiget')
    report.append(calendar_multiget)
    supported_reports.append(supported_report)

    supported_report = davvy.xml_node('{DAV:}supported-report')
    report = davvy.xml_node('{DAV:}report')
    supported_report.append(report)
    sync_collection = davvy.xml_node('{DAV:}sync-collection')
    report.append(sync_collection)
    supported_reports.append(supported_report)

    return supported_reports

davvy.register_prop('{urn:ietf:params:xml:ns:carddav}addressbook-home-set', prop_dav_addressbook_home_set, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}supported-report-set', prop_dav_supported_report_set, davvy.exceptions.Forbidden)
