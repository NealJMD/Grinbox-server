import os
import pickle
import GrinboxClassifiers.formality as formality
import GrinboxClassifiers.sentiment as sentiment
import GrinboxClassifiers.commercialism as commercialism

class GrinboxClassifier():
	"""Handle all classifications for Grinbox in one centralized class"""
	
	def get_true_value(self, name):
		return self.true_value[name]

	def create_classifier(self, name, relearn=False):
		"""Create the classifier named 'name' first by attempting to load it from
		the pickled file, and failing that by relearning it and saving the pickle."""
		loaded = False
		if not relearn:
			try:
				f = open(self.pickled_classifiers[name], 'rb')
				classifier = pickle.load(f)
				f.close()
				loaded = True
			except:
				pass
		if not loaded:
			if name == "sentiment":			classifier = sentiment.SentimentClassifier()
			elif name == "formality": 		classifier = formality.FormalityClassifier()
			elif name == "commercialism":	classifier = commercialism.CommercialismClassifier()
			else:							classifier = None
			f = open(self.pickled_classifiers[name], 'wb')
			pickle.dump(classifier, f)
			f.close()
		return classifier

	def classify(self, classifier_name, raw, auxiliary=None, as_boolean=False):
		classification = self.classifiers[classifier_name].classify(raw, auxiliary)
		if not as_boolean: return classification
		return (classification == self.true_value[classifier_name])

	def __init__(self, relearn=False):
		self.pickled_classifiers = {'sentiment': 'pickled/sentiment.pickle',
									'formality': 'pickled/formality.pickle',
									'commercialism': 'pickled/commercialism.pickle'}
		self.curdir = os.path.dirname(os.path.realpath(__file__))
		self.classifier_names = ['sentiment', 'formality', 'commercialism']
		for key, val in self.pickled_classifiers.iteritems():
			self.pickled_classifiers[key] = os.path.join(self.curdir, val)
		self.classifiers = {}
		self.true_value = {}
		for classifier_name in self.classifier_names:
			self.classifiers[classifier_name] = self.create_classifier(classifier_name, relearn)
			self.true_value[classifier_name] = self.classifiers[classifier_name].get_true_value()
			


