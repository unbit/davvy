from davvy.models import Resource, Prop
from lxml import etree
import davvy.exceptions
from django.http import HttpResponse

# global variables used for storing props callables and handlers
props_get = {}
props_set = {}

def register_prop(name, handler_get, handler_set):
    """
    register a property handler
    """
    global props_get, props_set
    if handler_get:
        props_get[name] = handler_get
    if handler_set:
        props_set[name] = handler_set

def xml_node(name, value=None):
    x = etree.Element(name)
    x.text = value
    return x

def _get_root(user, root):
    try:
        resource = Resource.objects.get(name=root,user=user,parent=None,collection=True)
    except:
        resource = Resource.objects.create(name=root,user=user,parent=None,collection=True)
    return resource

def get_resource(user, root, name, create=False,collection=False, strict=False):
    # remove final slashes
    name = name.rstrip('/')
    parent = _get_root(user, root)
    if not name: return parent
    # split the name
    parts = name.split('/')
    # skip the last item
    # on error, returns conflict
    # returns root in case of '/'
    for part in parts[:-1]:
        try:
            resource_part = Resource.objects.get(user=user,parent=parent,name=part)
            if not resource_part.collection: raise Resource.DoesNotExist()
        except Resource.DoesNotExist:
            raise davvy.exceptions.Conflict()
        parent = resource_part
    # now check for the requested item
    try:
        resource = Resource.objects.get(user=user,parent=parent,name=parts[-1]) 
        if strict and create:
            raise davvy.exceptions.AlreadyExists() 
    except Resource.DoesNotExist:
        if create:
            resource = Resource.objects.create(user=user,parent=parent,name=parts[-1],collection=collection)
        else:
            raise davvy.exceptions.NotFound()
        
    return resource

def created(request):
    response = HttpResponse('Created', content_type='text/plain')
    response.status_code = 201
    response.reason_phrase = 'Created'
    response['Cache-Control'] = 'no-cache'
    return response

def nocontent(request):
    response = HttpResponse('No Content', content_type='text/plain')
    response.status_code = 204
    response.reason_phrase = 'No Content'
    response['Cache-Control'] = 'no-cache'
    return response
