# Natural Language Toolkit: Naive Bayes Classifiers
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A classifier based on the Naive Bayes algorithm.  In order to find the
probability for a label, this algorithm first uses the Bayes rule to
express P(label|features) in terms of P(label) and P(features|label):

|                       P(label) * P(features|label)
|  P(label|features) = ------------------------------
|                              P(features)

The algorithm then makes the 'naive' assumption that all features are
independent, given the label:

|                       P(label) * P(f1|label) * ... * P(fn|label)
|  P(label|features) = --------------------------------------------
|                                         P(features)

Rather than computing P(featues) explicitly, the algorithm just
calculates the denominator for each label, and normalizes them so they
sum to one:

|                       P(label) * P(f1|label) * ... * P(fn|label)
|  P(label|features) = --------------------------------------------
|                        SUM[l]( P(l) * P(f1|l) * ... * P(fn|l) )
"""

import math

from collections import defaultdict

from nltk.probability import FreqDist, DictionaryProbDist, ELEProbDist, sum_logs

from nltk.classify.api import ClassifierI

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class NaiveBayesClassifier(ClassifierI):
    """
    A Naive Bayes classifier.  Naive Bayes classifiers are
    paramaterized by two probability distributions:

      - P(label) gives the probability that an input will receive each
        label, given no information about the input's features.

      - P(fname=fval|label) gives the probability that a given feature
        (fname) will receive a given value (fval), given that the
        label (label).

    If the classifier encounters an input with a feature that has
    never been seen with any label, then rather than assigning a
    probability of 0 to all labels, it will ignore that feature.

    The feature value 'None' is reserved for unseen feature values;
    you generally should not use 'None' as a feature value for one of
    your own features.
    """
    def __init__(self, label_probdist, feature_probdist):
        """
        :param label_probdist: P(label), the probability distribution
            over labels.  It is expressed as a ``ProbDistI`` whose
            samples are labels.  I.e., P(label) =
            ``label_probdist.prob(label)``.

        :param feature_probdist: P(fname=fval|label), the probability
            distribution for feature values, given labels.  It is
            expressed as a dictionary whose keys are ``(label, fname)``
            pairs and whose values are ``ProbDistI`` objects over feature
            values.  I.e., P(fname=fval|label) =
            ``feature_probdist[label,fname].prob(fval)``.  If a given
            ``(label,fname)`` is not a key in ``feature_probdist``, then
            it is assumed that the corresponding P(fname=fval|label)
            is 0 for all values of ``fval``.
        """
        self._label_probdist = label_probdist
        self._feature_probdist = feature_probdist
        self._labels = label_probdist.samples()

    def labels(self):
        return self._labels

    def classify(self, featureset, priors=None):
        return self.prob_classify(featureset, priors).max()

    def prob_classify(self, featureset, priors=None):
        # Discard any feature names that we've never seen before.
        # Otherwise, we'll just assign a probability of 0 to
        # everything.
        featureset = featureset.copy()
        for fname in featureset.keys():
            for label in self._labels:
                if (label, fname) in self._feature_probdist:
                    break
            else:
                #print 'Ignoring unseen feature %s' % fname
                del featureset[fname]

        # Find the log probabilty of each label, given the features.
        # Start with the log probability of the label itself.
        logprob = {}
        if priors == None:
            print "no prior",
            for label in self._labels:
                logprob[label] = self._label_probdist.logprob(label)
        else:
            for label, prob in priors.iteritems():
                logprob[label] = math.log(prob, 2)

        # Then add in the log probability of features given labels.
        for label in self._labels:
            for (fname, fval) in featureset.items():
                if (label, fname) in self._feature_probdist:
                    feature_probs = self._feature_probdist[label,fname]
                    logprob[label] += feature_probs.logprob(fval)
                else:
                    # nb: This case will never come up if the
                    # classifier was created by
                    # NaiveBayesClassifier.train().
                    logprob[label] += sum_logs([]) # = -INF.

        return DictionaryProbDist(logprob, normalize=True, log=True)

    def show_most_informative_features(self, n=10):
        # Determine the most relevant features, and display them.
        cpdist = self._feature_probdist
        print 'Most Informative Features'

        for (fname, fval) in self.most_informative_features(n):
            def labelprob(l):
                return cpdist[l,fname].prob(fval)
            labels = sorted([l for l in self._labels
                             if fval in cpdist[l,fname].samples()],
                            key=labelprob)
            if len(labels) == 1: continue
            l0 = labels[0]
            l1 = labels[-1]
            if cpdist[l0,fname].prob(fval) == 0:
                ratio = 'INF'
            else:
                ratio = '%8.1f' % (cpdist[l1,fname].prob(fval) /
                                  cpdist[l0,fname].prob(fval))
            print ('%24s = %-14r %6s : %-6s = %s : 1.0' %
                   (fname, fval, str(l1)[:6], str(l0)[:6], ratio))

    def most_informative_features(self, n=100):
        """
        Return a list of the 'most informative' features used by this
        classifier.  For the purpose of this function, the
        informativeness of a feature ``(fname,fval)`` is equal to the
        highest value of P(fname=fval|label), for any label, divided by
        the lowest value of P(fname=fval|label), for any label:

        |  max[ P(fname=fval|label1) / P(fname=fval|label2) ]
        """
        # The set of (fname, fval) pairs used by this classifier.
        features = set()
        # The max & min probability associated w/ each (fname, fval)
        # pair.  Maps (fname,fval) -> float.
        maxprob = defaultdict(lambda: 0.0)
        minprob = defaultdict(lambda: 1.0)

        for (label, fname), probdist in self._feature_probdist.items():
            for fval in probdist.samples():
                feature = (fname, fval)
                features.add( feature )
                p = probdist.prob(fval)
                maxprob[feature] = max(p, maxprob[feature])
                minprob[feature] = min(p, minprob[feature])
                if minprob[feature] == 0:
                    features.discard(feature)

        # Convert features to a list, & sort it by how informative
        # features are.
        features = sorted(features,
            key=lambda feature: minprob[feature]/maxprob[feature])
        return features[:n]

    @staticmethod
    def train(labeled_featuresets, estimator=ELEProbDist):
        """
        :param labeled_featuresets: A list of classified featuresets,
            i.e., a list of tuples ``(featureset, label)``.
        """
        label_freqdist = FreqDist()
        feature_freqdist = defaultdict(FreqDist)
        feature_values = defaultdict(set)
        fnames = set()

        # Count up how many times each feature value occurred, given
        # the label and featurename.
        for featureset, label in labeled_featuresets:
            label_freqdist.inc(label)
            for fname, fval in featureset.items():
                # Increment freq(fval|label, fname)
                feature_freqdist[label, fname].inc(fval)
                # Record that fname can take the value fval.
                feature_values[fname].add(fval)
                # Keep a list of all feature names.
                fnames.add(fname)

        # If a feature didn't have a value given for an instance, then
        # we assume that it gets the implicit value 'None.'  This loop
        # counts up the number of 'missing' feature values for each
        # (label,fname) pair, and increments the count of the fval
        # 'None' by that amount.
        for label in label_freqdist:
            num_samples = label_freqdist[label]
            for fname in fnames:
                count = feature_freqdist[label, fname].N()
                feature_freqdist[label, fname].inc(None, num_samples-count)
                feature_values[fname].add(None)

        # Create the P(label) distribution
        label_probdist = estimator(label_freqdist)

        # Create the P(fval|label, fname) distribution
        feature_probdist = {}
        for ((label, fname), freqdist) in feature_freqdist.items():
            probdist = estimator(freqdist, bins=len(feature_values[fname]))
            feature_probdist[label,fname] = probdist

        return NaiveBayesClassifier(label_probdist, feature_probdist)

##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////

def demo():
    from nltk.classify.util import names_demo
    classifier = names_demo(NaiveBayesClassifier.train)
    classifier.show_most_informative_features()

if __name__ == '__main__':
    demo()

