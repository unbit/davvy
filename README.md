Davvy
=====

A Django application for building WebDAV services

Installation and Configuration
==============================

Just add 'davvy' in `INSTALLED_APPS` and set the directory where you want to store WebDAV files via the `DAVVY_STORAGE_PATH` settings option:

```py
DAVVY_STORAGE_PATH = '/var/www/davvy'
```

Now you can start configuring urls; Davvy is class-view based, so you can extend it by simply subclassing the WebDAV class (as an example the included CardDAV and CalDAV classes inherit from it).

The url regexp must obey to a simple rule:

```py
from davvy.base import WebDAV
from davvy.addressbook import CardDAV
from davvy.calendar import CalDAV

urlpatterns = patterns('',
   
    url(r'^principals/(\w+)/(.*)', WebDAV.as_view(root='storage')),
    url(r'^storage/(\w+)/(.*)', WebDAV.as_view(root='storage')),
    url(r'^addressbook/(\w+)/(.*)', CardDAV.as_view(root='addressbook001')),
    url(r'^calendars/(\w+)/(.*)', CalDAV.as_view(root='calendars')),

    url(r'^admin/', include(admin.site.urls)),
)
```

As you can see the second part of the url must always be catched, as it is the username of the resource you want to use:

``/principals/foobar/``

will be the base for the 'foobar' user, as well as

``/principals/foobar/photos/2014/summer/1.jpg``

will map to the /photos/2014/summer/1.jpg resource for the 'foobar' user, while

``/addressbook/foobar``

is the main storage for the CardDAV system (all of the collections will be automatically mapped to an addressbook resource)

The `root` parameter in the class-based-view arguments, is required, and you can see it as the 'disk' containing collections and objects.

Internally, `/principals/foobar/photos/2014/summer/1.jpg` will be mapped to `storage/photos/2014/summer/1.jpg` of the user `foobar`. (a root is created for every user on-demand).


Homes set discovery (required for iOS/OSX clients)
==================================================

Moderns Dav clients, try to automatically discover the home of specific resources.

As an example a CardDAV client could get the home of a principal (see it as a username in Dav slang) addressbook, asking for the ``addressbook-home-set`` property (with a PROPFIND request).

Davvy can be configured to return such path via Django settings.py:

```py
DAVVY_CURRENT_USER_PRINCIPAL_BASE = '/principals'
DAVVY_ADDRESSBOOK_HOME_SET_BASE = '/addressbook'
DAVVY_CALENDAR_HOME_SET_BASE = '/calendars'
```

davvy will automatically append /username to every home.

Thanks to this options you will be able to force your client to search for calendars in /calendars/foobar even if it has been configured for /principals/foobar


Clients configuration
=====================

Sadly, client-side configuration varies.

As an example here are provided the configuration samples to be used in OSX Mavericks (10.9) Calendar/Contacts and Mozilla Thunderbird.

OSX Calendar configuration
--------------------------

Setup a new CalDAV account having the following configuration:

```
Account Type = Advanced
User Name = foo
Password = bar
Server Address = www.foo.org
Server Path = /calendars/foo
Port = 8080
```

OSX Contacts configuration
--------------------------
Setup a new CardDAV account (under other accounts) having the following configuration:

```
Account Type = Advanced
User Name = foo
Password = bar
Server Address = www.foo.org:8080/addressbook/foo
```

Mozilla Thunderbird configuration
--------------------------

Testing
=======

The project uses the litmus tool for testing
