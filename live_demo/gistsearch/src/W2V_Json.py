from nltk import word_tokenize
from stop_words import get_stop_words
#from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from gensim import corpora, models
import gensim
import os
import bs4 as bs
import time
from sklearn.cluster import KMeans
import logging
import json


# create Dutch stop words list
du_stop = get_stop_words('dutch')


# Create p_stemmer of class PorterStemmer
p_stemmer = PorterStemmer()
    
# read forum posts
doc_set = []

path = 'dutch_data'
for filename in os.listdir(path):
    if not filename.endswith('.json'): continue
    fullname = os.path.join(path, filename)
    with open(fullname,'r') as fh:
		print filename
		posts = json.loads(fh.read())
		for post in posts:
			if 'text' in post: # viva data
				doc_set.append(post['text'])   
			if 'post_text' in post: # gist forum
				doc_set.append(post['post_text']) 
		
		
		
print ' read ' , len(doc_set) , ' posts'
# list for tokenized documents in loop
texts = []

# loop through document list
for i in doc_set:
    # clean and tokenize document string
    raw = i.lower()
    tokens = word_tokenize(raw)

    # remove stop words from tokens
    stopped_tokens = [i for i in tokens if not i in du_stop]
	    
    # stem tokens
    #stemmed_tokens = [p_stemmer.stem(i) for i in stopped_tokens]
	    
    # add tokens to list
    #texts.append(stemmed_tokens)
    texts.append(stopped_tokens)

# turn our tokenized documents into a id <-> term dictionary
#dictionary = corpora.Dictionary(texts)
    
# convert tokenized documents into a document-term matrix
#corpus = [dictionary.doc2bow(text) for text in texts]

print "-- Creating W2V Model -- " , (time.strftime("%H:%M:%S"))
# generate Word2Vec model
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
w2vecmodel = gensim.models.Word2Vec(texts, workers=4, size=200, min_count=25, window=8, sample = 1e-3)
w2vecmodel.init_sims(replace=True)
model_name = "200features_25minwords_8context"
w2vecmodel.save(model_name)
w2vecmodel.save_word2vec_format(model_name+'binary.bin', binary=True)

'''
word_vectors = w2vecmodel.syn0
num_clusters = word_vectors.shape[0] / 5
kmeans_clustering = KMeans( n_clusters = num_clusters )
idx = kmeans_clustering.fit_predict( word_vectors )
word_centroid_map = dict(zip( w2vecmodel.index2word, idx ))

# alternative W2V implementation
#https://www.kaggle.com/c/word2vec-nlp-tutorial/details/part-2-word-vectors

# For the first 10 clusters
for cluster in xrange(0,10):
    #
    # Print the cluster number  
    print "\nCluster %d" % cluster
    #
    # Find all of the words for that cluster number, and print them out
    words = []
    for i in xrange(0,len(word_centroid_map.values())):
        if( word_centroid_map.values()[i] == cluster ):
            words.append(word_centroid_map.keys()[i])
    print words
'''