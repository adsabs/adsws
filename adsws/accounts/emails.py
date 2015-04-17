"""
Template emails for account maintence activities. Note that
the salt does not need to be secure for these particular activities,
since signing with the secret key is enough for these short lived
operations.
"""

class Email(object):
    """
    Data structure that contains email content data
    """
    msg = ''
    subject = ''
    salt = ''


class PasswordResetEmail(Email):
    msg = '''Hi,
Someone (probably you) has requested a password reset on the account associated with this email address.

To reset your password, please visit
<a href="{endpoint}">{endpoint}</a> with your browser.

This link will be valid for the next 10 minutes.

If this is a mistake, then just ignore this email.

-The ADS team
    '''
    subject = "[ADS] Password reset"
    salt = 'password-reset-email'


class VerificationEmail(Email):
    msg = '''
Hi,

Someone (probably you) has registered this email address with the NASA-ADS (http://ui.adsabs.harvard.edu).

To confirm this action, please visit
<a href="{endpoint}">{endpoint}</a> with your browser.

If this is a mistake, then just ignore this email.

-The ADS team'''
    subject = "[ADS] Please verify your email address"
    salt = 'verification-email'


class EmailChangedNotification(Email):
    msg = '''
Hi,

Someone (probably you) has just changed the email associated with this account.

A verification email to the new address was sent. After visiting the verification link therein, this email will no longer be associated with this account.

If you need further support, please contact ads@cfa.harvard.edu.

-The ADS team'''
    subject = "[ADS] An email change has been requested"