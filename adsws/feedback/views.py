# encoding: utf-8
"""
Views
"""

import json
import requests
import copy
from flask import current_app, request, render_template
from flask.ext.restful import Resource
from adsws.ext.ratelimiter import ratelimit, scope_func
from adsws.feedback.utils import err
from adsws.accounts.utils import verify_recaptcha, get_post_data
from werkzeug.exceptions import BadRequestKeyError
from utils import send_feedback_email, make_diff
from urllib import unquote

API_DOCS = 'https://github.com/adsabs/adsabs-dev-api'
ERROR_UNVERIFIED_CAPTCHA = dict(
    body='captcha was not verified',
    number=403
)
ERROR_MISSING_KEYWORDS = dict(
    body='Incorrect POST data, see the API docs {0}'
         .format(API_DOCS),
    number=404
)
ERROR_FEEDBACKFORM_PROBLEM = dict(
    body='Error while processing feedback form data',
    number=404
)
ERROR_EMAILBODY_PROBLEM = dict(
    body='Unable to generate email body',
    number=404
)
ERROR_UNKNOWN_ORIGIN = dict(
    body='No origin provided in feedback data',
    number=404
)
ERROR_WRONG_ENDPOINT = dict(
    body='Re-directed due to malformed request or incorrect end point',
    number=302
)
ERROR_EMAIL_NOT_SENT = dict(
    body='Delivery of feedback email to ADS failed!',
    number=404
)


class UserFeedback(Resource):
    """
    Forwards a user's feedback to Slack and/or email
    """
    decorators = [ratelimit.shared_limit_and_check("500/600 second", scope=scope_func)]

    @staticmethod
    def create_email_body(post_data):
        """
        Takes the data from the feedback and fills out the appropriate template
        :param post_data: the post data to fill out email template, dictionary expected
        :return: email body, string
        """
        # We will be manipulating the dictionary with POST data, so make a copy
        email_data = copy.copy(post_data)
        # Determine the origin of the feedback. There are some origin-specific actions
        origin = post_data.get('origin', 'NA')
        if origin == current_app.config['BBB_FEEDBACK_ORIGIN']:
            try:
                comments = email_data['comments']
            except BadRequestKeyError:
                raise
            email_data['_subject'] = 'Bumblebee Feedback'
            email_data['comments'] = post_data['comments'].encode('utf-8')
            used = ['channel', 'username', 'name', '_replyto', 'g-recaptcha-response']
            for key in used:
                email_data.pop(key, None)
        # Retrieve the appropriate template
        template = current_app.config['FEEDBACK_TEMPLATES'].get(email_data.get('_subject'))
        # For abstract corrections, we determine a diff from the original and updated records.
        # In case this fails we fall back on the POST data "diff" attribute that contains
        # the updated fields in Github "diff" format, URL encoded. For display purposes,
        # this needs to be decoded.
        if post_data.get('_subject') == 'Updated Record':
            try:
                email_data['diff'] = make_diff(post_data['original'], post_data['new'])
            except:
                email_data['diff'] = unquote(post_data.get('diff',''))
        # In the case of a new record the mail body will show a summary
        # In this summary it's easier to show a author list in the form of a string
        # We also attach the JSON data of the new record as a file
        if post_data.get('_subject') == 'New Record':
            try:
                email_data['new']['author_list'] = ";".join([a['name'] for a in post_data['new']['authors']])
            except:
                email_data['new']['author_list'] = ""
        # Construct the email body
        body = render_template(template, data=email_data)
        # If there is a way to insert tabs in the template, it should happen there
        # (currently, this only happens in the missing_references.txt template)
        body = body.replace('[tab]','\t')
        
        return body
    
    def post(self):
        """
        HTTP POST request
        :return: status code from the slack end point and for sending user feedback emails
        """

        post_data = get_post_data(request)

        current_app.logger.info('Received feedback of type {0}: {1}'.format(post_data.get('_subject'), post_data))

#        if not post_data.get('g-recaptcha-response', False) or \
#                not verify_recaptcha(request):
#            current_app.logger.info('The captcha was not verified!')
#            return err(ERROR_UNVERIFIED_CAPTCHA)
#        else:
#            current_app.logger.info('Skipped captcha!')
        # We only allow POST data from certain origins
        allowed_origins = [v for k,v in current_app.config.items() if k.endswith('_ORIGIN')]
        origin = post_data.get('origin', 'NA')
        if origin == 'NA' or origin not in allowed_origins:
            return err(ERROR_UNKNOWN_ORIGIN)
        # Some variable definitions
        email_body = ''
        slack_data = ''
        attachments=[]
        # Generate the email body based on the data in the POST payload
        try:
            email_body = self.create_email_body(post_data)
        except BadRequestKeyError as error:
            current_app.logger.error('Missing keywords: {0}, {1}'
                                     .format(error, post_data))
            return err(ERROR_MISSING_KEYWORDS)
        except Exception as error:
            current_app.logger.error('Fatal error creating email body: {0}'.format(error))
            return err(ERROR_EMAILBODY_PROBLEM)
        # Retrieve the name of the person submitting the feedback
        name = post_data.get('name', 'TownCrier')
        # There are some origin-specific actions
        if origin == current_app.config['FEEDBACK_FORMS_ORIGIN']:
            # The reply_to for feedback form data
            reply_to = post_data.get('email')
            # In the case of new or corrected records, attachments are sent along
            if post_data.get('_subject') == 'New Record':
                attachments.append(('new_record.json', post_data['new']))
            if post_data.get('_subject') == 'Updated Record':
                attachments.append(('updated_record.json', post_data['new']))
                attachments.append(('original_record.json', post_data['original']))
            # Prepare a minimal Slack message
            channel = post_data.get('channel', '#feedback')
            username = post_data.get('username', 'TownCrier')
            icon_emoji = current_app.config['FORM_SLACK_EMOJI']
            text = 'Received data from feedback form "{0}" from {1}'.format(post_data.get('_subject'), post_data.get('email'))
            slack_data = {
                'text': text,
                'username': username,
                'channel': channel,
                'icon_emoji': icon_emoji
            }
        elif origin == current_app.config['BBB_FEEDBACK_ORIGIN']:
            # The reply_to for the general feedback data
            reply_to = post_data.get('_replyto', 'TownCrier@lonelyvilla.ge')
            # Prepare the Slack message with submitted data
            text = '```Incoming Feedback```\n' + email_body
            channel = post_data.get('channel', '#feedback')
            username = post_data.get('username', 'TownCrier')
            icon_emoji = current_app.config['FEEDBACK_SLACK_EMOJI']
            slack_data = {
                'text': text,
                'username': username,
                'channel': channel,
                'icon_emoji': icon_emoji
            }
        print email_body
        # If we have an email body (should always be the case), send out the email
#        if email_body:
#            email_sent = False
#            try:
#                res = send_feedback_email(name, reply_to, post_data['_subject'], email_body, attachments=attachments)
#                email_sent = True
#            except Exception as e:
#                current_app.logger.error('Fatal error while processing feedback form data: {0}'.format(e))
#                email_sent = False
#            if not email_sent:
#                # If the email could not be sent, we can still log the data submitted
#                current_app.logger.error('Sending of email failed. Feedback data submitted by {0}: {1}'.format(post_data.get('email'), post_data))
#                return err(ERROR_EMAIL_NOT_SENT)
#        # If we have Slack data, post the message to Slack
#        if slack_data:
#            slack_data['text'] += '\n*sent to adshelp*: {0}'.format(email_sent)
#            try:
#                slack_response = requests.post(
#                    url=current_app.config['FEEDBACK_SLACK_END_POINT'],
#                    data=json.dumps(slack_data),
#                    timeout=60
#                )
#            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
#                return b'504 Gateway Timeout', 504
#            current_app.logger.info('slack response: {0}'
#                                    .format(slack_response.status_code))
#
#            # Slack annoyingly redirects if you have the wrong end point
#            current_app.logger.info('Slack API' in slack_response.text)
#
#            if 'Slack API' in slack_response.text:
#                return err(ERROR_WRONG_ENDPOINT)
#            elif slack_response.status_code == 200:
#                return {}, 200
#            else:
#                return {'msg': 'Unknown error'}, slack_response.status_code

        return {}, 200
