"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""
from flask import current_app
from flask.ext.mail import Message

def send_feedback_email(name, sender, feedback):
    help_email = current_app.config['FEEDBACK_EMAIL']
    msg = Message(subject="Bumblebee Feedback from %s (%s)" % (name, sender),
                  recipients=[help_email],
                  sender=("adshelp", help_email),
                  reply_to=(name, sender),
                  body=feedback)
    current_app.extensions['mail'].send(msg)
    return msg

def err(error_dictionary):
    """
    Formats the error response as wanted by the Flask app
    :param error_dictionary: name of the error dictionary

    :return: tuple of error message and error number
    """
    return {'error': error_dictionary['body']}, error_dictionary['number']
