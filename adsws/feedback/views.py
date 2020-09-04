# encoding: utf-8
"""
Views
"""

import json
import requests
from flask import current_app, request, render_template
from flask.ext.restful import Resource
from adsws.ext.ratelimiter import ratelimit, scope_func
from adsws.feedback.utils import err
from adsws.accounts.utils import verify_recaptcha, get_post_data
from werkzeug.exceptions import BadRequestKeyError
from utils import send_feedback_email
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


class SlackFeedback(Resource):
    """
    Forwards a user's feedback to slack chat using a web end
    """
    decorators = [ratelimit.shared_limit_and_check("500/600 second", scope=scope_func)]

    @staticmethod
    def prettify_post(post_data):
        """
        Converts the given input into a prettified version
        :param post_data: the post data to prettify, dictionary expected
        :return: prettified_post data, dictionary
        """
        channel = post_data.get('channel', '#feedback')
        username = post_data.get('username', 'TownCrier')

        name = post_data.get('name', 'TownCrier')
        reply_to = post_data.get('_replyto', 'TownCrier@lonelyvilla.ge')

        try:
            comments = post_data['comments']
        except BadRequestKeyError:
            raise

        text = [
            '*Commenter*: {}'.format(name),
            '*e-mail*: {}'.format(reply_to),
            '*Feedback*: {}'.format(comments.encode('utf-8')),
        ]

        used = ['channel', 'username', 'name', '_replyto', 'comments', 'g-recaptcha-response']
        for key in post_data:
            if key in used:
                continue
            text.append('*{}*: {}'.format(key, post_data[key]))
        text = '\n'.join(text)

        feedback_email = 'no email sent'
        if post_data.has_key('_replyto') and post_data.has_key('name'):
            try:
                res = send_feedback_email(name, reply_to, "Bumblebee Feedback", text)
                feedback_email = 'success'
            except Exception as e:
                current_app.logger.info('Sending feedback mail failed: %s' % str(e))
                feedback_email = 'failed'

        text = '```Incoming Feedback```\n' + text + '\n*sent to adshelp*: {}\n'.format(feedback_email)

        icon_emoji = current_app.config['FEEDBACK_SLACK_EMOJI']
        prettified_data = {
            'text': text,
            'username': username,
            'channel': channel,
            'icon_emoji': icon_emoji
        }
        return prettified_data

    @staticmethod
    def create_email_body(post_data):
        """
        Takes the data from the feedback forms and fills out the appropriate template
        :param post_data: the post data to fill out email template, dictionary expected
        :return: email body, string
        """
        # Retrieve the appropriate template
        template = current_app.config['FEEDBACK_TEMPLATES'].get(post_data.get('_subject'))
        # For abstract corrections, the POST payload has a "diff" attribute that contains
        # the updated fields in Github "diff" format, URL encoded. For display purposes,
        # this needs to be decoded.
        if post_data.has_key('diff'):
            post_data['diff'] = unquote(post_data['diff'])
        # In the case of a new record the mail body will show a summary
        # In this summary it's easier to show a author list in the form of a string
        # We also attach the JSON data of the new record as a file
        if post_data.get('_subject') == 'New Record':
            try:
                post_data['new']['author_list'] = ";".join([a['name'] for a in post_data['new']['authors']])
            except:
                post_data['new']['author_list'] = ""
        # Construct the email body
        body = render_template(template, data=post_data)
        # If there is a way to insert tabs in the template, it should happen there
        # (currently, this only happens in the missing_references.txt template)
        body = body.replace('[tab]','\t')
        
        return body        

    @staticmethod
    def process_feedbackform_submission(post_data, body):
        """
        Takes the data from the feedback forms and fills out the appropriate template
        :param post_data: the post data to fill out email template, dictionary expected
        :param body: email body
        :return: success message, string
        """
        # List to hold attachments to be sent along
        attachments=[]
        if post_data.get('_subject') == 'New Record':
            attachments.append(('new_record.json', post_data['new']))
        if post_data.get('_subject') == 'Updated Record':
            attachments.append(('updated_record.json', post_data['new']))
            attachments.append(('original_record.json', post_data['original']))

        feedback_email = 'no email sent'
        if post_data.has_key('email') and post_data.has_key('name'):
            try:
                res = send_feedback_email(post_data['name'], post_data['name'], post_data['_subject'], body, attachments=attachments)
                feedback_email = 'success'
            except Exception as e:
                current_app.logger.info('Sending feedback mail failed: %s' % str(e))
                feedback_email = 'failed'

        return feedback_email
    
    def post(self):
        """
        HTTP POST request
        :return: status code from the slack end point
        """

        post_data = get_post_data(request)

        current_app.logger.info('Received feedback: {0}'.format(post_data))


        if not post_data.get('g-recaptcha-response', False) or \
                not verify_recaptcha(request):
            current_app.logger.info('The captcha was not verified!')
            return err(ERROR_UNVERIFIED_CAPTCHA)
        else:
            current_app.logger.info('Skipped captcha!')
        origin = post_data.get('origin', 'NA')
        if origin == current_app.config['FEEDBACK_FORMS_ORIGIN']:
            current_app.logger.info('Received data from feedback form "{0}" from {1} ({2})'.format(post_data.get('_subject'), post_data.get('name'), post_data.get('email')))
            try:
                email_body = self.create_email_body(post_data)
            except Exception as error:
                current_app.logger.error('Fatal error creating email body: {0}'.format(error))
                return err(ERROR_EMAILBODY_PROBLEM)
            try:
                email_sent = self.process_feedbackform_submission(post_data, email_body)
            except Exception as error:
                current_app.logger.error('Fatal error while processing feedback form data: {0}'.format(error))
                return err(ERROR_FEEDBACKFORM_PROBLEM)
        elif origin == current_app.config['BBB_FEEDBACK_ORIGIN']:
            try:
                current_app.logger.info('Prettifiying post data: {0}'
                                        .format(post_data))
                formatted_post_data = json.dumps(self.prettify_post(post_data))
                current_app.logger.info('Data prettified: {0}'
                                        .format(formatted_post_data))
            except BadRequestKeyError as error:
                current_app.logger.error('Missing keywords: {0}, {1}'
                                         .format(error, post_data))
                return err(ERROR_MISSING_KEYWORDS)

            try:
                slack_response = requests.post(
                    url=current_app.config['FEEDBACK_SLACK_END_POINT'],
                    data=formatted_post_data,
                    timeout=60
                )
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                return b'504 Gateway Timeout', 504
            current_app.logger.info('slack response: {0}'
                                    .format(slack_response.status_code))

            # Slack annoyingly redirects if you have the wrong end point
            current_app.logger.info('Slack API' in slack_response.text)

            if 'Slack API' in slack_response.text:
                return err(ERROR_WRONG_ENDPOINT)
            elif slack_response.status_code == 200:
                return {}, 200
            else:
                return {'msg': 'Unknown error'}, slack_response.status_code
        else:
            return err(ERROR_UNKNOWN_ORIGIN)
        return {}, 200
