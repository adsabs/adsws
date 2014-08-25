'''
Bridge to the Classic users
'''
from flask import current_app as app
import requests
import sys
import traceback


__all__ = ['ClassicUserInfo', 'ClassicUser']


class ClassicUserInfo():
    """Read-Only info about the user accounts from ADS Classic"""
    
    def __init__(self, login, password=None):
        user = self._get_data(login, password)
        self._load(user)
        
        
    def _load(self, user):
        self.uid = user.myadsid or -1
        self.login = self.email = user.email or ''
        self.lastname = user.lastname or ''
        self.firstname = user.firstname or ''
        self.cookie = user.cookie
        self._user = user
        
    def _get_data(self, login, password=None):
        """Load JSON structure from the ADS Classic.
        
        ADS Classic exposes user info in the following format:
    
        curl 'http://adsabs.harvard.edu/cgi-bin/maint/manage_account/credentials?man_ads2=1&man_email=<email>&man_cmd=elogin'
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
        return self.uid
    
    def is_authenticated(self):
        return self._user.loggedin
    
    def is_real_user(self):
        if self._user['message'] == 'ACCOUNT_NOTFOUND':
            return False
        else:
            return True
        
    def _request(self, parameters, headers):
        return user_query(parameters, headers, app.config.get('CLASSIC_LOGIN_URL'))

class ClassicUser(ClassicUserInfo):
    
    def create(self, username, password, firstname=None, lastname=None):
        """Create an user in ADS Classic"""
        parameters = {'man_nemail':username, 'man_npasswd': password, 'man_vpasswd':password, 'man_name':'%s|%s' % (firstname, lastname),'man_cmd':'Update Record'}
        headers = {'User-Agent':'ADS Script Request Agent'}
        
        # TODO:rca what are the error states here?
        data = self._request(parameters, headers)
        if data:
            self._load(data)
            
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
        
        parameters = {'man_cmd':'Update Record', 'man_email':curusername, 'man_passwd':curpassword}
        parameters.update(kwargs)
        
        headers = {'User-Agent':'ADS Script Request Agent'}
        
        # TODO:rca what are the error states here?
        data = self._request(parameters, headers)
        if data:
            self._load(data)
    

    def reset_password(self, curusername, newpassword):
        """
        function to update the password without knowing the old one.
        It can be implemented also as a particular case of update_classic_password
        """
        parameters = {'man_cmd':'eupdate', 'man_npasswd':newpassword, 'man_vpasswd':newpassword, 'man_email':curusername}
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
    
    r = requests.get(service_url, params=parameters, headers=headers)    
    r.raise_for_status()

    
    try:
        user_json = r.json()
    except Exception, e:
        exc_info = sys.exc_info()
        app.logger.error("Author JSON decode error: %s, %s\n%s" % (exc_info[0], exc_info[1], traceback.format_exc()))
        r = None
        user_json = {}
    return user_json



