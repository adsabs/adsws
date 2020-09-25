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
from adsws.feedback.views import UserFeedback, verify_recaptcha
from adsws.tests.stubdata import missing_references, associated_other, associated_errata, new_abstract, corrected_abstract, general_feedback


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
        app_ = feedback.create_app(
            FEEDBACK_SLACK_END_POINT = 'https://hooks.slack.com/services/TOKEN/TOKEN',
            FEEDBACK_SLACK_EMOJI = ':interrobang:',
            FORM_SLACK_EMOJI = ':inbox_tray:',
            DEFAULT_EMAIL = 'adshelp@cfa.harvard.edu',
            FEEDBACK_FORMS_ORIGIN = 'user_submission',
            BBB_FEEDBACK_ORIGIN = 'bbb_feedback',
            FEEDBACK_TEMPLATES = {
                'Missing References': 'missing_references.txt',
                'Associated Articles': 'associated_articles.txt',
                'Updated Record': 'updated_record.txt',
                'New Record': 'new_record.txt',
                'Bumblebee Feedback':'bumblebee_feedback.txt'
            },
            FEEDBACK_EMAILS = {
                'Missing References': 'ads@cfa.harvard.edu',
            },  
            MAIL_SUPPRESS_SEND=True,
            GOOGLE_RECAPTCHA_ENDPOINT = 'https://www.google.com/recaptcha/api/siteverify',
            GOOGLE_RECAPTCHA_PRIVATE_KEY = 'MY_PRIVATE_KEY'

        )
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
        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=json.dumps(general_feedback.data)
            )
        self.assertEqual(response.status_code, 200)

    def test_submitting_missing_references(self):
        """
        A generic test of the entire work flow of the feedback submission
        end point: submissions of missing references
        """

        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=json.dumps(missing_references.data)
            )
        self.assertEqual(response.status_code, 200)
        
    def test_submitting_associated(self):
        """
        A generic test of the entire work flow of the feedback submission
        end point: submissions of associated records
        """

        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=json.dumps(associated_errata.data)
            )
        self.assertEqual(response.status_code, 200)
    
    def test_submitting_associated_other(self):
        """
        A generic test of the entire work flow of the feedback submission
        end point: submissions of associated records of type 'other'
        """

        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=json.dumps(associated_other.data)
            )
        self.assertEqual(response.status_code, 200)

    def test_submitting_new_abstract(self):
        """
        A generic test of the entire work flow of the feedback submission
        end point: submissions of new abstract
        """

        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=json.dumps(new_abstract.data)
            )
        self.assertEqual(response.status_code, 200)

    def test_submitting_corrected_abstract(self):
        """
        A generic test of the entire work flow of the feedback submission
        end point: submissions of new abstract
        """

        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=json.dumps(corrected_abstract.data)
            )
        self.assertEqual(response.status_code, 200)

    def test_submitting_feedback_with_minimal_information(self):
        """
        Check they can send minimal information to the end point
        """
        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=json.dumps(general_feedback.data)
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
            'g-recaptcha-response': 'correct_response',
            'origin': 'bbb_feedback'
        }

        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=form_data
            )
        self.assertEqual(response.status_code, 404)
    
    def test_404_if_not_right_origin(self):
        """
        Checks the passed data. The endpoint expects specific values for the 'origin' attribute
        """
        # User fills the user feedback form
        form_data = {
            'name': 'Commenter',
            '_replyto': 'commenter@email.com',
            'g-recaptcha-response': 'correct_response',
            'origin': 'foobar'
        }

        # User presses submit on the feedback form
        url = url_for('userfeedback')
        with SlackWebService() as SLW, GoogleRecaptchaService() as GRS:
            response = self.client.post(
                url,
                data=form_data
            )
        self.assertEqual(response.status_code, 404)

    def test_404_if_not_right_subject(self):
        """
        Checks the passed data. For user submission feedback, the value _subject field
        determines the email template. Exception is thrown when this has an unexpected value.
        """
        # User fills the user feedback form
        form_data = {
            'name': 'Commenter',
            '_replyto': 'commenter@email.com',
            'g-recaptcha-response': 'correct_response',
            'origin': 'user_submission',
            '_subject': 'foo'
        }

        # User presses submit on the feedback form
        url = url_for('userfeedback')
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

    def test_email_body(self):
        """
        
        """

        email_body = UserFeedback().create_email_body(corrected_abstract.data)
        self.assertEqual(email_body, corrected_abstract.response)
        
        email_body = UserFeedback().create_email_body(new_abstract.data)
        self.assertEqual(email_body, new_abstract.response)
        
        email_body = UserFeedback().create_email_body(associated_other.data)
        self.assertEqual(email_body, associated_other.response)
        
        email_body = UserFeedback().create_email_body(missing_references.data)
        self.assertEqual(email_body, missing_references.response)
        
        email_body = UserFeedback().create_email_body(general_feedback.data)
        self.assertEqual(email_body, general_feedback.response)

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
