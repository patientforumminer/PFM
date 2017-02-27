# coding=utf-8
# Suzan Verberne and Maya Sappelli


# + 1. Read json (query+result list), and extract threads
# + 2. For each thread in result list, extract post feats
# + 3. Standardize post feats
# + 4. Apply linear model
# + 5. Apply threshold
# + 6.Return json with for each thread, for each postid the value 1 or 0 for in/out summary, and the predicted value of the linear model



import sys
import re
import string
import operator
import functools
import numpy
from scipy.linalg import norm
import json

#json_filename = sys.argv[1]
#outfilename = sys.argv[2]





class Summarizer():
	"Summarizer class, which provides a summary for a thread"
	def __init__(self): # adapted for flexible indexnames
		self.feat_weights = dict()
		self.intercept = 2.45595
		self.feat_weights["abspos"] = -0.69456
		self.feat_weights["relpos"] = -0.17991
		self.feat_weights["noresponses"] = -0.11507
		self.feat_weights["noofupvotes"] = 0 # not in viva data
		self.feat_weights["cosinesimwthread"] = 0.32817
		self.feat_weights["cosinesimwtitle"] = 0.13588
		self.feat_weights["wordcount"] = -1.44997
		self.feat_weights["uniquewordcount"] = 1.90478
		self.feat_weights["ttr"] = -0.38033
		self.feat_weights["relpunctcount"] = -0.12664
		self.feat_weights["avgwordlength"] = 0.18753
		self.feat_weights["avgsentlength"] = 0 # not significant
		self.feat_weights["relauthorcountsinthread"] =	-0.11927
		self.columns = dict() # key is feature name, value is dict with key (threadid,postid) and value the feature value
		self.postsperthread = dict() # dictionary with threadid as key and posts dictionary ((author,timestamp)->postid) as value


	def __setitem__(self, key, item): self.data[key] = item
	def __getitem__(self, key): return self.data[key]

	def tokenize(self,t):
		text = t.lower()
		text = re.sub("\n"," ",text)
		text = re.sub('[^a-zèéeêëûüùôöòóœøîïíàáâäæãåA-Z0-9- \']', "", text)
		wrds = text.split()
		return wrds

	

	def split_into_sentences(self,text):
		caps = "([A-Z])"
		prefixes = "(Dhr|Mevr|Dr|Drs|Mr|Ir|Ing)[.]"
		suffixes = "(BV|MA|MSc|BSc|BA)"
		starters = "(Dhr|Mevr|Dr|Drs|Mr|Ir|Ing)"
		acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
		websites = "[.](com|net|org|io|gov|nl)"
		
		# adapted from http://stackoverflow.com/questions/4576077/python-split-text-on-sentences
		text = " " + text + "  "
		text = text.replace("\n"," ")
		text = re.sub(prefixes,"\\1<prd>",text)
		text = re.sub(websites,"<prd>\\1",text)
		if "Ph.D" in text: text = text.replace("Ph.D.","Ph<prd>D<prd>")
		text = re.sub("\s" + caps + "[.] "," \\1<prd> ",text)
		text = re.sub(acronyms+" "+starters,"\\1<stop> \\2",text)
		text = re.sub(caps + "[.]" + caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>\\3<prd>",text)
		text = re.sub(caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>",text)
		text = re.sub(" "+suffixes+"[.] "+starters," \\1<stop> \\2",text)
		text = re.sub(" "+suffixes+"[.]"," \\1<prd>",text)
		text = re.sub(" " + caps + "[.]"," \\1<prd>",text)
		if "\"" in text: text = text.replace(".\"","\".")
		if "!" in text: text = text.replace("!\"","\"!")
		if "?" in text: text = text.replace("?\"","\"?")
		text = re.sub("([\.\?!]+\)?)","\\1<stop>",text)
		if "<stop>" not in text:
			text += "<stop>"
		text = text.replace("<prd>",".")
		text = re.sub('	 +',' ',text)
		sents = text.split("<stop>")
		sents = sents[:-1]
		sents = [s.strip() for s in sents]
		return sents

	def count_punctuation(self,t):
		punctuation = string.punctuation
		punctuation_count = len(list(filter(functools.partial(operator.contains, punctuation), t)))
		textlength = len(t)
		relpc = 0
		if textlength>0:
			relpc = float(punctuation_count)/float(textlength)
		return relpc

	def nrofsyllables(self,w):
		count = 0
		vowels = 'aeiouy'
		w = w.lower().strip(".:;?!")
		if w[0] in vowels:
			count +=1
		for index in range(1,len(w)):
			if w[index] in vowels and w[index-1] not in vowels:
				count +=1
		if w.endswith('e'):
			count -= 1
		if w.endswith('le'):
			count+=1
		if count == 0:
			count +=1
		return count


	# noinspection PyUnresolvedReferences
	def fast_cosine_sim(self,a, b):
		#print (a)
		if len(b) < len(a):
			a, b = b, a
		up = 0
		a_value_array = []
		b_value_array = []
		for key in a:
			a_value = a[key]
			b_value = b[key]
			a_value_array.append(a_value)
			b_value_array.append(b_value)
			up += a_value * b_value
		if up == 0:
			return 0
		return up / norm(a_value_array) / norm(b_value_array)




	

	def addvaluestocolumnsoverallthreads(self,dictionary,feature):
		columndict = dict()
		if feature in self.columns: # if this is not the first thread, we already have a columndict for this feature
			columndict = self.columns[feature] # key is (threadid,postid) and value the feature value
		for (threadid,postid) in dictionary:
			value = dictionary[(threadid,postid)]
			columndict[(threadid,postid)] = value
		#print feature, columndict
		self.columns[feature] = columndict

	def standardize_values(self,columndict,feature):
		values = list()
		for (threadid,postid) in columndict:
			values.append(columndict[(threadid,postid)])
		mean = numpy.mean(values)
		stdev = numpy.std(values)
		normdict = dict() # key is (threadid,postid) and value the normalized feature value
		for (threadid,postid) in columndict:
			value = columndict[(threadid,postid)]
			if stdev == 0.0:
				stdev = 0.000000000001
				#print ("stdev is 0! ", feature, value, mean, stdev)
			#if value != 0:
			normvalue = (float(value)-float(mean))/float(stdev)
			normdict[(threadid,postid)] = normvalue
	#		 if feature == "noofupvotes":
	#			print threadid,postid, feature, float(value), mean, stdev, normvalue, len(columndict)

		return normdict

	
	def findQuote (self,content,thread_id) :
		months_conversion = {'januari': '01', 'februari': '02', 'maart': '03', 'april': '04', 'mei': '05', 'juni': '06', 'juli': '07', 'augustus': '08', 'september': '09', 'oktober': '10', 'november': '11', 'december': '12', 'May': '05'}
	
		pattern = re.compile("\*\*\[(.*) schreef op (.*) @ ([0-9:]+)\]")
		# > quote: > > **[kattie2 schreef op 28 januari 2015 @ 16:32]
		match = pattern.search(content)
		referred_post = ""
		if match :
			#print (match)
			user = match.group(1)
			date = match.group(2)
			time = match.group(3)
			datepattern = re.compile("^[^ ]+ [^ ]+ [^ ]+$")
			if datepattern.match(date) :
				[day,month,year] = date.split()
				monthnumber = months_conversion[month]
				converteddate = day+"-"+monthnumber+"-"+year+" "+time
				if thread_id in self.postsperthread:
					postsforthread = self.postsperthread[thread_id]

					if (user,converteddate) in postsforthread:
						referred_post = postsforthread[(user,converteddate)]
						#sys.stderr.write("Found referred post: "+user+" "+converteddate+" :: "+postid+"\n")
					else :
						#sys.stderr.write("Quoted post is missing from thread: "+user+" "+converteddate+" ")

						user = "anoniem"
						if (user,converteddate) in postsforthread :
							referred_post = postsforthread[(user,converteddate)]
							#sys.stderr.write("but found anoniempje at that timestamp and used that")
						else :
							for (u,d) in postsforthread:
								if converteddate == d:# and re.match(".*[aA]noniem.*",u):
									#sys.stderr.write("but found "+u+" at that timestamp and used that")
									referred_post = postsforthread[(u,d)]
									break
						#sys.stderr.write ("\n")
		return referred_post

	'''
	MAIN: READ JSON AND EXTRACT FEATURES
	'''
	def get_summarized_thread(self, json_string):
		openingpost_for_thread = dict() # key is threadid, value is id of opening post
		postids_dict = dict() # key is (threadid,postid), value is postid. Needed for pasting the columns at the end
		threadids = dict() # key is (threadid,postid), value is threadid. Needed for pasting the columns at the end
		threadids_list = list() # needed for feature standardization: length of list is total no of posts
		threadids_dict = dict()
		postids_per_threadid = dict()
		upvotecounts = dict()  # key is (threadid,postid), value is # of upvotes
		responsecounts = dict()	 # key is (threadid,postid), value is # of replies
		cosinesimilaritiesthread = dict()  # key is (threadid,postid), value is cossim with term vector for complete thread
		cosinesimilaritiestitle = dict()  # key is (threadid,postid), value is cossim with term vector for title
		uniquewordcounts = dict()  # key is (threadid,postid), value is unique word count in post
		wordcounts = dict() # key is (threadid,postid), value is word count in post
		typetokenratios = dict()  # key is (threadid,postid), value is type-token ratio in post
		abspositions = dict() # key is (threadid,postid), value is absolute position in thread
		relpositions = dict()  # key is (threadid,postid), value is relative position in thread
		relauthorcountsinthreadforpost = dict()	 # key is (threadid,postid), value is relative number of posts by author in this thread
		relpunctcounts = dict() # key is (threadid,postid), value is relative punctuation count in post
		avgwordlengths = dict() # key is (threadid,postid), value is average word length (nr of characters)
		avgnrsyllablesinwords = dict() # key is (threadid,postid), value is average word length (nr of syllables)
		avgsentlengths = dict() # key is (threadid,postid), value is average word length (nr of words)
		readabilities = dict() # key is (threadid,postid), value is readability
		bodies = dict()	 # key is (threadid,postid), value is content of post
		op_source_strings = dict() # key is threadid, value is the value of the 'source' field of the opening post
		post_source_strings = dict() # key is (threadid,postid), value is the value of the 'source' field of the comment

		featnames = ("threadid","postid","abspos","relpos","noresponses","noofupvotes","cosinesimwthread","cosinesimwtitle","wordcount","uniquewordcount","ttr","relpunctcount","avgwordlength","avgsentlength","relauthorcountsinthread")



		#json_string = ""
		#with open(json_filename,'r') as json_file:
		#	for line in json_file:
		#		json_string += line.rstrip()


		parsed_json = json.loads(json_string)

		query_words = parsed_json['query_words']
		entity_matrix = parsed_json['entity_matrix']
		threads = parsed_json['threads']

		#json_out = open(outfilename, 'w')
		summarized_threads = []

		for thread in threads:
			termvectors = dict()  # key is postid, value is dict with term -> termcount for post
			termvectorforthread = dict()  # key is term, value is termcount for full thread
			termvectorfortitle = dict()	 # key is term, value is termcount for title
			authorcountsinthread = dict()  # key is authorid, value is number of posts by author in this thread
			post_per_postid = dict() # key is postid, value is complete post dictionary (needed for printing)
			#print(thread)
			threadid = thread['thread_id']
			title = ""
			if 'thread_title' in thread:
				title = thread['thread_title']
			#print(threadid,title)
			thread_content = thread['content']
			openingpost = thread_content['message']
			text_of_openingpost = openingpost['text']
			author_of_openingpost = openingpost['author']
			timestamp_of_openingpost = openingpost['time']
			postid_of_openingpost = openingpost['msg_id']
			#print (postid_of_openingpost,text_of_openingpost)
			openingpost_for_thread[threadid] = postid_of_openingpost

			# save all author-time combinations (including of openingpost) for postid lookup
			postsforthread = dict()
			if threadid in self.postsperthread:
				postsforthread = self.postsperthread[threadid]
			postsforthread[(author_of_openingpost,timestamp_of_openingpost)] = postid_of_openingpost
			self.postsperthread[threadid] = postsforthread

			# In the TNO json, the msg_id of the opening post is equal to the threadid
			category = "" # no category information in json
			#print (text_of_openingpost)
			posts = thread_content['comments']
			noofposts = len(posts)
			#print (threadid,"no of comments in this thread:",noofposts)

			for post in posts:
				# first go through the thread to find all authors,
				postid = post['msg_id']
				post_per_postid[postid] = post
				timestamp = post['time']
				author = post['author']
				if author in authorcountsinthread:
					authorcountsinthread[author] += 1
				else:
					authorcountsinthread[author] =1

				# and save all author-time combinations for postid lookup
				postsforthread = dict()
				if threadid in self.postsperthread:
					postsforthread = self.postsperthread[threadid]
				postsforthread[(author,timestamp)] = postid
				self.postsperthread[threadid] = postsforthread

			postcount = 0
			for post in posts:
				# then go through the thread again to calculate all feature values
				postcount += 1
				postid = post['msg_id']
				timestamp = post['time']
				author = post['author']

				postidsforthread = list()
				if threadid in postids_per_threadid:
					postidsforthread = postids_per_threadid[threadid]
				postidsforthread.append(postid)
				postids_per_threadid[threadid] = postidsforthread

				body = post['text']

				postids_dict[(threadid,postid)] = postid
				threadids[(threadid,postid)] = threadid
				threadids_list.append(threadid) # needed for feature standardization: length of list is total no of posts
				threadids_dict[threadid] = 1
				parentid = ""
				if 'parent' in post:
					parentid = post['parent'] # no parent field in current version of TNO json
				else:
					parentid = self.findQuote(body,threadid)
					if parentid != openingpost_for_thread[threadid]:
						# do not save responses for openingpost because openingpost will not be in feature file
						# (and disturbs the column for standardization)
						if (threadid,parentid) in responsecounts:
							responsecounts[(threadid,parentid)] += 1
						else:
							responsecounts[(threadid,parentid)] = 1

				upvotes = 0
				if 'upvotes' in post:
					upvotes = int(post['upvotes']) # no upvotes in current version of json (does not exist for viva)
				upvotecounts[(threadid,postid)] = upvotes

				relauthorcountsinthreadforpost[(threadid,postid)] = float(authorcountsinthread[author])/float(noofposts)

				if "smileys" in body:
					body = re.sub(r'\((http://forum.viva.nl/global/(www/)?smileys/.*.gif)\)','',body)

				if "http" in body:
					body = re.sub(r'http://[^ ]+','',body)

				bodies[(threadid,postid)] = body

				words = self.tokenize(body)
				wc = len(words)

				sentences = self.split_into_sentences(body)
				sentlengths = list()

				for s in sentences:
					sentwords = self.tokenize(s)
					nrofwordsinsent = len(sentwords)
					#print (s, nrofwordsinsent)
					sentlengths.append(nrofwordsinsent)
				if len(sentences) > 0:
					avgsentlength = numpy.mean(sentlengths)
					avgsentlengths[(threadid,postid)] = avgsentlength
				else:
					avgsentlengths[(threadid,postid)] = 0
				relpunctcount = self.count_punctuation(body)
				relpunctcounts[(threadid,postid)] = relpunctcount
				#print (body, punctcount)
				wordcounts[(threadid,postid)] = wc
				uniquewords = dict()
				wordlengths = list()
				nrofsyllablesinwords = list()
				for word in words:
					#print (word, nrofsyllables(word))
					nrofsyllablesinwords.append(self.nrofsyllables(word))
					wordlengths.append(len(word))
					uniquewords[word] = 1
					if word in termvectorforthread:	 # dictionary over all posts
					   termvectorforthread[word] += 1
					else:
					   termvectorforthread[word] = 1

					worddict = dict()
					if postid in termvectors:
						worddict = termvectors[postid]
					if word in worddict:
						worddict[word] += 1
					else:
						worddict[word] = 1
					termvectors[postid] = worddict

				uniquewordcount = len(uniquewords)
				uniquewordcounts[(threadid,postid)] = uniquewordcount
				readabilities[(threadid,postid)] = 0

				if wc > 0:
					avgwordlength = numpy.mean(wordlengths)
					#avgnrsyllablesinword = numpy.mean(nrofsyllablesinwords)
					avgwordlengths[(threadid,postid)] = avgwordlength
					#avgnrsyllablesinwords[(threadid,postid)] = avgnrsyllablesinword
					#readabilities[(threadid,postid)] = readability(avgnrsyllablesinword,avgsentlength)
				else:
					avgwordlengths[(threadid,postid)] = 0

				#print (threadid, postid, wc, avgsentlengths[(threadid,postid)])

				typetokenratio = 0
				if wordcounts[(threadid,postid)] > 0:
					typetokenratio = float(uniquewordcount) / float(wordcounts[(threadid,postid)])
				typetokenratios[(threadid,postid)] = typetokenratio

				relposition = float(postcount)/float(noofposts)
				#relposition = float(postid)/float(noofposts)
				relpositions[(threadid,postid)] = relposition
				abspositions[(threadid,postid)] = postcount

				#abspositions[(threadid,postid)] = postid

			# add zeroes for titleterms that are not in the thread vector
			titlewords = self.tokenize(title)
			for tw in titlewords:
				if tw in termvectorfortitle:
					termvectorfortitle[tw] += 1
				else:
					termvectorfortitle[tw] = 1

			for titleword in termvectorfortitle:
				if titleword not in termvectorforthread:
					termvectorforthread[titleword] = 0

			# add zeroes for terms that are not in the title vector:
			for word in termvectorforthread:
				if word not in termvectorfortitle:
					termvectorfortitle[word] = 0

			# add zeroes for terms that are not in the post vector:
			for postid in termvectors:
				worddictforpost = termvectors[postid]
				for word in termvectorforthread:
					if word not in worddictforpost:
						worddictforpost[word] = 0
				termvectors[postid] = worddictforpost

				cossimthread = self.fast_cosine_sim(termvectors[postid], termvectorforthread)
				cossimtitle = self.fast_cosine_sim(termvectors[postid], termvectorfortitle)
				cosinesimilaritiesthread[(threadid,postid)] = cossimthread
				cosinesimilaritiestitle[(threadid,postid)] = cossimtitle
				#print(title,postid,cossimtitle)

			for postid in postidsforthread:
				if not (threadid,postid) in responsecounts:
					responsecounts[(threadid,postid)] = 0
				if not (threadid,postid) in cosinesimilaritiesthread:
					cosinesimilaritiesthread[(threadid,postid)] = 0.0
				if not (threadid,postid) in cosinesimilaritiestitle:
					cosinesimilaritiestitle[(threadid,postid)] = 0.0
				if not (threadid,postid) in responsecounts:
					responsecounts[(threadid,postid)] = 0

			columns_for_thread = dict()
			columns_for_thread["threadid"] = threadids
			columns_for_thread["postid"] = postids_dict

			columns_for_thread["abspos"] = abspositions
			columns_for_thread["relpos"] = relpositions
			columns_for_thread["noresponses"] = responsecounts
			columns_for_thread["noofupvotes"] = upvotecounts
			columns_for_thread["cosinesimwthread"] = cosinesimilaritiesthread
			columns_for_thread["cosinesimwtitle"] = cosinesimilaritiestitle
			columns_for_thread["wordcount"] = wordcounts
			columns_for_thread["uniquewordcount"] = uniquewordcounts
			columns_for_thread["ttr"] = typetokenratios
			columns_for_thread["relpunctcount"] = relpunctcounts
			columns_for_thread["avgwordlength"] = avgwordlengths
			columns_for_thread["avgsentlength"] = avgsentlengths
			columns_for_thread["relauthorcountsinthread"] = relauthorcountsinthreadforpost

			columns_std = dict()
			for featurename in featnames:
				columndict = columns_for_thread[featurename]

				columndict_with_std_values = columndict
				if featurename != "postid" and featurename != "threadid":
					columndict_with_std_values = self.standardize_values(columndict,featurename)
				columns_std[featurename] = columndict_with_std_values
				#print (featurename,columns_std[featurename])


		#	 predicted = dict()
		#	 include = dict()

			posts_with_decision = []
			for postid in postidsforthread:
				#print (threadid,postid)
				post = post_per_postid[postid]
				predicted_outcome = self.intercept

				for featurename in featnames:
					#print (featurename)
					columndict_with_std_values = columns_std[featurename]
					value = columndict_with_std_values[(threadid,postid)]
					if featurename in self.feat_weights:
						weighted_value = self.feat_weights[featurename]*value
						predicted_outcome += weighted_value
					#predicted[(threadid,postid)] = predicted_outcome
				post['summary_predicted'] = predicted_outcome
				#print(threadid,postid,predicted_outcome)
				if predicted_outcome >= 3.72:
					# fixed threshold, based on tune set 5 from viva data
					#include[(threadid,postid)] = 1
					post['summary_include'] = 1
				else:
					#include[(threadid,postid)] = 0
					post['summary_include'] = 0
				#print(postid,post)
				posts_with_decision.append(post)

			openingpost['summary_predicted'] = 1 # always include the opening post in the summary
			openingpost['summary_include'] = 1
			thread_content['message'] = openingpost
			thread_content['comments'] = posts_with_decision
			thread['content'] = thread_content
			summarized_threads.append(thread)

		print >> sys.stderr, 'Threads summarized for query ' + str(parsed_json['query_words'])
		#print ('Threads summarized for query ' + str(parsed_json['query_words']))
		parsed_json['threads'] = summarized_threads
		return json.dumps(parsed_json)
		#json.dump(parsed_json,json_out)

		#json_out.close()

