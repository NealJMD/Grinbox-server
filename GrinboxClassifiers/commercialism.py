class CommercialismClassifier():
	"""Classify email messages as commercial or personal"""
	
	def get_true_value(self):
		return self.commercial_label

	def classify(self, raw_with_case, metadata={}):
		raw = raw_with_case.lower()
		if 'from' in metadata:
			if 'sales' in metadata['from'].lower() or 'reply' in metadata['from'].lower():
				return self.commercial_label
		if 'content_type' in metadata:
			if metadata['content_type'] == 'text/plain': return self.personal_label
		if '<style' in raw: return self.commercial_label
		if 'view it in a browser' in raw: return self.commercial_label
		if 'view it in your browser' in raw: return self.commercial_label
		if 'view this email' in raw: return self.commercial_label
		if 'viewing this email' in raw: return self.commercial_label
		if raw.count('<img') >= 2: return self.commercial_label
		return self.personal_label

	def __init__(self):
		self.commercial_label = 'commercial'
		self.personal_label = 'personal'
		
		