import time
import re
import imaplib
import model
import oauth2
import urllib2
import random
import email
import grinbox_classifier
import simplejson as json
import email.utils as eu

address_pattern = re.compile('[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}')
classifier = grinbox_classifier.GrinboxClassifier(relearn=False)
SQL_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_email_address(target):
    address = address_pattern.search(target)
    if address: return address.group(0)
    else: return ''

def email_to_sql_date(timestring):
    """input: Sat, 27 Apr 2013 19:57:10 -0400
    output: 2013-04-27 19:57:10
    output: YYYY-MM-DD HH:MM:SS"""
    seconds = eu.mktime_tz(eu.parsedate_tz(timestring))
    ret = time.strftime(SQL_TIME_FORMAT, time.gmtime(seconds))
    return ret

def get_auth_token(address):
    group = model.get_tokens(address)
    return group.auth if group is not None else ''

def earlier_time(time_str1, time_str2):
    time1 = eu.mktime_tz(eu.parsedate_tz(time_str1))
    time2 = eu.mktime_tz(eu.parsedate_tz(time_str2))
    # units are seconds since epoch
    if time1 > time2: return time_str1
    else: return time_str2

def fetch_and_classify_recent_mail(token, address, start_index=0, end_index=4):
    msgs = fetch_recent_mail(token, address, start_index, end_index)
    processed_msgs = []
    for email_data in msgs:
        # if type(email_data) == type((1,2)): continue # hackaround. need to figure out this type error.
        classification = model.get_classification(address, email_data['uid'])
        if classification is None:
            formality = classifier.classify('formality', email_data['content'], email_data['subject'], as_boolean=True)
            sentiment = classifier.classify('sentiment', email_data['content'], None, as_boolean=True)
            commercialism = classifier.classify('commercialism', email_data['content'], email_data, as_boolean=True)
            msgs.append((email_data['from'], email_to_sql_date(email_data['time']), email_data['subject']))
            model.new_classification(
                recipient=address,
                sender=email_data['from'],
                time=email_to_sql_date(email_data['time']),
                subject=email_data['subject'],
                formality=formality,
                sentiment=sentiment,
                commercialism=commercialism,
                uid=email_data['uid'] )
            email_data['formality'] = formality
            email_data['sentiment'] = sentiment
            email_data['commercialism'] = commercialism
        else:
            email_data['formality'] = classification.formality
            email_data['sentiment'] = classification.sentiment
            email_data['commercialism'] = classification.commercialism
        email_data.pop('content', None)
        processed_msgs.append(email_data)
    return processed_msgs

def fetch_recent_mail(token, address, start_index=0, end_index=49):
    print token
    print address
    imap = get_inbox_connection(token, address)
    result, data = imap.uid('search', None, "ALL")
    num_messages = len(data[0].split())
    msgs = []
    for i in reversed(range(num_messages-end_index, num_messages-start_index)):
        latest_email_uid = data[0].split()[i]
        result, raw_data = imap.uid('fetch', latest_email_uid, '(RFC822)')
        raw_email = raw_data[0][1]
        msg = email.message_from_string(raw_email)
        email_data = {
                    'recipient': address,
                    'from': get_email_address(msg.get('From')),
                    'subject': msg.get('Subject'),
                    'time': msg.get('Date'),
                    'content_type': msg.get_content_type(),
                    'uid': latest_email_uid}
        while msg.is_multipart(): 
            done = False
            for part in msg.get_payload():
                if 'html' in part.get_content_type(): 
                    msg = part
                    done = True
            if not done: msg = msg.get_payload()[-1]

        email_data['content'] = msg.get_payload()
        if type(email_data) == type((1,2)):
            print type(email_data)
            print email_data
        msgs.append(email_data)
    return msgs

def get_inbox_connection(token, address):
    nonce = str(random.randrange(2**64 - 1))
    timestamp = str(int(time.time()))

    auth_string = oauth2.GenerateOAuth2String(address, token, False)
    
    imap_conn = imaplib.IMAP4_SSL('imap.gmail.com')
    imap_conn.debug = 4
    imap_conn.authenticate('XOAUTH2', lambda x: auth_string)
    imap_conn.select('inbox', readonly=True)
    return imap_conn

def get_address(token):
    get_address_endpoint = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='+token
    address_endpoint_response = urllib2.urlopen(get_address_endpoint)
    address_info = json.loads(address_endpoint_response.read())
    if 'email' not in address_info: 
        print('unable to fetch user address')
        return ''
    return address_info['email']

