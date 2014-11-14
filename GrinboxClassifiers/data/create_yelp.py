import os, sys, nltk, random
import simplejson as json


def create_dataset(pmax, nmax):
	curdir = os.path.dirname(os.path.realpath(__file__))
	big = open(os.path.join(curdir,'yelp/yelp_academic_dataset_review.json'), 'rb');
	little = open(os.path.join(curdir,'yelp/yelp_academic_dataset_review_abridged.json'), 'wb');
	
	pcount = 0
	ncount = 0
	for line in big.readlines():
		rev = json.loads(line)
		if rev['stars'] <= 3 and ncount < nmax:
			ncount += 1
			little.write(line)
		elif rev['stars'] > 3 and pcount < pmax:
			pcount += 1
			little.write(line)
		elif pcount >= pmax and ncount >= nmax: break
	print "negative: ", ncount
	print "positive: ", pcount
	big.close()
	little.close()

if __name__ == '__main__':
	create_dataset(6000, 14000)