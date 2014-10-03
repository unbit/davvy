from django.test import TestCase

from django.test import RequestFactory
from davvy.base import WebDAV

from django.test.utils import override_settings
from django.contrib.auth.models import User
import base64
from django.contrib.sessions.middleware import SessionMiddleware
import os.path

# Create your tests here.


@override_settings(DAVVY_STORAGE_PATH='/tmp')
class WebDAVTestCase(TestCase):

    def setUp(self):
        self.username = 'tester'
        self.view = WebDAV.as_view(root='tests')
        self.user = User.objects.create_user(
            self.username, 'test@test', self.username)
        self.auth = 'Basic ' + \
            base64.b64encode('{}:{}'.format(self.username, self.username))
        self.middleware = SessionMiddleware()
        self.factory = RequestFactory()
        self.base = '/principal/' + self.username

    def test_putandget(self, resource_name='services'):
        uri = os.path.join(self.base, resource_name)
        request = self.factory.put(uri,
                                   content_type='text/plain',
                                   data=open('/etc/services').read(),
                                   HTTP_AUTHORIZATION=self.auth,
                                   )
        self.middleware.process_request(request)
        response = self.view(request, self.username, resource_name)
        self.assertEqual(response.status_code, 201)

        request = self.factory.get(uri, HTTP_AUTHORIZATION=self.auth)
        self.middleware.process_request(request)
        response = self.view(request, self.username, resource_name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertEqual(
            ''.join(response.streaming_content), open('/etc/services').read())

    def test_mkcol(self, resource_name='coll'):
        uri = os.path.join(self.base, resource_name)
        request = self.factory.generic('MKCOL', uri,
                                       HTTP_AUTHORIZATION=self.auth,
                                       )
        self.middleware.process_request(request)
        response = self.view(request, self.username, resource_name)
        self.assertEqual(response.status_code, 201)

        self.test_putandget(resource_name + '/services')

    def test_delete_not_empty_coll(self):
        self.test_mkcol('coll2')
        uri = os.path.join(self.base, 'coll2')
        request = self.factory.generic('DELETE', uri,
                                       HTTP_AUTHORIZATION=self.auth,
                                       HTTP_DEPTH='0',
                                       )
        self.middleware.process_request(request)
        response = self.view(request, self.username, 'coll2')
        self.assertEqual(response.status_code, 403)

    def test_delete_coll(self):
        self.test_mkcol('coll3')
        uri = os.path.join(self.base, 'coll3')
        request = self.factory.generic('DELETE', uri,
                                       HTTP_AUTHORIZATION=self.auth,
                                       )
        self.middleware.process_request(request)
        response = self.view(request, self.username, 'coll3')
        self.assertEqual(response.status_code, 200)

    def test_delete_resource(self, resource_name='deleteme'):
        self.test_putandget(resource_name)
        uri = os.path.join(self.base, resource_name)
        request = self.factory.generic('DELETE', uri,
                                       HTTP_AUTHORIZATION=self.auth,
                                       )
        self.middleware.process_request(request)
        response = self.view(request, self.username, resource_name)
        self.assertEqual(response.status_code, 200)
