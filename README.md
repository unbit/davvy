#Davvy

A Django application for building WebDAV services.

#Installation and Configuration

Just add 'davvy' in `INSTALLED_APPS` and set the directory where you want to store WebDAV files via the `DAVVY_STORAGE_PATH` settings option:

```py
DAVVY_STORAGE_PATH = '/var/www/davvy'
```

Now you can start configuring your application's urls. 
Davvy is class-view based, so you can extend it by simply subclassing the WebDAV class (as an example the included CardDAV and CalDAV classes inherit from it).

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

As you can see, the second part of the url must always be catched, as it contains the username owning the resource you want to use.

``/principals/foobar/`` will be the base for the 'foobar' user, as well as ``/principals/foobar/photos/2014/summer/1.jpg`` will map to the /photos/2014/summer/1.jpg resource for the 'foobar' user.

``/addressbook/foobar`` is instead the main storage for the CardDAV system (all of the collections will be automatically mapped to an addressbook resource).

The `root` parameter in the class-based-view arguments is required, and you can see it as the _'disk'_ containing collections and objects.

Internally, `/principals/foobar/photos/2014/summer/1.jpg` will be indeed mapped to `storage/photos/2014/summer/1.jpg` of the user `foobar`. 
The root directory is created for every user on-demand.

#Davvy specific features
<!-- Davvy provides the following specific features. -->

##Resource protection
Protected resources won't be deleted by any of the client requests.
You can mark protected resources by using, for instance, the Django Admin Interface.

##Resource sharing
Resources can be shared among users.
Specifically, you can assign resources to one or more groups.
Then, those resources will be shared among every user belonging to the selected groups.

As an example, you could share one of your calendars with the group "bars". 
To do so, you only need to select "bars" among the groups of your calendar, in the Django admin interface, or anywhere else. 
That's it, refresh your client and voilà!

#Home sets autodiscovery (required for iOS/OSX clients)

Moderns Dav clients automatically try to discover the home of specific resources.

As an example a CardDAV client could get the home of a principal (see it as a username in Dav _slang_) addressbook, asking for the ``addressbook-home-set`` property (with a PROPFIND request).

Davvy can be configured to return such path via Django settings.py:

```py
DAVVY_CURRENT_USER_PRINCIPAL_BASE = '/principals'
DAVVY_ADDRESSBOOK_HOME_SET_BASE = '/addressbook'
DAVVY_CALENDAR_HOME_SET_BASE = '/calendars'
```

Remember: davvy will automatically append /username to every home.

Thanks to this options you will be able to force your client to search for calendars in /calendars/foobar even if it has been configured for /principals/foobar.


## Apple's custom autodiscovery

In addition to the [_home set_ requirements](#home-sets-autodiscovery-required-for-iososx-clients), Apple's clients can use a [custom autodiscovery protocol](https://tools.ietf.org/html/rfc6764) to automatically locate WebDAV extensions specific home sets and services.

As a consequence, you'll be able to configure your client by only entering the server remote address, without caring about any of the home sets.

Davvy can be configured to correctly return the required protocol components to any Apple client by simply editing your `urlpatterns` as follows:

```py
from davvy.wellknown import WellKnownDAV

urlpatterns = patterns('',
    # ...
    url(r'^.well[-_]?known/caldav/?$', 
        WellKnownDAV.as_view(root='calendars')),
    url(r'^.well[-_]?known/carddav/?$', 
        WellKnownDAV.as_view(root='addressbook001')),
    # ...
)
```


#Client configuration

Client-side configuration largely varies.

As an example, we provide here some configuration samples to be used in OS X Mavericks (10.9) Calendar/Contacts and in Mozilla Thunderbird.

##OS X Calendar

If you have enabled [davvy's autodiscovery for Apple clients](#apples-custom-autodiscovery) you can simply setup a CalDAV account as follows:

```ini
Account Type = Manual
User Name = foo
Password = bar
Server Address = www.yourserver.org
```

Otherwise, you should use the following configuration:

```ini
Account Type = Advanced
User Name = foo
Password = bar
Server Address = www.yourserver.org
Server Path = /calendars/foo
Port = 8080  ; or any port you want
```

##OS X Contacts

If you have enabled [davvy's autodiscovery for Apple clients](#apples-custom-autodiscovery) you can simply setup a CardDAV account as follows:

```ini
Account Type = CardDAV
User Name = foo
Password = bar
Server Address = www.foo.org
```

Otherwise, your server address path should point to the specific user's addressbook: `www.foo.org/addressbooks/foo/`.

Note: the trailing slash in the server address is mandatory when running in HTTPS mode.

##Mozilla Thunderbird

Mozilla Thunderbird does not provide WebDAV support _out-of-the-box_, but provides service specific extensions.

As a consequence, to manage your CalDAV calendars you'll need to install the [Lightning extension](https://addons.mozilla.org/it/thunderbird/addon/lightning/).

Then, you can add a new "on the network" CalDAV calendar. 
Lightning does not provide any form of service discovery. So, you'll need to enter the full calendar path in the location field: _i.e._: 
``http://remote:port/calendars/username/calendar_hash/``.

#Testing

This project makes use of the litmus tool for testing.
