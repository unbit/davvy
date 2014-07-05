from django.http import StreamingHttpResponse, HttpResponse, HttpResponseForbidden
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
import davvy
from lxml import etree
from django.utils.http import http_date
from davvy.models import Resource
from django.http.multipartparser import ChunkIter
from django.core.servers.basehttp import FileWrapper
import base64
import mimetypes
import types
from django.conf import settings

current_user_principals = []

class WebDAV(View):

    http_method_names = ['get', 'put', 'propfind', 'delete', 'head', 'options', 'mkcol', 'proppatch', 'copy', 'move']

    collection_type = '{DAV:}collection'

    # add your OPTIONS Dav header extensions here
    dav_extensions = []

    root = None

    @csrf_exempt
    def dispatch(self, request, username, *args, **kwargs):
        print request.META
        user = None
        # REMOTE_USER should be always honoured
        if request.META.has_key('REMOTE_USER'):
            user = User.objects.get(username=request.META['REMOTE_USER'])
            login(request, user)
        elif request.META.has_key('HTTP_AUTHORIZATION'):
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = base64.b64decode(auth[1]).split(':')
                    user = authenticate(username=uname, password=passwd)
        if user and user.is_active and user.username == username:
            login(request, user)
            request.user = user
            try:
                return super(WebDAV, self).dispatch(request, username, *args, **kwargs)
            except davvy.exceptions.DavException as e:
                code, phrase = e.status.split(' ', 1)
                response = HttpResponse(phrase, content_type='text/plain')
                response.status_code = int(code)
                response.reason_phrase = phrase
                return response 
           
        response = HttpResponse('Unathorized', content_type='text/plain')
        response.status_code = 401
        response['WWW-Authenticate'] = 'Basic realm="davvy"'
        return response

    def options(self, request, user, resource_name):
        response = HttpResponse()
        dav_base = ['1']
        dav_base += getattr(settings, 'DAVVY_EXTENSIONS', [])
        response['Dav'] = ','.join(dav_base + self.dav_extensions)
        response['Allow'] = ','.join([method.upper() for method in self.http_method_names])
        return response

    def head(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name)
        if resource.collection:
            return HttpResponseForbidden()
        response = HttpResponse(content_type=resource.content_type)
        response['Content-Length'] = resource.file.size
        response['Content-Disposition'] = "attachment; filename=%s" % resource.name
        return response

    def get(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name)
        if resource.collection:
            return HttpResponseForbidden()
        response = StreamingHttpResponse(FileWrapper(resource.file), content_type=resource.content_type)
        response['Content-Length'] = resource.file.size 
        response['Content-Disposition'] = "attachment; filename=%s" % resource.name
        return response

    def delete(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name)
        depth = request.META.get('HTTP_DEPTH', 'infinity')
        # return forbidden if there are still items in the collection and
        # Depth is not 'infinity'
        # this is not standard-compliant, but should increase security
        if resource.collection and depth != 'infinity':
            if resource.resource_set.count() > 0:
                return HttpResponseForbidden()
        resource.delete()
        return HttpResponse()

    def _get_destination(self, request, resource_name):
        destination = request.META['HTTP_DESTINATION']
        try:
            scheme = request.scheme
        except:
            scheme = request.META['wsgi.url_scheme']
        base = scheme + '://' + request.META['HTTP_HOST'] + request.path[:-len(resource_name)]
        if not destination.startswith(base):
            raise davvy.exceptions.BadGateway()

        return destination[len(base):].rstrip('/')
     
        
    def move(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name)
        depth = request.META.get('HTTP_DEPTH', 'infinity')
        overwrite = request.META.get('HTTP_OVERWRITE', 'T')

        destination = self._get_destination(request, resource_name)

        result = davvy.created

        try:
            resource2 = davvy.get_resource(request.user, self.root, destination)
            if overwrite == 'F':
                raise davvy.exceptions.PreconditionFailed()
            elif overwrite == 'T':
                result = davvy.nocontent
        except davvy.exceptions.NotFound:
            resource2 = davvy.get_resource(request.user, self.root, destination, create=True)

        # copy the resource
        resource2.collection = resource.collection
        resource2.file = resource.file
        resource2.size = resource.size
        resource2.content_type = resource.content_type
        resource2.created_at = resource.created_at
        resource2.save()

        # move properties
        for prop in resource.prop_set.all():
            prop.resource = resource2
            prop.save()

        # move children
        if resource.collection:
            for child in resource.resource_set.all():
                # first check for another child with the same attributes
                try:
                    twin = Resource.objects.get(parent=resource2,name=child.name)
                    if overwrite == 'T':
                        twin.delete()
                        raise Resource.DoesNotExist()
                    else:
                        raise davvy.exceptions.PreconditionFailed()
                except Resource.DoesNotExist:
                    child.parent = resource2
                    child.save()

        # destroy the old resource
        resource.delete()
        
        return result(request)

    def _copy_resource(self, request, resource, destination, overwrite):
        result = davvy.created

        try:
            resource2 = davvy.get_resource(request.user, self.root, destination)
            if overwrite == 'F':
                raise davvy.exceptions.PreconditionFailed()
            elif overwrite == 'T':
                result = davvy.nocontent
        except davvy.exceptions.NotFound:
            resource2 = davvy.get_resource(request.user, self.root, destination, create=True) 

        # copy the resource
        resource2.collection = resource.collection
        resource2.file = resource.file
        resource2.size = resource.size
        resource2.content_type = resource.content_type
        resource2.created_at = resource.created_at
        resource2.save()

        # copy properties
        for prop in resource.prop_set.all():
            prop.pk = None
            prop.parent = resource2
            prop.save()

        return result

    def _copy_coll(self, request, resource, destination, overwrite):
        result = self._copy_resource(request, resource, destination, overwrite)
        if resource.collection:
            for child in resource.resource_set.all():
                self._copy_coll(request, child, destination + '/' + child.name, overwrite)
        return result

    def copy(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name)
	overwrite = request.META.get('HTTP_OVERWRITE', 'T')
        depth = request.META.get('HTTP_DEPTH', 'infinity')
 
        destination = self._get_destination(request, resource_name)

        if resource.collection and depth == 'infinity':
            result = self._copy_coll(request, resource, destination, overwrite)
        else:
            result = self._copy_resource(request, resource, destination, overwrite)
            

        return result(request) 

    def _file_from_put(self, request, filename):
        upload_handlers = request.upload_handlers
        content_type = request.META.get('CONTENT_TYPE', None)
        if not content_type:
            content_type, encoding = mimetypes.guess_type(filename)
        if not content_type:
            content_type = 'application/octet-stream'
        content_length = request.META['CONTENT_LENGTH']
        for handler in upload_handlers:
            result = handler.handle_raw_input(None, request.META, content_length, None, None)
            if result is not None:
                return result[1], content_type
        possible_sizes = [x.chunk_size for x in upload_handlers if x.chunk_size]
        chunk_size = min([64 * 1024 * 1024] + possible_sizes)
        chunks = ChunkIter(request, chunk_size) 
        counters = [0] * len(upload_handlers)
        for handler in upload_handlers:
            try:
                handler.new_file(None, filename, content_type,
                                 content_length, None)
            except StopFutureHandlers:
                break

        for chunk in chunks:
            for i, handler in enumerate(upload_handlers):
                chunk_length = len(chunk)
                chunk = handler.receive_data_chunk(chunk, counters[i])
                counters[i] += chunk_length
                if chunk is None:
                    break

        for i, handler in enumerate(upload_handlers):
            file_obj = handler.file_complete(counters[i])
            if file_obj: return file_obj, content_type

        raise Exception('unable to get file handle from PUT request')


    def put(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name, create=True)
        resource.file, resource.content_type = self._file_from_put(request, resource.name)
        resource.size = resource.file.size
        resource.save()
        return davvy.created(request)

    def mkcol(self, request, user, resource_name):
        cl = int(request.META.get('CONTENT_LENGTH', '0'))
        if cl > 0:
            raise davvy.exceptions.UnsupportedMediaType()
        resource = davvy.get_resource(request.user, self.root, resource_name, create=True, collection=True, strict=True) 
        return davvy.created(request)

    def _propfind_response(self, request, href, resource, requested_props):
        response_props = resource.properties(self, request, requested_props)
        multistatus_response = etree.Element('{DAV:}response')
        multistatus_response_href = etree.Element('{DAV:}href')
        try:
            scheme = request.scheme
        except:
            scheme = request.META['wsgi.url_scheme']
        multistatus_response_href.text = scheme + '://' + request.META['HTTP_HOST'] + href 
        multistatus_response.append(multistatus_response_href)
        for prop in response_props:
            propstat = etree.Element('{DAV:}propstat')
            multistatus_response.append(propstat)
            tag, value, status = prop
            prop_element = etree.Element('{DAV:}prop')
            prop_element_item = etree.Element(tag)
            if isinstance(value, etree._Element):
                prop_element_item.append(value)
            elif isinstance(value, list) or isinstance(value, types.GeneratorType):
                for item in value:
                    prop_element_item.append(item)
            else:
                if value != '':
                    prop_element_item.text = value
            prop_element.append(prop_element_item)
            propstat.append(prop_element)
            propstat_status = etree.Element('{DAV:}status')
            propstat_status.text = request.META['SERVER_PROTOCOL'] + ' ' + status
            propstat.append(propstat_status)

        return multistatus_response

    def _proppatch_response(self, request, href, resource, requested_props):
        multistatus_response = etree.Element('{DAV:}response')
        multistatus_response_href = etree.Element('{DAV:}href')
        multistatus_response_href.text = href
        multistatus_response.append(multistatus_response_href)
        for prop in requested_props:
            propstat = etree.Element('{DAV:}propstat')
            multistatus_response.append(propstat)
            tag, status = prop
            prop_element = etree.Element('{DAV:}prop')
            prop_element.append(etree.Element(tag))
            propstat.append(prop_element)
            propstat_status = etree.Element('{DAV:}status')
            propstat_status.text = request.META['SERVER_PROTOCOL'] + ' ' + status
            propstat.append(propstat_status)

        return multistatus_response

    def propfind(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name)

        try:
            dom = etree.fromstring(request.read())
        except:
            raise davvy.exceptions.BadRequest()

        print etree.tostring(dom, pretty_print=True)

        requested_props = []
        props = dom.find('{DAV:}prop')
        if props is None: props = []
        for prop in props:
            requested_props.append(prop.tag)
        depth = request.META.get('HTTP_DEPTH', 'infinity')

        print "DEPTH", depth

        doc = etree.Element('{DAV:}multistatus')

        multistatus_response = self._propfind_response(request, request.path, resource, requested_props)
        doc.append(multistatus_response)

        if depth == '1':
            resources = Resource.objects.filter(parent=resource)
            for resource in resources:
                multistatus_response = self._propfind_response(request, request.path.rstrip('/') + '/' + resource.name, resource, requested_props)
                doc.append(multistatus_response)           

        print etree.tostring(doc, pretty_print=True)

        response = HttpResponse(etree.tostring(doc, pretty_print=True), content_type='text/xml; charset=utf-8')
        response.status_code = 207
        response.reason_phrase = 'Multi-Status'
        return response

    def proppatch(self, request, user, resource_name):
        resource = davvy.get_resource(request.user, self.root, resource_name)

        try:
            dom = etree.fromstring(request.read())
        except:
            raise davvy.exceptions.BadRequest()

        requested_props = []

        for setremove_item in dom:
            props = setremove_item.find('{DAV:}prop')
            if props is None: props = []
            # top-down must be respected
            for prop in props:
                if setremove_item.tag == '{DAV:}set':
                    try:
                        resource.set_prop(self, request, prop.tag, prop)
                        requested_props.append((prop.tag, '200 OK'))
                    except davvy.exceptions.DavException as e:
                        requested_props.append((prop.tag, e.status))
                elif setremove_item.tag == '{DAV:}remove':
                    try:
                        resource.del_prop(self, request, prop.tag)
                        requested_props.append((prop.tag, '200 OK'))
                    except davvy.exceptions.DavException as e:
                        requested_props.append((prop.tag, e.status))

        doc = etree.Element('{DAV:}multistatus')

        multistatus_response = self._proppatch_response(request, request.path, resource, requested_props)
        doc.append(multistatus_response)

        response = HttpResponse(etree.tostring(doc, pretty_print=True), content_type='text/xml; charset=utf-8')
        response.status_code = 207
        response.reason_phrase = 'Multi-Status'
        return response


def prop_dav_resourcetype(dav, request, resource):
    if resource.collection:
        if isinstance(dav.collection_type, list):
            rtypes = []
            for rtype in dav.collection_type:
                rtypes.append(davvy.xml_node(rtype))
            print rtypes
            return rtypes
        return davvy.xml_node(dav.collection_type)
    return ''

def prop_dav_getcontentlength(dav, request, resource):
    if not resource.collection:
        try:
            return str(resource.size)
        except:
            return '0'

def prop_dav_getetag(dav, request, resource):
    return str(resource.updated_at.strftime('%s'))

def prop_dav_getcontenttype(dav, request, resource):
    if not resource.collection:
        return resource.content_type
    return 'httpd/unix-directory'

def prop_dav_getlastmodified(dav, request, resource):
    return http_date(int(resource.updated_at.strftime('%s')))

def prop_dav_creationdate(dav, request, resource):
    return http_date(int(resource.created_at.strftime('%s')))

def prop_dav_current_user_principal(dav, request, resource):
    current_user_principal = getattr(settings, 'DAVVY_CURRENT_USER_PRINCIPAL_BASE', None)
    if current_user_principal is not None:
        if isinstance(current_user_principal, list) or isinstance(current_user_principal, tuple):
            for base in current_user_principal:
                yield davvy.xml_node('{DAV:}href', base.rstrip('/') + '/' + request.user.username)
        else:
            yield davvy.xml_node('{DAV:}href', current_user_principal.rstrip('/') + '/' + request.user.username)

def prop_dav_current_user_privilege_set(dav, request, resource):
    write = davvy.xml_node('{DAV:}privilege')
    write.append(davvy.xml_node('{DAV:}write'))
    return write

def prop_dav_acl(dav, request, resource):
    ace = davvy.xml_node('{DAV:}ace')
    ace_principal = davvy.xml_node('{DAV:}principal')
    ace_principal.append(davvy.xml_node('{DAV:}all'))
    #principals = prop_dav_current_user_principal(dav, request, resource)
    #for principal in principals:
    #    ace_principal.append(principal)
    ace.append(ace_principal)
    grant = davvy.xml_node('{DAV:}grant')
    privilege = davvy.xml_node('{DAV:}privilege')
    privilege.append(davvy.xml_node('{DAV:}write'))
    grant.append(privilege)
    ace.append(grant)
    return ace

davvy.register_prop('{DAV:}resourcetype', prop_dav_resourcetype, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}getcontentlength', prop_dav_getcontentlength, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}getetag', prop_dav_getetag, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}getcontenttype', prop_dav_getcontenttype, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}getlastmodified', prop_dav_getlastmodified, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}creationdate', prop_dav_creationdate, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}current-user-principal', prop_dav_current_user_principal, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}current-user-privilege-set', prop_dav_current_user_privilege_set, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}acl', prop_dav_acl, davvy.exceptions.Forbidden)
davvy.register_prop('{DAV:}sync-token', prop_dav_getetag, davvy.exceptions.Forbidden)
