"""
Django-specific test utilities
"""
from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import WSGIRequest
from django.db import close_connection
from django.test import TestCase
from django.test.client import Client

class UnprotectedClientHandler(BaseHandler):
    """
    A HTTP Handler that can be used for testing purposes.
    Uses the WSGI interface to compose requests, but returns
    the raw HttpResponse object

    This handler does not disable CSRF protection
    """
    def __call__(self, environ):
        from django.conf import settings
        from django.core import signals

        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            self.load_middleware()

        signals.request_started.send(sender=self.__class__)
        try:
            request = WSGIRequest(environ)
            response = self.get_response(request)

            # Apply response middleware.
            for middleware_method in self._response_middleware:
                response = middleware_method(request, response)
            response = self.apply_response_fixes(request, response)
        finally:
            signals.request_finished.disconnect(close_connection)
            signals.request_finished.send(sender=self.__class__)
            signals.request_finished.connect(close_connection)

        return response


class CSRFClient(Client):
    """
    Subclass of django's own test.client.Client that disables
    the hack used by the regular client to bypass CSRF checks
    """

    def __init__(self, **defaults):
        super(CSRFClient, self).__init__(**defaults)
        self.handler = UnprotectedClientHandler()


class CSRFTestCase(TestCase):
    """
    Subclass of django's own test.TestCase that allows to interact with cross
    site request forgery protection that is disabled by the regular
    TestCase.

    The actual thing happens inside CSRFClient()
    """

    def setUp(self):
        super(CSRFTestCase, self).setUp()
        self.client = CSRFClient()