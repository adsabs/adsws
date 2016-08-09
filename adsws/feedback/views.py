# encoding: utf-8
"""
Views
"""

import json
import requests
from flask import current_app, request
from flask.ext.restful import Resource
from adsws.ext.ratelimiter import ratelimit, scope_func
from adsws.feedback.utils import err
from adsws.accounts.utils import verify_recaptcha, get_post_data
from werkzeug.exceptions import BadRequestKeyError
from utils import send_feedback_email

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
ERROR_WRONG_ENDPOINT = dict(
    body='Re-directed due to malformed request or incorrect end point',
    number=302
)


class SlackFeedback(Resource):
    """
    Forwards a user's feedback to slack chat using a web end
    """
    decorators = [ratelimit(50, 600, scope_func=scope_func)]

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

        feedback_email = 'no email sent'
        if post_data.has_key('_replyto') and post_data.has_key('name'):
            try:
                res = send_feedback_email(name, reply_to, comments)
                feedback_email = 'success'
            except Exception as e:
                current_app.logger.info('Sending feedback mail failed: %s' % str(e))
                feedback_email = 'failed'

        icon_emoji = current_app.config['FEEDBACK_SLACK_EMOJI']

        text = [
            '```Incoming Feedback```',
            '*Commenter*: {}'.format(name),
            '*e-mail*: {}'.format(reply_to),
            '*Feedback*: {}'.format(comments),
            '*sent to adshelp*: {}'.format(feedback_email)
        ]

        used = ['channel', 'username', 'name', '_replyto', 'comments', 'g-recaptcha-response']
        for key in post_data:
            if key in used:
                continue
            text.append('*{}*: {}'.format(key, post_data[key]))

        text = '\n'.join(text)

        prettified_data = {
            'text': text,
            'username': username,
            'channel': channel,
            'icon_emoji': icon_emoji
        }
        return prettified_data

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

        slack_response = requests.post(
            url=current_app.config['FEEDBACK_SLACK_END_POINT'],
            data=formatted_post_data
        )
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
