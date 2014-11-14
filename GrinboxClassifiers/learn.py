import sys, re, pprint, nltk, formality, sentiment
import simplejson as json
import pickle
from numpy import *
from pybrain.tools.shortcuts import buildNetwork
from nltk.corpus import stopwords
from pybrain.datasets import UnsupervisedDataSet
from pybrain.unsupervised.trainers import *
from pybrain.auxiliary import kmeans
from collections import defaultdict
from gensim import corpora, models, similarities

K = 10
PER_FILE = 500
TIME_BINS = 8
MORNING_STARTS = 6
NUM_TOPICS = 8
PREFIX = "data/email/emails"
USER_ADDRESS = "NealJMD@gmail.com"
GENERIC_DOMAINS = ["gmail.com", "yahoo.com", "comcast.net", "hotmail.com", "aol.com", "verizon.net"]
EMAIL_STOPWORDS = ["from", "to", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "mon", "tue", "wed", "thu", "fri", "sat", "sun", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "email", "http", "recipient", "contenttype", "unsubscribe"]
TIME_BIN_SIZE = 24 / TIME_BINS

address_pattern = re.compile('[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.([A-Za-z]{2,4}))')
alphanumeric_pattern = re.compile('[\W_0-9]+')

# [<total count>, <html count>, <tld>, <domain>]
TOTAL_IDX = 0
HTML_IDX = 1
TLD_IDX = 2
TIME_IDX = 3
LSI_IDX = 4
DOMAIN_IDX = 5

FEATURE_COUNT = 6

max_messages = 1
working_dict = defaultdict()
lsi_dict = corpora.Dictionary()
texts = []
# lsi_model = models.lsimodel.LsiModel()
bags = []
authors = []
domains = {}

def generate_tld_rater():
	tld_rater = {}
	tld_rater["gov"] = 1
	tld_rater["edu"] = .8
	tld_rater["org"] = .7
	tld_rater["com"] = .5
	tld_rater["default"] = tld_rater["com"]
	tld_rater["xxx"] = 0
	return tld_rater

def get_weighter():
	weight = {}
	weight[TLD_IDX] = 1
	weight[TOTAL_IDX] = 3
	weight[TIME_IDX] = 3
	weight[DOMAIN_IDX] = 2 # remember this one is binary so don't make it too big
	weight[HTML_IDX] = 7
	weight[LSI_IDX] = 4 # this one has a shitload of dimensions and is the only one that goes [-1, 1] instead of [0, 1]
	return weight

def preprocess_content(content_string):
	raw = nltk.clean_html(content_string)
	tokens = nltk.word_tokenize(raw)
	words = []
	for token in tokens:
		t = token.lower()
		if t not in stopwords.words('english') and t not in EMAIL_STOPWORDS:
			word = alphanumeric_pattern.sub('', t)
			if len(word) > 1: words.append(word)
	stemmer = nltk.PorterStemmer()
	stems = [stemmer.stem(w) for w in words]
	# for stem in stems: print stem,
	return stems

def parse_time(dirty_string):
	reg_find = re.search('([0-9][0-9])\:[0-9][0-9]\:[0-9][0-9]', dirty_string)
	if reg_find is None: 
		print dirty_string
		return 0
	hour = int(reg_find.group(1))
	return hour - (hour % (TIME_BIN_SIZE))

def parse_address(dirty_string):
	address = address_pattern.search(dirty_string)
	# address = address_pattern.search(dirty_string)
	if(address is not None): return [address.group(0), address.group(1), address.group(2)]
	else: return "FAILURE"

def mode(times):
	champ_val = 0
	champ_time = 0
	tied = 0
	for hour, count in enumerate(times):
		if count > champ_val: 
			champ_val = count
			champ_time = hour
			tied = 0
		elif count is champ_val:
			tied += 1

	# randomly choose between tied bins
	if tied is 0: return champ_time
	picked = random.randint(0, tied)
	current = 0
	for hour, count in enumerate(times):
		if count is champ_val:
			if current is picked: return hour
			else: current += 1

def main():
	file_number = 34000
	read_error_count = 0
	print("building sentiment classifier")
	sentiment_classifier = sentiment.SentimentClassifier()
	print("building formality classifier")
	formality_classifier = formality.FormalityClassifier()

	formality_file = open('formality.pickle', 'wb')
	pickle.dump(formality_classifier, formality_file)
	formality_file.close()

	sentiment_file = open('sentiment.pickle', 'wb')
	pickle.dump(sentiment_classifier, sentiment_file)
	sentiment_file.close()
	print("pickled!")
	
	formal_pos_subjects = {}
	informal_pos_subjects = {}
	formal_neg_subjects = {}
	informal_neg_subjects = {}

	print("importing and parsing email")
	while True:
		file_number += PER_FILE
		print "Importing and classifying messages %s to %s" % (file_number, file_number+PER_FILE-1)
		filename = PREFIX+USER_ADDRESS+str(file_number)
		try:
			f = open(filename, 'rb')
		except IOError as e:
			print "Finished reading and processing " + str(file_number - PER_FILE - read_error_count) +" messages"
			if read_error_count > 0: print "Failed to read "+ str(read_error_count) + "messages"
			break
		try:
			emails = json.load(f)
		except:
			print "failed to read ", filename
			read_error_count += PER_FILE
			continue
		for email in emails:
			process_email(email)
			formal = formality_classifier.classify(email["Content"], email["Subject"])
			feeling = sentiment_classifier.classify(email["Content"])
			if feeling == "neg": print formal, feeling, email["Subject"]
			if formal == "informal": 
				if feeling == "pos":
					if email["Subject"] not in informal_pos_subjects:
						informal_pos_subjects[email["Subject"]] = email["From"]#, formality_classifier.prob_classify(email["Content"]))
				if feeling == "neg":
					if email["Subject"] not in informal_neg_subjects:
						informal_neg_subjects[email["Subject"]] = email["From"]#, formality_classifier.prob_classify(email["Content"]))
			elif formal == "formal":
				if feeling == "pos":
					if email["Subject"] not in formal_pos_subjects:
						formal_pos_subjects[email["Subject"]] = email["From"]#, formality_classifier.prob_classify(email["Content"]))
				if feeling == "neg":
					if email["Subject"] not in formal_neg_subjects:
						formal_neg_subjects[email["Subject"]] = email["From"]#, formality_classifier.prob_classify(email["Content"]))	# print formal+": "+email["Content"][:35]+"}}"
	
	print "informal_pos_subjects ", len(informal_pos_subjects)
	print "informal_neg_subjects ", len(informal_neg_subjects)
	print "formal_pos_subjects ", len(formal_pos_subjects)
	print "formal_neg_subjects ", len(formal_neg_subjects)

	informal_pos_output = open(USER_ADDRESS+"_informal_pos", "wb")
	for subject, address in informal_pos_subjects.iteritems():
		# try: 
		informal_pos_output.write(subject + " ::: " + address+"\n")
		# except: pass
	informal_pos_output.close()
	formal_pos_output = open(USER_ADDRESS+"_formal_pos", "wb")
	for subject, address in formal_pos_subjects.iteritems():
		# try: 
		formal_pos_output.write(subject + " ::: " + address+"\n")
		# except: pass
	formal_pos_output.close()
	formal_neg_output = open(USER_ADDRESS+"_formal_neg", "wb")
	for subject, address in formal_neg_subjects.iteritems():
		# try: 
		formal_neg_output.write(subject + " ::: " + address+"\n")
		# except: pass
	formal_neg_output.close()
	informal_neg_output = open(USER_ADDRESS+"_informal_neg", "wb")
	for subject, address in informal_neg_subjects.iteritems():
		# try: 
		informal_neg_output.write(subject + " ::: " + address+"\n")
		# except: pass
	informal_neg_output.close()
	# lsi_topics()

def process_email(email):
	global max_messages
	global working_dict
	global lsi_dict
	global texts
	address = parse_address(email["From"])
	full_address = address[0]
	domain = address[1]
	tld = address[2]
 	html_count = 1 if ("<html>" in email["Content"] or "<HTML>" in email["Content"]) else 0
 	sent_time = parse_time(email["Received"])

 	stem_list = preprocess_content(email["Content"])
 	
 	# if(len(stem_list) > 0): 	
	lsi_dict.add_documents([stem_list])
	texts.append(stem_list)
	authors.append(full_address)

 	if full_address in working_dict:
 		current = working_dict[full_address]
 		current[HTML_IDX] += html_count
 		current[TOTAL_IDX] += 1
 		current[TIME_IDX][sent_time] += 1	
 		
 		if(current[TOTAL_IDX] > max_messages): max_messages = current[TOTAL_IDX]
 		working_dict[full_address] = current
 	else:
 		a = {}
 		a[TOTAL_IDX] = 1
 		a[HTML_IDX] = html_count
 		a[DOMAIN_IDX] = domain
 		a[TLD_IDX] = tld
 		a[TIME_IDX] = [0]*24
 		a[TIME_IDX][sent_time] = 1
 		
 		working_dict[full_address] = a
 		if domain not in GENERIC_DOMAINS:
			if domain in domains:
				domains[domain] += 1
			else:
				domains[domain] = 1


def lsi_topics():
		# LSI stuff
	print("performing semantic indexing")
	corpus = [lsi_dict.doc2bow(text) for text in texts]
	tfidf = models.TfidfModel(corpus)
	corpus_tfidf = tfidf[corpus]
	lsi = models.LsiModel(corpus_tfidf, id2word=lsi_dict, num_topics=NUM_TOPICS)
	corpus_lsi = lsi[corpus_tfidf]
	doc_id = 0
	for doc in lsi[corpus_tfidf]:
		owner = authors[doc_id]
		try:
			existing = working_dict[owner][LSI_IDX]
		except:
			existing = []
		existing.append(doc)
		working_dict[owner][LSI_IDX] = existing
		doc_id += 1
	print("finished creating "+str(NUM_TOPICS)+" topics")

	topics = lsi.show_topics()
	topic_output = open(USER_ADDRESS+"_topics", "wb")
	for topic in topics: 
		topic_output.write(topic+"\n")
	topic_output.close()

if __name__ == "__main__":
    main()

	# informal_tuples = []
	# formal_tuples = []
	# for subject, (address, posterior) in informal_subjects.iteritems():
	# 	informal_tuples.append((subject, posterior, address))
	# for subject, (address, posterior) in formal_subjects.iteritems():
	# 	formal_tuples.append((subject, posterior, address))
	# informal_tuples.sort(key= lambda tuple: tuple[2])
	# formal_tuples.sort(key= lambda tuple: tuple[2])
	# informal_output = open(USER_ADDRESS+"_informal_emails", "wb")
	# for (subject, posterior, address) in informal_tuples:
	# 	try: informal_output.write(subject + " ::: " + str(posterior)+" ::: "+ address)
	# 	except: 
	# 		print "Failed decoding"
	# 		pass
	# informal_output.close()
	# formal_output = open(USER_ADDRESS+"_formal_emails", "wb")
	# for (subject, posterior, address) in formal_tuples:
	# 	try: formal_output.write(subject + " ::: " + str(posterior)+" ::: "+ address)
	# 	except: 
	# 		print "Failed decoding"
	# 		pass
