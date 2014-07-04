Davvy
=====

A Django application for building WebDAV services

Installation and Configuration
==============================

Just add 'davvy' in `INSTALLED_APPS` and set the directory where you want to store WebDAV files via the `DAVVY_STORAGE_PATH` settings option

```py
DAVVY_STORAGE_PATH = '/var/www/davvy'
```

Now you can start configuring urls; Davvy is class-based-view based, so you can extend it simply subclassing the WebDAV class (as an example the included CardDAV and CalDAV classes inherit from it).

The url regexp must obey to a simple rule:

```py
from davvy.base import WebDAV
from davvy.addressbook import CardDAV

urlpatterns = patterns('',
   
    url(r'^principals/(\w+)/(.*)', WebDAV.as_view(root='storage')),
    url(r'^storage/(\w+)/(.*)', WebDAV.as_view(root='storage')),
    url(r'^addressbook/(\w+)/(.*)', CardDAV.as_view(root='addressbook001')),

    url(r'^admin/', include(admin.site.urls)),
)
```

