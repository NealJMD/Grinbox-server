""" Server for Grinbox """
import web
import model
import simplejson as json
import email
import oauth2
import time
import urllib2
import grinbox_classifier
import grinbox_utils as gutils
import random

### Url mappings

urls = (
    '/', 'Index',
    '/login', 'Login',
    '/oauth2callback', 'Login',
    '/get-mail-with-classifications', 'Retrieve'
)

codes = {   'google_client_secret': '1Qwkrj7tlRE1KgnXEFQvtoPZ',
            'google_client_id': '1056643587877',
            'authentication_identifier': 'NLA62413609',
            'oauth_redirect_uri': 'http://127.0.0.1:8080/oauth2callback' }

### Templates
render = web.template.render('templates', base='base')
classifier = grinbox_classifier.GrinboxClassifier(relearn=False)

class Retrieve:
    def GET(self):
        url_params = web.input(recipient='none', quantity=100, threading='threading')
        if url_params.recipient == 'none': return web.notfound()
        address = url_params.recipient
        if len(gutils.get_email_address(address)) < 2: return web.notfound()
        token = gutils.get_auth_token(address)
        if len(token) < 2: return web.forbidden()
        try:
            classified_mail = gutils.fetch_and_classify_recent_mail(token, address, 0, 100)
        except:
            return web.forbidden()
        if url_params.threading != 'threading': return json.dumps(classified_mail)
        classified_threads = {}
        # could just sort and would probably be much more efficient
        for msg in classified_mail:
            if msg['subject'] not in classified_threads:
                classified_threads[msg['subject']] = msg
            elif gutils.earlier_time(classified_threads[msg['subject']]['time'], msg['time']) == msg['time']:
                    classified_threads[msg['subject']] = msg
        return json.dumps([msg for (subj, msg) in classified_threads.iteritems()])

class Index:

    form = web.form.Form(
        web.form.Textbox('title', web.form.notnull, 
            description="I need to:"),
        web.form.Button('Add todo'),
    )

    def GET(self):
        """ Show page """
        todos = []
        return render.index(todos, form)

    def POST(self):
        raise web.seeother('/')

class Login:

    def GET(self):
        url_params = web.input(error="none", state="none")
        if 'oauth_token' not in session and url_params.state == codes['authentication_identifier']:
            # we must be calling back from oauth
            if url_params.error != "none": 
                print("Oauth denied: "+url_params.error)
                raise web.seeother('/')

            tokens_dict = oauth2.AuthorizeTokens(codes['google_client_id'], codes['google_client_secret'],
                                                url_params.code, codes['oauth_redirect_uri'])
            session['oauth_token'] = tokens_dict['access_token']
            if 'refresh_token' in tokens_dict:
                session['refresh_token'] = tokens_dict['refresh_token']

        elif 'oauth_token' not in session:
            # this must be the first interaction with this user
            scope = 'https://mail.google.com https://www.googleapis.com/auth/userinfo.email' 
            url = oauth2.GeneratePermissionUrl(client_id=codes['google_client_id'], scope=scope, 
                                        redirect_uri=codes['oauth_redirect_uri'], state=codes['authentication_identifier'],
                                        access_type='offline')
            raise web.seeother(url)
        
        # if we make it this far, session['oauth_token'] is live
        if 'email_address' not in session: session['email_address'] = gutils.get_address(session['oauth_token'])
        model.new_tokens(session['email_address'], auth=session['oauth_token'])
        msgs = gutils.fetch_and_classify_recent_mail(session['oauth_token'], session['email_address'])
        web.seeother('https://mail.google.com')


app = web.application(urls, globals())
session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'oauth_token': None})


if __name__ == '__main__':
    app.run()