"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""
from flask import current_app
from flask.ext.mail import Message
import json
#from dictdiffer import diff
from jsondiff import diff

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

def make_diff(original, updated):

    diffdata = diff(original, updated)

    results = ''
    if diffdata.has_key('comments'):
        results += "\n\nComments: %s\n\n" % diffdata['comments']
    for field, changes in diffdata.items():
        if field == 'comments':
            continue
        results += ">>>> %s\n" % field
        if isinstance(changes,dict):
            for k,v in changes.items():
                results += "{0} -- {1}\n".format(k,v)
        elif isinstance(changes,list):
            for item in changes:
                try:
                    results += "{0}\t{1}\n".format(updated['bibcode'], item.replace('(bibcode) ','').replace('(reference) ',''))
                except:
                    results += str(item) + "\n"
        else:
            results += str(changes) + "\n"
        results += ">>>>\n"

    return results

def err(error_dictionary):
    """
    Formats the error response as wanted by the Flask app
    :param error_dictionary: name of the error dictionary

    :return: tuple of error message and error number
    """
    return {'error': error_dictionary['body']}, error_dictionary['number']


