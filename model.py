import web
import time

db = web.database(dbn='mysql', db='grinbox', user='root')

def get_tokens(address):
	values = {'address': address}
	matches = db.select('tokens', vars=values, where='address=$address')
	if len(matches) > 0: return matches[0]
	return None

def new_tokens(address, auth='', refresh=''):
	values = {'address': address, 'auth': auth, 'refresh':refresh}
	db.query("INSERT INTO tokens (address, auth, refresh) VALUES ($address, $auth, $refresh) ON DUPLICATE KEY UPDATE auth=$auth, refresh=$refresh", vars=values)
	# db.insert('tokens', address=address, auth=auth, refresh=refresh)

def get_classification_without_uid(recipient, sender, time, subject):
	values = {'recipient': recipient,
				'time': time,
				'subject': subject,
				'sender': sender }
	matches = db.select('classifications', vars=values, 
		where='recipient = $recipient AND time = $time AND subject = $subject AND sender = $sender', order='time DESC')
	if len(matches) > 0: return matches[0]
	matches = db.select('classifications', vars=values, 
		where='recipient = $recipient AND time = $time', order='time DESC')
	if len(matches) > 0: return matches[0]
	return None	

def get_classification(recipient, uid):
	values={'recipient': recipient,
			'uid': uid}
	matches = db.select('classifications', vars=values, where='recipient=$recipient AND uid=$uid')
	if len(matches) > 0: return matches[0]
	return None

def new_classification(recipient, sender, time, subject, formality, sentiment, commercialism, uid):
	values = {  'recipient': recipient,
				'sender': sender,
				'time': time,
				'subject': subject,
				'formality': formality,
				'sentiment': sentiment,
				'commercialism': commercialism,
				'uid': uid }
	db.query("INSERT IGNORE INTO classifications (recipient, sender, time, subject, formality, sentiment, commercialism, uid) VALUES ($recipient, $sender, $time, $subject, $formality, $sentiment, $commercialism, $uid)", vars=values)