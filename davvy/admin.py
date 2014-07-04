from django.contrib import admin
from davvy.models import *
from django import forms

class ResourceAdminForm(forms.ModelForm):
    class Meta:
        model = Resource
        widgets = {
            'file':forms.TextInput(attrs={'size':'64'})
        }

# Register your models here.

class ResourceAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'user')
    form = ResourceAdminForm
    

admin.site.register(Resource, ResourceAdmin)
admin.site.register(Prop)
