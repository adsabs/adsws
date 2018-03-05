# coding=utf-8
"""
Template emails for account maintence activities. Note that
the salt does not need to be secure for these particular activities,
since signing with the secret key is enough for these short lived
operations.
"""

open_tag = '''<p style="font-family: sans-serif; font-size: 14px; font-weight: normal; margin: 0; Margin-bottom: 15px;">'''

html_template = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html>
        <head>
            <meta name="viewport" content="width=device-width">
            <meta http-equiv="Content-Type" content="text/html charset=UTF-8" />
        </head>
        <body>
            <table border="0" cellpadding="0" cellspacing="0" height="100%" width="100%" id="bodyTable" style="background-color: #E0E0E0;">
                <tr>
                    <td align="center" valign="top">
                        <table border="0" cellpadding="10" cellspacing="0" width="600" id="emailContainer">
                            <tr>
                                <td align="center" valign="top">
                                    <table border="0" cellpadding="20" cellspacing="0" width="100%" id="emailHeader">
        
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" valign="top">
                                    <table border="0" cellpadding="20" cellspacing="0" width="100%" id="emailBody" style="background-color: #ffffff;">
                                        <tr>
                                            <td align="center" valign="top" background="https://ui.adsabs.harvard.edu/styles/img/background.jpg" style="width:100%; background-color: #150E35" >
                                                <img src="https://ui.adsabs.harvard.edu/styles/img/ads_logo.png" alt="Astrophysics Data System" style="width: 70%; color: #ffffff; font-size: 34px; font-family: sans-serif;"/> 
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="left" valign="top">
                                                {msg}
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" valign="top">
                                    <table border="0" cellpadding="20" cellspacing="0" width="100%" id="emailFooter" style="color: #999999; font-size: 12px; text-align: center; font-family: sans-serif;">
                                        <tr>
                                            <td align="center" valign="top">
                                                <p> This message was sent to {email_address}. </p>
                                                <p> &copy; SAO/NASA <a href="https://ui.adsabs.harvard.edu">Astrophysics Data System</a> <br> 60 Garden Street <br> Cambridge, MA</p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """

class Email(object):
    """
    Data structure that contains email content data
    """
    msg_plain = ''
    msg_html = ''
    subject = ''
    salt = ''

class PasswordResetEmail(Email):
    msg_plain = '''Hi,

You’ve recently requested to reset your password for the NASA ADS account associated with this email address. 
Copy and paste the link below into your browser to reset it. 

{endpoint}

This link is only valid for the next 24 hours.

If you didn't request this, you can safely ignore this email.

- the ADS team
    '''
    msg = '''{open_tag}Hi,</p>

{open_tag}You've recently requested to reset your password for the <a href="https://ui.adsabs.harvard.edu">NASA ADS</a> 
account associated with this email address. Click the link below to reset it:</p>

{open_tag}<a href="{endpoint}">{endpoint}</a></p>

{open_tag}This link is only valid for the next 24 hours.</p>

{open_tag}If you didn't request this, you can safely ignore this email.</p>

{open_tag}- the ADS team</p>'''.format(open_tag=open_tag,endpoint='''{endpoint}''')
    msg_html = html_template.format(msg=msg,email_address='''{email_address}''')
    subject = "[ADS] Password reset"
    salt = 'password-reset-email'


class WelcomeVerificationEmail(Email):
    msg_plain = '''Hi,

Welcome to the new NASA ADS! To finish setting up your account, please confirm your email address by copying and 
pasting the link below into your browser:

{endpoint}

This link is only valid for the next 24 hours. 

If you didn't request this, you can safely ignore this email.

- the ADS team
    '''

    msg = '''{open_tag}Hi,</p>

{open_tag}Welcome to the new <a href="https://ui.adsabs.harvard.edu">NASA ADS</a>! To finish setting up your account, 
please confirm your email address:</p>

{open_tag}<a href="{endpoint}">{endpoint}</a></p>

{open_tag}This link is only valid for the next 24 hours.</p>

{open_tag}If you didn't request this, you can safely ignore this email.</p>

{open_tag}- the ADS team</p>'''.format(open_tag=open_tag,endpoint='''{endpoint}''')
    msg_html = html_template.format(msg=msg,email_address='''{email_address}''')
    subject = "[ADS] Please verify your email address"
    salt = 'verification-email'

class VerificationEmail(Email):
    msg_plain = '''Hi,

You've recently requested to change the email address associated with your NASA ADS account. To confirm this change, 
please copy and paste the link below into your browser:

{endpoint}

This link is only valid for the next 24 hours.

If you didn't request this, you can safely ignore this email.

- the ADS team
    '''

    msg = '''{open_tag}Hi,</p>

{open_tag}You've recently requested to change the email address associated with your 
<a href="https://ui.adsabs.harvard.edu">NASA ADS</a> account. To confirm this change, please click the link below:</p>

{open_tag}<a href="{endpoint}">{endpoint}</a></p>

{open_tag}This link is only valid for the next 24 hours.</p>

{open_tag}If you didn't request this, you can safely ignore this email.</p>

{open_tag}- the ADS team</p>'''.format(open_tag=open_tag,endpoint='''{endpoint}''')
    msg_html = html_template.format(msg=msg,email_address='''{email_address}''')
    subject = "[ADS] Please verify your email address"
    salt = 'verification-email'

class EmailChangedNotification(Email):
    msg_plain = '''Hi,

You’ve recently requested to change the email address associated with your NASA ADS account.

A verification email has been sent to the new email address. After the new email address has been confirmed, 
this email address will no longer be associated with your account.

If you didn't request this, please reply to this email, or contact the support team at adshelp@cfa.harvard.edu directly.

- the ADS team'''

    msg = '''{open_tag}Hi,</p>

{open_tag}You’ve recently requested to change the email address associated with your 
<a href="https://ui.adsabs.harvard.edu">NASA ADS</a> account. </p>

{open_tag}A verification email has been sent to the new email address. After the new email address has been confirmed, 
this email address will no longer be associated with your account.</p>

{open_tag}If you didn't request this, please reply to this email, or contact the 
<a href="mailto:adshelp@cfa.harvard.edu">support team</a> directly.</p>

{open_tag}- the ADS team</p> '''.format(open_tag=open_tag)

    msg_html = html_template.format(msg=msg,email_address='''{email_address}''')
    subject = "[ADS] An email change has been requested"