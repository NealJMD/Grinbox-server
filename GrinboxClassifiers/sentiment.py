import os, sys, nltk, re
import simplejson as json
from lib.tfidf import TfIdf
from customnaivebayes import NaiveBayesClassifier as learner
from nltk.corpus import stopwords

class SentimentClassifier():
	"""Classify text on positive or negative sentiment"""

	def file_to_list(self, filename):
		try:
			lines = [line.strip() for line in file(filename).readlines()]
		except:
			print "--- WARNING: Needs %s to be in the same directory as formality.py" % (filename)
			return []
		return lines

	def get_true_value(self):
		return self.positive_label

	def load_data(self):

		# uncomment to use Term Frequency Inverse Document Frequency normalization
		# self.tf = TfIdf()
		# for root, dirs, files, in os.walk('data/amazon'):
		# 	for name in files:
		# 		if "unlabeled" in name: continue
		# 		filename = ''.join([root,'/',name])
		# 		reviews = [line.strip() for line in file(filename).readlines()]
		# 		for rev in reviews:
		# 			self.tf.add_input_document(rev)

		f = open(os.path.join(self.curdir,'data/yelp/yelp_academic_dataset_review_abridged.json'), 'rb');
		neg_count = 0
		pos_count = 0
		for line in f.readlines():
			rev = json.loads(line)
			# if rev['stars'] == 3: continue
			sentiment = self.negative_label if rev['stars'] <= 3 else self.positive_label
			features = self.classification_format(rev['text'])
			self.dataset.append((features, sentiment))
			if rev['stars'] <= 3: neg_count += 1
			else: pos_count += 1
		print "negative: ", neg_count
		print "positive: ", pos_count
		f.close()
		

	def build_classifier(self):
		if self.dataset == []: self.load_data()
		classifier = learner.train(self.dataset)
		classifier.show_most_informative_features()
		return classifier

	def get_classifier(self):
		return self.classifier

	def test_self(self):
		correct = 0
		pos_correct = 0
		neg_correct = 0
		false_positive = 0
		false_negative = 0
		for (example, label) in self.dataset:
			if self.classifier.classify(example, self.priors) == label: 
				correct += 1
				if label == self.positive_label: pos_correct += 1
				if label == self.negative_label: neg_correct += 1
			else:
				if label == self.positive_label: false_negative += 1
				if label == self.negative_label: false_positive += 1
		print correct, " / ", len(self.dataset)
		print "positive correct: ", pos_correct
		print "negative correct: ", neg_correct
		print "false positive: ", false_positive
		print "false negative: ", false_negative

	def classify(self, raw, subject=None):
		x = self.classifier.classify(self.classification_format(raw), self.priors)
		return x

	def prob_classify(self, raw, subject=None):
		dist = self.classifier.prob_classify(self.classification_format(raw), self.priors)
		return dist.prob(dist.max())		

	def classification_format(self, msg):
		featureset = {}
		# msg = nltk.clean_html(raw)
		# tokens = [t.lower() for t in nltk.word_tokenize(msg)]
		# for token in tokens:
		# 	featureset[token] = True
		# return featureset

		raw = nltk.clean_html(msg)
		tokens = nltk.word_tokenize(raw)
		words = []
		for token in tokens:
			t = token.lower()
			if t not in self.stop_dict:
				word = self.alphanumeric_pattern.sub('', t)
				if len(word) > 1: words.append(word)
		for w in words: featureset[self.stemmer.stem(w)] = True
		return featureset

	def __init__(self):
		self.dataset = []
		self.positive_label = "positive"
		self.negative_label = "negative"
		self.alphanumeric_pattern = re.compile('[\W_0-9]+')
		self.stemmer = nltk.PorterStemmer()
		self.stop_dict = {}
		for w in stopwords.words('english'):
			self.stop_dict[w] = True
		self.priors = {}
		self.priors['negative'] = 0.001
		self.priors['positive'] = 0.999
		self.curdir = os.path.dirname(os.path.realpath(__file__))
		self.classifier = self.build_classifier()
		self.test_self()


def main():
	f = SentimentClassifier()
	classifier = f.get_classifier()
	
if __name__ == "__main__":
	main()