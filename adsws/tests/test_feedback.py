# coding: utf-8
"""
Test webservices
"""

import json
import unittest
import requests

from adsws import feedback
from flask import url_for, current_app
from flask.ext.testing import TestCase
from httpretty import HTTPretty
from adsws.feedback.views import SlackFeedback, verify_recaptcha


class GoogleRecaptchaService(object):
    """
    Set up a mock google recaptcha api
    """
    def __init__(self):
        """
        Constructor
        """
        self.api_endpoint = current_app.config['GOOGLE_RECAPTCHA_ENDPOINT']

        def request_callback(request, uri, headers):
            """
            Callback
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return: httpretty response
            """
            data = request.parsed_body

            if data['response'][0] == 'correct_response':
                res = {'success': True}
            elif data['response'][0] == 'incorrect_response':
                res = {'success': False}
            elif data['response'][0] == 'dont_return_200':
                return 503, headers, "Service Unavailable"
            else:
                raise Exception(
                    "This case is not expected by the tests: {0}".format(data)
                )

            return 200, headers, json.dumps(res)

        HTTPretty.register_uri(
            method=HTTPretty.POST,
            uri=self.api_endpoint,
            body=request_callback,
            content_type="application/json"
        )

    def __enter__(self):
        """
        Defines the behaviour for __enter__
        """
        HTTPretty.enable()

    def __exit__(self, etype, value, traceback):
        """
        Defines the behaviour for __exit__
        :param etype: exit type
        :param value: exit value
        :param traceback: the traceback for the exit
        """
        HTTPretty.reset()
        HTTPretty.disable()


class SlackWebService(object):
    """
    context manager that mocks a ADSWS API response
    """
    def __init__(self):
        """
        Constructor
        """
        self.api_endpoint = current_app.config['FEEDBACK_SLACK_END_POINT']

        def request_callback(request, uri, headers):
            """
            Callback
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return: httpretty response
            """
            if 'text' in request.body:
                resp = json.dumps(dict(
                    msg='success'
                ))
                return 200, headers, resp
            else:
                resp = json.dumps(dict(
                    msg='fail'
                ))
                return 400, headers, resp

        HTTPretty.register_uri(
            method=HTTPretty.POST,
            uri=self.api_endpoint,
            body=request_callback,
            content_type="application/json"
        )

    def __enter__(self):
        """
        Defines the behaviour for __enter__
        """

        HTTPretty.enable()

    def __exit__(self, etype, value, traceback):
        """
        Defines the behaviour for __exit__

        :param etype: exit type
        :param value: exit value
        :param traceback: the traceback for the exit
        """

        HTTPretty.reset()
        HTTPretty.disable()


class TestBase(TestCase):
    """
    A basic base class for all of the tests here
    """

    def create_app(self):
        """
        Create the wsgi application
        """
        app_ = feedback.create_app()
        return app_


class TestFunctionals(TestBase):
    """
    Class that holds all the tests relevant to a complete workflow set,
    or functional test.
    """
    def test_submitting_feedback(self):
        """
        A generic test of the entire work flow of the feedback submission
        end point
        """
        # User fills the user feedback form
        form_data = {
            'name': 'Commenter',
            'comments': 'Why are my citations missing?',
            '_replyto': 'commenter@email.com',
            'g-recaptcha-response': 'correct_response'
        }

        # User presses submit on the feedback form
        url = url_for('slackfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=form_data
            )
        self.assertEqual(response.status_code, 200)

    def test_submitting_feedback_with_minimal_information(self):
        """
        Check they can send minimal information to the end point
        """
        # User fills the user feedback form
        form_data = {
            'comments': 'Why are my citations missing?',
            'g-recaptcha-response': 'correct_response'
        }

        # User presses submit on the feedback form
        url = url_for('slackfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=form_data
            )
        self.assertEqual(response.status_code, 200)

    def test_404_if_not_right_data(self):
        """
        Checks the passed data, at the moment we accept specific fields, and so it will not work if the user does not
        supply any comments
        """
        # User fills the user feedback form
        form_data = {
            'name': 'Commenter',
            '_replyto': 'commenter@email.com',
            'g-recaptcha-response': 'correct_response'
        }

        # User presses submit on the feedback form
        url = url_for('slackfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=form_data
            )
        self.assertEqual(response.status_code, 404)


class TestUnits(TestBase):
    """
    Class that contains all of the unit tests required for the slack feedback
    end point.
    """
    def test_mock_of_slack_endpoint(self):
        """
        Tests that the mock of the slack end point behaves as expected
        """

        post_data = {
            'text': 'Some text',
            'username': 'webhookbot',
            'channel': '#feedback',
            'icon_emoji': ':ghost:'
        }

        with SlackWebService():
            response = requests.post(
                current_app.config['FEEDBACK_SLACK_END_POINT'],
                data=post_data
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['msg'], 'success')

    def test_mock_of_slack_endpoint_fail(self):
        """
        Tests that the mock of the slack end point fails when no text is passed
        """

        post_data = {}

        with SlackWebService():
            response = requests.post(
                current_app.config['FEEDBACK_SLACK_END_POINT'],
                data=post_data
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['msg'], 'fail')

    def test_parser_parses_content(self):
        """
        Tests that the input given is parsed sensibly for slack
        """
        emoji = current_app.config['FEEDBACK_SLACK_EMOJI']
        post_data_sent = {
            'text': '```Incoming Feedback```\n'
                    '*Commenter*: Commenter\n'
                    '*e-mail*: commenter@email.com\n'
                    '*Feedback*: Why are my citations missing?\n'
                    '*sent to adshelp*: failed',
            'username': 'TownCrier',
            'channel': '#feedback',
            'icon_emoji': emoji
        }

        form_data = {
            'name': 'Commenter',
            'comments': 'Why are my citations missing?',
            '_replyto': 'commenter@email.com'
        }

        prettified_post_data = SlackFeedback().prettify_post(form_data)

        for key in post_data_sent.keys():
            self.assertEqual(post_data_sent[key], prettified_post_data[key])

    def test_can_send_abritrary_keyword_values(self):
        """
        Test the end point is not restrictive on the keyword values it can
        create content for.
        """
        emoji = current_app.config['FEEDBACK_SLACK_EMOJI']
        post_data_sent = {
            'text': '```Incoming Feedback```\n'
                    '*Commenter*: Commenter\n'
                    '*e-mail*: commenter@email.com\n'
                    '*Feedback*: Why are my citations missing?\n'
                    '*sent to adshelp*: failed\n'
                    '*IP Address*: 127.0.0.1\n'
                    '*Browser*: Firefox v42',
            'username': 'TownCrier',
            'channel': '#feedback',
            'icon_emoji': emoji
        }

        form_data = {
            'name': 'Commenter',
            'comments': 'Why are my citations missing?',
            'Browser': 'Firefox v42',
            'IP Address': '127.0.0.1',
            '_replyto': 'commenter@email.com'
        }

        prettified_post_data = SlackFeedback().prettify_post(form_data)

        for key in post_data_sent.keys():
            self.assertEqual(post_data_sent[key], prettified_post_data[key])

    def test_verify_google_recaptcha(self):
        """
        Test the function responsible for contacting the google recaptcha API
        and verifying the captcha response, using a mocked API
        """
        with GoogleRecaptchaService():
            # Set up a fake request object that will be passed directly to
            # the function being tested
            class FakeRequest: pass
            fakerequest = FakeRequest()
            fakerequest.remote_addr = 'placeholder'

            # Test a "success" response
            fakerequest.get_json = lambda **x: \
                {'g-recaptcha-response': 'correct_response'}
            res = verify_recaptcha(fakerequest)
            self.assertTrue(res)

            # Test a "fail" response
            fakerequest.get_json = lambda **x: \
                {'g-recaptcha-response': 'incorrect_response'}
            res = verify_recaptcha(fakerequest)
            self.assertFalse(res)

            # Test a 503 response
            fakerequest.get_json = lambda **x: \
                {'g-recaptcha-response': 'dont_return_200'}
            self.assertRaises(
                requests.HTTPError,
                verify_recaptcha,
                fakerequest
            )

            # Test a malformed request
            fakerequest = FakeRequest()
            self.assertRaises(
                (KeyError, AttributeError),
                verify_recaptcha,
                fakerequest
            )

if __name__ == '__main__':
    unittest.main(verbosity=2)
