"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""
from flask import current_app
from flask.ext.mail import Message
import json

def send_feedback_email(name, sender, subject, data, attachments=None):
    # Allow the default recipient to be overriden depending on email subject
    email = current_app.config['FEEDBACK_EMAILS'].get(subject, current_app.config['DEFAULT_EMAIL'])
    msg = Message(subject="%s from %s (%s)" % (subject, name, sender),
                  recipients=[email],
                  sender=("ADS Administration", current_app.config['DEFAULT_EMAIL']),
                  reply_to=(name, sender),
                  body=data)
    if attachments:
        for attachment in attachments:
            # Each entry is a tuple of file name and JSON data
            msg.attach(attachment[0], "application/json", json.dumps(attachment[1]))
    current_app.extensions['mail'].send(msg)
    current_app.logger.info('Successfully sent email: data submitted by {0}, sent to {1} (form: {2})'.format(sender, email, subject))
    return msg

def err(error_dictionary):
    """
    Formats the error response as wanted by the Flask app
    :param error_dictionary: name of the error dictionary

    :return: tuple of error message and error number
    """
    return {'error': error_dictionary['body']}, error_dictionary['number']
