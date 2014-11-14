import os, sys, re, nltk, enchant, random
import simplejson as json
import xml.etree.ElementTree as ET
from nltk.corpus import nps_chat
from nltk.classify.naivebayes import NaiveBayesClassifier as learner

english = enchant.Dict("en_US")
SUBJECT_CHARS = 50

class FormalityClassifier:
	"""Classify text based on the formality of the formatting and content"""
	
	def build_informal_set(self):
		minlines = 6
		maxlines = 25
		labeled_sets = []
		xml_posts = nps_chat.xml_posts()
		lines = 0
		goal = random.randint(minlines, maxlines)
		builder = ""
		for msg in xml_posts:
			if ".ACTION" not in msg.text:
				builder = builder+" "+msg.text.strip()
				lines += 1
			if lines > goal:
				labeled_sets.append((self.extract_features(builder), self.informal_label))
				goal = random.randint(minlines, maxlines)
				builder = ""
				lines = 0
		return labeled_sets

	def build_formal_set(self):
		newspath = os.path.join(self.curdir, "data/news")
		labeled_sets = []
		for filename in os.listdir(newspath):
			x = newspath+"/"+filename
			print x
			xmldoc = ET.parse(x)
			for r in xmldoc.findall('REUTERS'):
				for t in r.findall('TEXT'):
					for msg in t.findall('BODY'):
						labeled_sets.append((self.extract_features(msg.text), self.formal_label))			
		return labeled_sets

	def test_self(self):
		correct = 0
		pos_correct = 0
		neg_correct = 0
		false_formal = 0
		false_informal = 0
		for (example, label) in self.labeled_features:
			if self.classifier.classify(example) == label: 
				correct += 1
				if label == self.formal_label: pos_correct += 1
				if label == self.informal_label: neg_correct += 1
			else:
				if label == self.formal_label: false_informal += 1
				if label == self.informal_label: false_formal += 1
		print correct, " / ", len(self.labeled_features)
		print "formal correct: ", pos_correct
		print "informal correct: ", neg_correct
		print "false formal: ", false_formal
		print "false informal: ", false_informal

	# def build_labeled_set(self, filename, label):
	# 	f = open(filename)
	# 	msgs = msg_delimiter_pattern.split(f.read())
	# 	labeled_sets = []
	# 	for msg in msgs: labeled_sets.append((self.extract_features(msg), label))

	# 	return labeled_sets

	def build_classifier(self):
		self.labeled_features = self.build_informal_set()
		self.labeled_features.extend(self.build_formal_set())
		classifier = learner.train(self.labeled_features)
		classifier.show_most_informative_features()
		return classifier

	def get_classifier(self):
		return self.classifier

	def get_true_value(self):
		return self.formal_label

	def file_to_list(self, filename):
		try:
			lines = [line.strip() for line in file(filename).readlines()]
		except:
			print "--- WARNING: Needs %s to be in the same directory as formality.py" % (filename)
			return []
		return lines

	def classification_format(self, raw, subject=None):
		msg = nltk.clean_html(raw)
		fs = self.extract_features(msg, subject)
		return fs
		
	def classify(self, raw, subject=None):
		return self.classifier.classify(self.classification_format(raw, subject))

	def prob_classify(self, raw, subject=None):
		dist = self.classifier.prob_classify(self.classification_format(raw, subject))
		return dist.prob(dist.max())

	def extract_features(self, msg, subj=None):
		# features: 
		# 	portion of words capitalized properly
		# 	occurence of swear words, emoticons, and 
		# 	number of misspelled words (real but not spelled correctly)
		words = nltk.word_tokenize(msg)
		if subj is None:
			if len(msg) < SUBJECT_CHARS: subj = msg
			else: subj = msg[:50]
		subject = nltk.word_tokenize(subj)
		messy_words = msg.rsplit()
		counts = {}
		weights = {}
		features = {}
		counts["capitalized"] = 0
		counts["emoticons"] = 0
		counts["abbreviations"] = 0
		counts["slurs"] = 0
		counts["swears"] = 0
		counts["misspelled"] = 0
		counts["subject_capitalized"] = 0
		wordcount = len(words)
		if wordcount is 0: wordcount = 1
		for word in words:
			if word == word.capitalize(): counts["capitalized"] += 1.0
			else: # don't check capitalized words for spelling as they're likely to be proper nouns 
				if not english.check(word): counts["misspelled"] += 1.0
			word = word.lower()
			if word in self.swears: counts["swears"] += 1.0
			if word in self.abbreviations: counts["abbreviations"] += 1.0
			lastchar = ''
			streak = 1
			for char in word:
				if streak > 2: 
					counts["slurs"] += 1.0
					break
				if lastchar == char: streak += 1
				else: lastchar = char
		for word in messy_words:
			if word in self.emoticons: counts["emoticons"] += 1.0
		for word in subject:
			if word.lower() == 're' or word.lower() == 'fwd': continue
			if word == word.capitalize() and word.isalpha():
				counts["subject_capitalized"] += 1.0

		features["swears"] = (counts["swears"] > 0)
		features["emoticons"] = (counts["emoticons"] > 0)
		features["abbreviations"] = (counts["abbreviations"] > 0)
		features["slurs"] = (counts["slurs"] > 0)
		features["misspelled"] = (counts["misspelled"] > 1)
		features["subject_capitalized"] = (counts["subject_capitalized"] > 1)
		features["capitalized"] = (counts["capitalized"]/wordcount > 0.07)
		return features

	def __init__(self):		
		self.curdir = os.path.dirname(os.path.realpath(__file__))
		self.formal_label = "formal"
		self.informal_label = "informal"
		self.swears = self.file_to_list(os.path.join(self.curdir, "data/informal/swears"))
		self.emoticons = self.file_to_list(os.path.join(self.curdir, "data/informal/emoticons"))
		self.abbreviations = self.file_to_list(os.path.join(self.curdir, "data/informal/abbreviations"))
		self.classifier = self.build_classifier()
		self.test_self()

def main():
	f = FormalityClassifier()
	classifier = f.get_classifier()
	
if __name__ == "__main__":
	main()