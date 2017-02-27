#!/usr/bin/env python
# encoding: utf-8

#=~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~=
#
# gistsearch.py - search the GIST facebook group
#
# Author: Martijn Spitters, TNO
#
# Semanticsearch inherits from the Elasticsearch class and extends it with word2vec-based
# query expansion and search functionality, and a specific wrapper around the search result
#
#=~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~=


import sys
import argparse
import os
import gensim
import logging
import cPickle
import gzip
import json
import pprint
import itertools
import numpy as np
from gensim import utils, matutils
from sklearn import neighbors
from elasticsearch import Elasticsearch


 
class Semanticsearch(Elasticsearch):
	"Semantic searcher class, which extends the Elasticsearch class with word2vec-based expansion functionality"
	'''def __init__(self, indexname): # adapted for flexible indexnames
		Elasticsearch.__init__(self, host='elasticsearch')
		self.indices.refresh(index=indexname)
		self.host		   = 'elasticsearch'
		self.data		   = {}
		self.indexname	   = indexname
		self.entities	   = True
		self.n_expand	   = 5
		self.n_results	   = 100
		self.w2vmodel	   = "../data/"+indexname+"/"+indexname+"_word2vec_model.bin"
		#self.w2vmodel		= "../data/"+indexname+"/dutch_word2vec_model.bin"
		#self.w2vmodel		= "../data/dutch_wikipedia_word2vec_model.txt"
		#self.vectordb		= "../data/"+indexname+"/"+indexname+"_posts.txt"
		self.load_w2vmodel(self.w2vmodel)
		#self.load_vectordb(self.vectordb)
	'''
	def __init__(self): # adapted for flexible indexnames
		Elasticsearch.__init__(self, host='elasticsearch')
		#self.indices.refresh()
		self.host		   = 'elasticsearch'
		self.data		   = {}
		self.entities	   = True
		self.n_expand	   = 5
		self.n_results	   = 100
		#self.w2vmodelnl	   = "../data/dutch_word2vec_model.bin"
		self.w2vmodelnl	   = None
		self.w2vmodelen	   = "../data/gist_word2vec_model.bin"
		self.load_w2vmodel(self.w2vmodelnl,self.w2vmodelen)
	

	def __setitem__(self, key, item): self.data[key] = item
	def __getitem__(self, key): return self.data[key]
	
	
	def expanded_search(self,q,i):
		"Expands the input query using word2vec, then performs a regular search with the expanded query"
		exp_q = []
		if self.query_has_known_word(q,i) is True:
			exp_q = self.expand_query(q,i)
		else:
			exp_q = q
		
		return self.regular_search(exp_q,i)
		
	def expanded_search_fullthreads(self,q, i):
		"Expands the input query using word2vec, then performs a regular search with the expanded query"
		exp_q = []
		if self.query_has_known_word(q,i) is True:
			exp_q = self.expand_query(q,i)
		else:
			exp_q = q
		
		return self.regular_search_fullthreads(exp_q, i)
		
	
	def regular_search(self,q,i):
		"Performs a regular search with Elasticsearch, and adds some FB-specific stuff"	   
		result = { 'query_words':[], 'hits':[], 'entity_matrix':[] }

		hits = self.search(index=i,size=self.n_results,body={'query':{'match':{'text':" ".join(q)}}})

		# restructure the search result according to Facebook's message/comment structure
		result['hits'] = self.create_message_blocks(hits, False, i)

		# create an entity co-occurrence matrix for graph visualization
		if self.entities == True:
			result['entity_matrix'] = self.create_entity_matrix(result['hits'])

		# and add the expanded query
		result['query_words'] = q			

		return json.dumps(result,indent=4)
	
	
	def setResultHit(self,thread, mid, score):
		for message in thread:
			#print(mid + " " + message['message']['_source']['msg_id'])
			if message['message']['msg_id'] == mid:
					message['searchhit'] = score
			for comment in message['comments']:
				if comment[u'msg_id'] == mid:
					comment[u'searchhit'] = score
		return thread
		
	def regular_search_fullthreads(self,q, i):
		"Performs a regular search with Elasticsearch, and returns the entire thread"	 
		result = { 'query_words':[], 'entity_matrix':[], 'index': i }

		hits = self.search(index=i,size=self.n_results,body={'query':{'match':{'text.sentence':" ".join(q)}}})

		# restructure the search result according to Facebook's message/comment structure
		threadids = []
		threads = {}
	
		result['threads'] = []
		titles = {}
		for h in hits['hits']['hits']:
			tid = h['_source']['thread_id']
			mid = h['_source']['msg_id']
			score = h['_score']
			if 'thread_title' in h['_source']:
				titles[tid] = h['_source']['thread_title']
			else:
				titles[tid] = "no title"
			#tid = "10"
			if not tid in threads:
				thread = self.search(index=i,size=self.n_results,body={'query':{'constant_score':{'filter':{'term':{'thread_id':tid}}}}})
				#print thread
				threads[tid] = self.create_message_blocks(thread, True, i)
			threads[tid] = self.setResultHit(threads[tid], mid, score)
			
		for tid in threads:
			result['threads'].append({'thread_id':tid,'thread_title':titles[tid],'content':threads[tid][0]})

		# create an entity co-occurrence matrix for graph visualization
		rhits= self.create_message_blocks(hits, False,i)
		if self.entities == True:
			result['entity_matrix'] = self.create_entity_matrix(rhits)

		# and add the expanded query
		result['query_words'] = q			

		return json.dumps(result,indent=4)
	
	
	def expand_query(self,query, index):
		"Expands the query by searching for related words in the word2vec model"
		exp_q_json = self.semantic_word_search(query,index,self.n_expand)
		exp_q = query + [ i['word'] for i in json.loads(exp_q_json) ]
		return exp_q
	
	
	def query_has_known_word(self,q, index):
		"Checks if the query contains at least one word which is known in the word2vec model"
		if 'gist_en' in index:
			m = self.men
		else:
			m = self.mnl
		#m = self.m
		for word in q:
			if word in m.vocab:
				return True			   
		return False
	

	def create_message_blocks(self,result,full,index):
		"Restructures the Elasticsearch result according to Facebook's message-comment structure"
		msg_blocks = []
		block_ids = {}
		for h in result['hits']['hits']:
			if full:
				h['_source']['searchhit'] = 0
			if h['_source']['type'] == 'message':
				tid = h['_source']['thread_id']
				if not tid in block_ids:
					m = h['_source']
					if 'thread_title' in m:
						del m['thread_title']
					del m['thread_id']
					msg_blocks.append({"block_id":tid,"message":m,"comments":[]})
					block_ids[tid] = len(msg_blocks)-1
		
			elif h['_source']['type'] == 'comment':
				tid = h['_source']['thread_id']
				mid = h['_source']['msg_id']
				m = h['_source']
				if 'thread_title' in m:
					del m['thread_title']
				del m['thread_id']
				#fid = tid+mid
				if tid in block_ids:
					msg_blocks[block_ids[tid]]['comments'].append(m)
				else:
					#ts = self.get(index="gist",id=tid)
					try:
						ts = self.get(index=index,id=tid) # gaat fout bij gist forum (thread not found)
						m2 = ts['_source']
						if 'thread_title' in m2:
							del m2['thread_title']
						
						del m2['thread_id']
						msg_blocks.append({"block_id":tid,"message":m2,"comments":[m]})
						
						block_ids[tid] = len(msg_blocks)-1
					except:
						print "topic start not found trying with +1"
						try:
							ts = self.get(index=index,id=tid+"1") # gaat fout bij gist forum (thread not found)
							m2 = ts['_source']
							if 'thread_title' in m2:
								del m2['thread_title']
							
							del m2['thread_id']
							msg_blocks.append({"block_id":tid,"message":m2,"comments":[m]})
							
							block_ids[tid] = len(msg_blocks)-1
						except:
							print "topic start still not found, using current message as topic start"
							msg_blocks.append({"block_id":tid,"message":m,"comments":[]})
		return msg_blocks

	def create_entity_matrix(self,msg_blocks):
		"Creates a co-occurrence matrix of the entities found in the forum posts"
		mtrx = {}
		cats = {}
		for b in msg_blocks:
			ents = []			 
			if 'entities' in b['message']:		   
				m_ent = b['message']['entities']
				for e in m_ent:
					if not 'Mentaal Process' in e['category']:
						ents.append(e['entity'])
						if e['entity'] not in cats:
							cats[e['entity']] = e['category']
			if 'comments' in b:
				for c in b['comments']:
					if 'entities' in c:
						for e in c['entities']:
							if not 'Mentaal Process' in e['category']:
								ents.append(e['entity'])
								if e['entity'] not in cats:
									cats[e['entity']] = e['category']
							
			entset = sorted(set(ents))
			for (e1,e2) in itertools.combinations(entset, 2):
				if e1 not in mtrx: mtrx[e1] = {}
				if e2 not in mtrx[e1]:
					mtrx[e1][e2] = 1
				else:
					mtrx[e1][e2] += 1
	
		entity_matrix = []
	
		for a in mtrx:
			for b in mtrx[a]:
				if mtrx[a][b] > 2:
					entity_matrix.append({'a':{'entity':a,'category':cats[a]},'b':{'entity':b,'category':cats[b]},'weight':mtrx[a][b]})
	
		return entity_matrix 

	''' (old with _source)
	def create_entity_matrix(self,msg_blocks):
		"Creates a co-occurrence matrix of the entities found in the forum posts"
		mtrx = {}
		cats = {}
		for b in msg_blocks:
			ents = []			 
			if '_source' in b['message'] and 'entities' in b['message']['_source']:		   
				m_ent = b['message']['_source']['entities']
				for e in m_ent:
					ents.append(e['entity'])
					if e['entity'] not in cats:
						cats[e['entity']] = e['category']				 
			if 'comments' in b:
				for c in b['comments']:
					if 'entities' in c['_source']:
						for e in c['_source']['entities']:
							ents.append(e['entity'])
							if e['entity'] not in cats:
								cats[e['entity']] = e['category']
							
			entset = sorted(set(ents))
			for (e1,e2) in itertools.combinations(entset, 2):
				if e1 not in mtrx: mtrx[e1] = {}
				if e2 not in mtrx[e1]:
					mtrx[e1][e2] = 1
				else:
					mtrx[e1][e2] += 1
	
		entity_matrix = []
	
		for a in mtrx:
			for b in mtrx[a]:
				if mtrx[a][b] > 2:
					entity_matrix.append({'a':{'entity':a,'category':cats[a]},'b':{'entity':b,'category':cats[b]},'weight':mtrx[a][b]})
	
		return entity_matrix 
	'''

	def load_w2vmodel(self,f1,f2):
		"Load an existing binary word2vec model from file f"
		try:
			if f1 != None:
				print >> sys.stderr, 'Loading word2vec model from file ' + f1
				if ".txt" in f1:
					self.mnl = gensim.models.Word2Vec.load(f1)
				else:
					self.mnl = gensim.models.Word2Vec.load_word2vec_format(f1,binary=True)
			print >> sys.stderr, 'Loading word2vec model from file ' + f2
			if ".txt" in f2:
				self.men = gensim.models.Word2Vec.load(f2)
			else:
				self.men = gensim.models.Word2Vec.load_word2vec_format(f2,binary=True)
		except:
			print >> sys.stderr, 'Could not load word2vec model from file ' + f1 + ' or ' + f2
			raise
		


	def load_vectordb(self,db):
		"Load an existing vector and annotation database from file"
		try:
			print >> sys.stderr, 'Loading vector database from ' + db
			vdb = np.load(db + ".vect.npy")
			docsfile = gzip.open(db + '.docs', 'r')
			anno = cPickle.load(docsfile)
			docsfile.close()
			self.v = { 'vect': vdb, 'anno': anno }
		except:
			print >> sys.stderr, 'Could not load vector database from ' + db
			raise
	
	
	def get_vector(self,q):
		"Returns the average vector for the input word(s)"
		m = self.mnl
		mn = []
		for word in q.split():
			if word in m.vocab:
				mn.append(m[word])
			
		if len(mn):
			return matutils.unitvec(np.array(mn).mean(axis=0)).astype(np.float32)
		else:
			return None


	def semantic_word_search(self,q,index, k=10):
		"Returns the k most similar words in the model for the input query as json"
		if 'gist_en' in index:
			m = self.men
		else:
			m = self.mnl
		known = []
		a = []
		
		for word in q:
			if word in m.vocab:
				known.append(word)
			else:
				print >> sys.stderr, word + " is out of vocabulary and therefore ignored"
		
		if len(known) > 0:
			res = m.most_similar(positive=known,topn=k)
			for rank,r in enumerate(res):
				d = { "rank":rank, "word":r[0], "score":r[1] }
				a.append(d)
				
		return json.dumps(a)
		

	def kNN_search(self,q):
		"""
		Creates a kNN model in memory for vectors and matches each query in q
		Performs a direct kNN search on the documents without using elasticsearch
		Returns json
		"""
		model = self.mnl
		vectors = self.v
		vect = np.asarray(vectors['vect'], np.float32)
		n = len(vect)
		y = range(n)
		a = []
	
		print >> sys.stderr, 'Fitting kNN model on training data'
		clf = neighbors.KNeighborsClassifier(n_neighbors=self.n_results, weights='distance')
		clf.fit(vect, y)

		print >> sys.stderr, 'Done loading, predicting'

		for (q_i,q_v) in enumerate(q):
			print "QV: " + q_v
			query = np.asarray([self.get_vector(q_v)], np.float32) 
			p = clf.kneighbors(query)
			print '-------------------------------------'
			print 'Query ' + str(q_i), q_v
	
			for qr_i, qr_a in enumerate(p[1]):
				for id_i, id in enumerate(qr_a):
					dist = p[0][qr_i][id_i]
					text = vectors['anno'][id]
					d = { "rank": id_i+1, "score": 1-dist, "post":text, "id":id}
					a.append(d)
		return json.dumps(a)





if __name__ == "__main__":

	# parse the commandline arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('-q', '--query', required=True, help="The input query: one or more words, separated by spaces")
	parser.add_argument('-e', '--expand', type=bool, default=False, help="Expand the query using the word2vec model")
	parser.add_argument('-r', '--retrieve', default='text', choices=['text','word'], help="Retrieve words or documents")
	parser.add_argument('-n', type=int, default=10, help="The number of hits to return")	
	args = parser.parse_args()

	s = Semanticsearch()
	s.n_results = args.n
	q = args.query.split(" ")

	if args.retrieve == 'text':
		if args.expand == True:
			print s.expanded_search(q)
		else:
			print s.regular_search(q)
	elif args.retrieve == 'word':
		print s.semantic_word_search(q)


