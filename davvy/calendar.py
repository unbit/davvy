import davvy
from davvy.base import WebDAV
from django.http import HttpResponseForbidden,HttpResponse
from django.conf import settings
from lxml import etree

class CalDAV(WebDAV):

    collection_type = ['{urn:ietf:params:xml:ns:caldav}calendar', '{DAV:}collection']
    dav_extensions = ['calendar-access','calendar']

    def __init__(self, **kwargs):
        self.http_method_names += ['mkcalendar', 'report']
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

        #print etree.tostring(dom, pretty_print=True)

        for prop in dom.find('{DAV:}set').find('{DAV:}prop'):
            resource.set_prop(self, request, prop.tag, prop)

   
        doc = etree.Element('{urn:ietf:params:xml:ns:caldav}mkcalendar-response')
        doc_propstat = etree.Element('{DAV:}propstat')
        doc_propstat_status = etree.Element('{DAV:}status')
        doc_propstat_status.text = request.META['SERVER_PROTOCOL'] + ' 200 OK'
        doc_propstat.append(doc_propstat_status)
        doc.append(doc_propstat)
         

        response = HttpResponse(etree.tostring(doc, pretty_print=True), content_type='text/xml; charset=utf-8')
        response.status_code = 201
        response.reason_phrase = 'Created'
        response['Cache-Control'] = 'no-cache'
        return response

    def _multiget_response(self, request, resource, href, report_type='response'):
        try:
            scheme = request.scheme
        except:
            scheme = request.META['wsgi.url_scheme']
        multistatus_response = davvy.xml_node('{DAV:}' + report_type)
        # temp hack, we need to find a better solution
        multistatus_response_href = davvy.xml_node('{DAV:}href', scheme + '://' + request.META['HTTP_HOST'] + href)
        multistatus_response.append(multistatus_response_href)
        # add properties
        multistatus_response_propstat = davvy.xml_node('{DAV:}propstat')
        multistatus_response_propstat_prop = davvy.xml_node('{DAV:}prop')
        multistatus_response_propstat.append(multistatus_response_propstat_prop)
        if not resource.collection:
            multistatus_response_propstat_prop_calendar_data = davvy.xml_node('{urn:ietf:params:xml:ns:caldav}calendar-data', resource.file.read())
            multistatus_response_propstat_prop.append(multistatus_response_propstat_prop_calendar_data)
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
        resource = davvy.get_resource(request.user, self.root, resource_name)

        try:
            dom = etree.fromstring(request.read())
        except:
            raise davvy.exceptions.BadRequest()

        print etree.tostring(dom, pretty_print=True)

        doc = etree.Element('{DAV:}multistatus')

        if dom.tag == '{urn:ietf:params:xml:ns:caldav}calendar-query':
            doc.append(self._multiget_response(request, resource, request.path))
            for child in resource.resource_set.all():
                doc.append(self._multiget_response(request, child, request.path.rstrip('/') + '/' + child.name))
        elif dom.tag == '{DAV:}sync-collection':
            doc.append(self._multiget_response(request, resource, request.path, 'sync-response'))
            for child in resource.resource_set.all():
                doc.append(self._multiget_response(request, child, request.path.rstrip('/') + '/' + child.name, 'sync-response'))
            doc.append(davvy.xml_node('{DAV:}sync-token', prop_dav_calendar_getctag(self, request, resource)))
        elif dom.tag == '{urn:ietf:params:xml:ns:caldav}calendar-multiget':
            hrefs = dom.iterfind('{DAV:}href')
            for href in hrefs:
                child = davvy.get_resource(request.user, self.root, resource.name + '/' + href.text[len(request.path):].lstrip('/'))
                doc.append(self._multiget_response(request, child, request.path.rstrip('/') + '/' + child.name))
        else:
            raise davvy.exceptions.BadRequest()

        print etree.tostring(doc, pretty_print=True)

        response = HttpResponse(etree.tostring(doc, pretty_print=True), content_type='text/xml; charset=utf-8')
        response.status_code = 207
        response.reason_phrase = 'Multi-Status'
        return response

def prop_dav_calendar_home_set(dav, request, resource):
    current_user_principal = getattr(settings, 'DAVVY_CALENDAR_HOME_SET_BASE', None)
    if current_user_principal is not None:
        if isinstance(current_user_principal, list) or isinstance(current_user_principal, tuple):
            for base in current_user_principal:
                yield davvy.xml_node('{DAV:}href', base.rstrip('/') + '/' + request.user.username)
        else:
            yield davvy.xml_node('{DAV:}href', current_user_principal.rstrip('/') + '/' + request.user.username)

def prop_dav_calendar_getctag(dav, request, resource):
    max_value = int(resource.updated_at.strftime('%s'))
    if resource.collection:
        for child in resource.resource_set.all():
            new_value = int(child.updated_at.strftime('%s'))
            if new_value > max_value:
                max_value = new_value
    return str(max_value)
    

davvy.register_prop('{urn:ietf:params:xml:ns:caldav}calendar-home-set', prop_dav_calendar_home_set, davvy.exceptions.Forbidden)
davvy.register_prop('{http://calendarserver.org/ns/}getctag', prop_dav_calendar_getctag, davvy.exceptions.Forbidden)