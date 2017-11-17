'''
Bridge to the Classic users
'''
from flask import current_app as app
import requests


__all__ = ['ClassicUserInfo', 'ClassicUser']


class ClassicUserInfo():
    """Read-Only info about the user accounts from ADS Classic"""

    def __init__(self, login, password=None):
        self._passwd_info = None
        self.msg = None
        self.uid = -1
        self.lastname = None
        self.firstname = None
        self._passwd_info = 0
        user = self._get_data(login, password)
        self._load(user, password)


    def _load(self, user, password=None):
        if not isinstance(user, dict):
            raise Exception("Wrong data received from ADS Classic")

        if not 'email' in user:
            raise Exception("Every user datastruct must contain 'email'")

        self.uid = int(user.get('myadsid', '-1'))
        self.login = self.email = user.get('email', '')
        self.lastname = user.get('lastname', '')
        self.firstname = user.get('firstname', '')
        self.cookie = user.get('cookie', '')
        self.msg = user.get('message', '')
        self.loggedin = int(user.get('loggedin', '0'))

        self._passwd_info = 0
        if password:
            if self.msg == 'LOGGED_IN':
                self._passwd_info = 1
            else:
                self._passwd_info = -1

        self._user = user

    def _get_data(self, login, password=None):
        """Load JSON structure from the ADS Classic.

        ADS Classic exposes user info in the following format:

        curl 'http://adsabs.harvard.edu/cgi-bin/maint/manage_account/credentials?\
            man_ads2=1&man_email=<email>&man_cmd=elogin'
        {
          "email": "<email>",
          "cookie": "4201071e52",
          "tmp_cookie": "",
          "openurl_srv": "http://sfx.hul.harvard.edu/hvd",
          "openurl_icon": "http://sfx.hul.harvard.edu/hvd/sfx.gif",
          "loggedin": "0",
          "myadsid": "316870278",
          "lastname": "John",
          "firstname": "Doe",
          "fullname": "John Doe",
          "message": "PASSWORD_REQUIRED",
          "request": {
              "man_cookie": "",
              "man_email": "email@cfa.harvard.edu",
              "man_nemail": "",
              "man_passwd": "",
              "man_npasswd": "",
              "man_vpasswd": "",
              "man_name": "",
              "man_url": "",
              "man_cmd": "4"
           }
        }
        """

        parameters = {'man_email':login, 'man_cmd':'elogin'}
        if password:
            parameters.update({'man_passwd':password})
        headers = {'User-Agent':'ADS Script Request Agent'}
        return self._request(parameters, headers)

    def get_id(self):
        '''-1 means id was not supplied; 0 means account doesn't exist at all'''
        return self.uid

    def is_authenticated(self):
        return bool(self.loggedin)

    def is_real_user(self):
        if self.msg == 'ACCOUNT_NOTFOUND':
            return False
        if not self.uid or self.uid <= 0:
            return False
        return True

    def get_name(self):
        if 'fullname' in self._user and self._user['fullname']:
            return self._user['fullname']
        first = last = ''
        if 'firstname' in self._user and self._user['firstname']:
            first = self._user['firstname']
        if 'lastname' in self._user and self._user['lastname']:
            last = self._user['lastname']
        if first and last:
            return '%s %s' % (first, last)
        if first:
            return first
        return last

    def passwd_info(self):
        """Flag telling you whether the user account was loaded together
        with a password and whether the password was correct. We do not
        store passwords together with the User object for security reasons

        :return:
            -1 = password was used, but was incorrect
             0 = no password was used
             1 = password used and was correct
        """
        return self._passwd_info


    def _request(self, parameters, headers):
        return user_query(parameters, headers, app.config.get('CLASSIC_LOGIN_URL'))

class ClassicUser(ClassicUserInfo):

    def update_passwd(self, username, passwd, new_passwd):
        self.update(username, passwd, man_npasswd=new_passwd,
                           man_vpasswd=new_passwd)
        if self.is_authenticated():
            return True
        return False

    def update(self, curusername, curpassword, **kwargs):
        """Updates the record on ADS Classic.

        To update name:
            :man_name: firstname|lastname

        To set a new password:
            :man_npasswd: new password
            :man_vpasswd: new password

        To update user name:
            :man_nemail: new user name

        """

        parameters = {'man_cmd':'Update Record', 'man_email':curusername,
                      'man_passwd':curpassword}
        parameters.update(kwargs)

        headers = {'User-Agent':'ADS Script Request Agent'}

        # TODO:rca what are the error states here?
        data = self._request(parameters, headers)
        if data:
            self._load(data)
        return data


    def reset_password(self, curusername, newpassword):
        """
        function to update the password without knowing the old one.
        It can be implemented also as a particular case of update_classic_password
        """
        parameters = {'man_cmd':'eupdate', 'man_npasswd':newpassword,
                      'man_vpasswd':newpassword, 'man_email':curusername}
        headers = {'User-Agent':'ADS Script Request Agent'}
        # TODO:rca what are the error states here?
        data = self._request(parameters, headers)
        if data:
            self._load(data)




def user_query(parameters, headers, service_url):
    """
    function that performs a get request and returns a json object
    """
    #add necessary general parameter
    parameters['man_ads2'] = '1'

    try:
        r = requests.get(service_url, params=parameters, headers=headers, timeout=60)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        raise
    r.raise_for_status()
    return r.json()

    #    user_json = r.json()
    #except Exception, e:
    #    exc_info = sys.exc_info()
    #    app.logger.error("Author JSON decode error: %s, %s\n%s" % (exc_info[0], exc_info[1], traceback.format_exc()))
    #    r = None
    #    user_json = {}
    #return user_json



