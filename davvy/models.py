from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import uuid
import os.path
import davvy
import davvy.exceptions
from lxml import etree

# Create your models here.

class Resource(models.Model):

    def generate_uuid():
        return str(uuid.uuid4())

    user = models.ForeignKey(User)
    parent = models.ForeignKey('Resource',null=True,blank=True)
    name = models.CharField(max_length=255)
    collection = models.BooleanField(default=False)
    uuid = models.CharField(max_length=36,default=generate_uuid)
    content_type = models.CharField(max_length=255,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    size = models.BigIntegerField(default=0)

    # pretty ugly, but should help viewing the full names
    def __unicode__(self):
        parts = []
        parent = self.parent
        while True:
            if not parent: break 
            parts.insert(0, Resource.objects.get(pk=parent.id).name)
            parent = parent.parent
        parts.append(self.name)
        return '/'+'/'.join(parts)

    def del_prop(self, dav, request, name):
        try:
            model_prop = self.prop_set.get(name=name)
            model_prop.delete()
        except Prop.DoesNotExist:
            # removing a non existent property is not an error 
            pass

    def get_prop(self, dav, request, name):
       if name in davvy.props_get:
           value = davvy.props_get[name](dav, request, self)
           if value is not None: return value
           raise davvy.exceptions.Forbidden()
       try:
           model_prop = self.prop_set.get(name=name)
           if model_prop.is_xml:
               return etree.fromstring(model_prop.value)
           return model_prop.value
       except Prop.DoesNotExist:
           raise davvy.exceptions.NotFound()

    def set_prop(self, dav, request, name, value):
       if name in davvy.props_set:
           e = davvy.props_set[name](dav, request, self, value)
           if isinstance(e, Exception):
               raise e
       else:
           try:
               prop = self.prop_set.get(name=name)
           except Prop.DoesNotExist:
               prop = self.prop_set.create(name=name)
           if value.text is not None:
               prop.value = value.text
               prop.is_xml = False
           elif hasattr(value, 'get_children') and len(value.get_children()) > 0:
               prop.value = etree.tostring(value, pretty_print=True)
               prop.is_xml = True
           prop.save()
       return self.get_prop(dav, request, name)

    @property
    def displayname(self):
        try:
            prop = self.prop_set.get(name='{DAV:}displayname')
            return prop.value
        except:
            return ''

    def properties(self, dav, request, requested_props):
        propstat = []
        for prop in requested_props:
            try:
                value = self.get_prop(dav, request, prop)
                status = '200 OK'
            except Exception as e:
                value = None
                if hasattr(e, 'status'):
                    status = e.status
                else:
                    status = '500 Internal Server Error'
            propstat.append((prop, ) + (value, status))
        return propstat

    class Meta:
        unique_together = ( 'user', 'parent', 'name' )

class Prop(models.Model):

    resource = models.ForeignKey(Resource)
    name = models.CharField(max_length=255)
    value = models.TextField(blank=True,null=True)
    is_xml = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ( 'resource', 'name' )
