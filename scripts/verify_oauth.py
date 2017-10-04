
import mechanize
import json
import urllib
import requests
import sys
import getpass

"""
A utility script to test OAuth token dance; you have to have
mechanize and requests libraries installed:

    pip install -U mechanize html5lib requests

First, make sure that you have an account with the ADS site.
You can choose from the following:

    - sandbox: devui.adsabs.harvard.edu
    - production: ui.adsabs.harvard.edu
    
In both cases, there is a 'register' in the top right corner
of the user interface.

After you registered (and confirmed) your account. You can 
call the script.

Usage:

    python test_oauth.py <username1> <password1> <username2> <password2>
    
"""




def dance_oauth_dance(api_url='https://devapi.adsabs.harvard.edu', 
                    admin_name='admin@myservice.com', 
                    admin_password='adminadmin',
                    user_name='user@ads', 
                    user_password='testtest',
                    redirect_uri='https://myserver.com/myservice',
                    scopes='user api'):
    
    # let's pretend we have two different users; one is the 'admin' and owns the 'OAuth' application
    # the other one is the 'user' who grants 'admin' access to his own data (using scopes)
    admin_browser = login_with_ads(api_url, admin_name, admin_password)
    user_browser = login_with_ads(api_url, user_name, user_password)
    
    # bootstrap the OAuth application (this application will belong to admin)
    # this needs to happen only once - and in fact, once created - we don't
    # allow you to change redirect_uri or 'scopes' (you can always contact
    # ADS to do that)
    oauth_application = bootstrap_oauth_application(api_url, admin_browser, redirect_uri, scopes)
    
    
    # now imagine that the user came to your website; you want to get access to their private libraries
    # so to do that you have to redirect them back to ADS. ADS will present them if they want to
    # give you access; if they do, you will receive a 'code' that can be exchanged for an 'access_token'
    code = ask_for_authorization_code(user_browser, api_url, scopes, oauth_application['client_id'])
    
    
    # the user was redirected to '<redirect_uri>?code=.....' (that's your web server)
    # so right now the user was redirected back to us, we have to exchange the code
    response = exchange_code_for_token(api_url, oauth_application, code, scopes, redirect_uri)
    
    
    # ok, this should be it
    print 'Response from the server'
    print response
    
    # let's use the new access token for something useful
    print 'Using the new access_token for searching'
    r = requests.get(api_url + '/v1/search/query', params={'q': '*:*'}, headers={'Authorization': 'Bearer:'  + response['access_token']})
    print r.text
    


def login_with_ads(base_url, username, password):    
    
    browser = mechanize.Browser()
    
    # login
    browser.open(base_url + '/login')
    browser.select_form(nr = 0)
    browser.form['email'] = username
    browser.form['password'] = password
    browser.submit()
    
    # verify we are logged in
    d = browser.response().get_data()
    assert username in d
    return browser


def bootstrap_oauth_application(base_url, browser, redirect_uri, scopes):
    print 'Creating OAuth application at:'
    print base_url + '/v1/accounts/bootstrap?redirect_uri={redirect_uri}&scope={scopes}'.format(redirect_uri=urllib.quote(redirect_uri), scopes=urllib.quote(scopes))
    
    # create OAuth client and set the redirect_uri
    browser.open(base_url + '/v1/accounts/bootstrap?redirect_uri={redirect_uri}&scope={scopes}'.format(redirect_uri=urllib.quote(redirect_uri), scopes=urllib.quote(scopes)))
    
    # in response, the ADS returns the client_id and client_secret info
    data = json.loads(browser.response().get_data())
    print 'Response:', data
    
    assert 'client_secret' in data
    return data
    

def ask_for_authorization_code(browser, base_url, scopes, client_id):
    print 'Redirecting user to: '
    print base_url + '/oauth/authorize?scope={scopes}&client_id={client_id}&response_type=code'.format(scopes=urllib.quote(scopes), client_id=client_id)
    
    # the rest is what happens in the browsers of your users
    browser.open(base_url + '/oauth/authorize?scope={scopes}&client_id={client_id}&response_type=code'.format(scopes=urllib.quote(scopes), client_id=client_id))
    
    # if the user is not logged in, he/she will be automatically redirected to the /login page
    # but since we are already logged in, we'll be presented with the form that we can accept/decline
    # uncomment to see the html page
    # print browser.response().get_data()
    
    # select the first button (submit) 
    browser.select_form(nr=0)
    
    try:
        browser.submit(nr=0)
    except Exception, e:
        if '403' in str(e) or '404' in str(e):
            print 'Ignoring 40x errors: ' + str(e)
        else:
            raise 
    
    # we should have been redirected
    redirect_url = browser.response().geturl()
    print 'Server returned (?)', redirect_url
    return redirect_url.split('code=')[1]


def exchange_code_for_token(base_url, oauth_app, code, scopes, redirect_uri):
    # we must supply the same scopes/redirect_uri as in the first step!
    client_id = oauth_app['client_id']
    client_secret = oauth_app['client_secret']
    
    headers = {'Authorization': 'Bearer:%s' % oauth_app['access_token']}
    
    r = requests.post(base_url + '/oauth/token', data={'client_id': client_id, 
                                                       'client_secret': client_secret, 
                                                       'grant_type': 'authorization_code', 
                                                       'code': code, 
                                                       'scope': scopes, 
                                                       'redirect_uri': redirect_uri},
                                                #headers=headers, # causes invalid_client error
                                                       )
    return json.loads(r.text)


if __name__ == '__main__':
    if len(sys.argv) == 5:
        print 'Logging in with admin=%s, and user=%' % (sys.argv[1], sys.argv[3])
        dance_oauth_dance(admin_name=sys.argv[1], admin_password=sys.argv[2], 
                    user_name=sys.argv[3], user_password=sys.argv[4])
    elif len(sys.argv) == 3:
        print 'Logging in with admin=%s, and user=%' % (sys.argv[1], sys.argv[2])
        dance_oauth_dance(admin_name=sys.argv[1], admin_password=sys.argv[2], 
                    user_name=sys.argv[1], user_password=sys.argv[2])
    else:
        
        kws = {}
        for x in ['admin_name', 'admin_password', 'user_name', 'user_password', 'api_url', 'scopes', 'redirect_uri']:
            if 'pass' in x:
                kws[x] = getpass.getpass('%s:' % x)
            else:
                kws[x] = raw_input('%s:' % x)
        print 'Running with', map(lambda x: (x[0], 'pass' in x[0] and '***' or x[1]), kws.items())
        dance_oauth_dance(**kws)
