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
