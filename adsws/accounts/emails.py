class PASSWORD_RESET_EMAIL:
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

class VERIFICATION_EMAIL:
    msg = '''
    Hi,

    Someone (probably you) has registered this email address with the NASA-ADS (http://ui.adsabs.harvard.edu).

    To confirm this action, please visit
    <a href="{endpoint}">{endpoint}</a> with your browser.

    If this is a mistake, then just ignore this email.

    -The ADS team'''
    subject = "[ADS] Please verify your email address"
    salt = 'verification-email'