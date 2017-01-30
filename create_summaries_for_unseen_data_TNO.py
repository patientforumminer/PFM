# coding=utf-8
# python3 create_summary_for_unseen_data_TNO.py json_example_query_results.new.json json_example_query_results.summary.json Dutch_model.json
# python3 create_summary_for_unseen_data_TNO.py json_example_query_results.new.json json_example_query_results.summary.json English_model.json

#0. Read the config file with models and thresholds (json, 3rd argument)
#1. Read json output of semantic search engine (query+result list), and extract threads
#2. For each thread in result list, extract post feats and sentence feats
#3. Standardize features
#4. Apply linear models
#5. By default, include half of the sentences (predicted value > median for sentences) and half of the posts (predicted value > median for posts)
#6. Write to json file with for each thread, for each postid and for each sentence the value 1 or 0 for in/out summary, and the predicted value of the linear model.


import sys
import re
import string
import functools
import operator
import numpy
import json
from scipy import sparse
import scipy
from scipy.linalg import norm
from sklearn.metrics.pairwise import cosine_similarity
import time

json_filename = sys.argv[1]
outfilename = sys.argv[2]
modelfilename = sys.argv[3]

feat_weights = dict()

json_config_string = ""
with open(modelfilename,'r') as json_file:
    for line in json_file:
        json_config_string += line.rstrip()
parsed_json_config = json.loads(json_config_string)

#print (parsed_json_config)

levels = []
feat_weights_per_level = dict() # key is 'post' or 'sentence', value is dict with feature weights for that level
feat_names_per_level = dict() # key is 'post' or 'sentence', value is list with feature names for that level
#threshold_per_level = dict()

for model_definition in parsed_json_config:
    print (model_definition)
    language = model_definition['language']
    #threshold = model_definition['threshold']

    level = model_definition['level']
    levels.append(level)
    #threshold_per_level[level] = threshold

    linear_model = model_definition['model']

    print ("\nMODEL:",model_definition['comment'])
    #featnames = ["threadid","postid"]
    featnames = []
    feat_weights = dict()

    for var in linear_model:
        if var != "Intercept":
            featnames.append(var)
        beta = linear_model[var]['beta']
        p = linear_model[var]['p']
        print (var,beta,p)
        if float(p) > 0.05:
            beta=0
        feat_weights[var] = float(beta)

    #intercept = feat_weights['Intercept']

    print ("features",featnames)
    feat_names_per_level[level] = featnames
    feat_weights_per_level[level] = feat_weights




def tokenize(t):
    text = t.lower()
    text = re.sub("\n"," ",text)
    text = re.sub('[^a-zèéeêëûüùôöòóœøîïíàáâäæãåA-Z0-9- \']', "", text)
    wrds = text.split()
    return wrds

caps = "([A-Z])"
prefixes = "(Dhr|Mevr|Dr|Drs|Mr|Ir|Ing)[.]"
suffixes = "(BV|MA|MSc|BSc|BA)"
starters = "(Dhr|Mevr|Dr|Drs|Mr|Ir|Ing)"
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|nl)"

def split_into_sentences(text):
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
    text = re.sub('  +',' ',text)
    sents = text.split("<stop>")
    sents = sents[:-1]
    sents = [s.strip() for s in sents]
    return sents

def count_punctuation(t):
    punctuation = string.punctuation
    punctuation_count = len(list(filter(functools.partial(operator.contains, punctuation), t)))
    textlength = len(t)
    relpc = 0
    if textlength>0:
        relpc = float(punctuation_count)/float(textlength)
    return relpc

def nrofsyllables(w):
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


def fast_cosine_sim(a, b):
    if len(b) < len(a):
        a, b = b, a

    up = 0
    i=0
    for a_value in a:
        b_value = b[i]
        up += a_value * b_value
        i +=1
    if up == 0:
        return 0
    return up / norm(a) / norm(b)


def alternative_cosine_sim(a,b):
    v1 = scipy.sparse.csr_matrix(a)
    v2 = scipy.sparse.csr_matrix(b)
    similarities_sparse = cosine_similarity(v1,v2,dense_output=False)
    return similarities_sparse


def standardize_values(columndict,feature):
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
            print ("stdev is 0! ", feature, value, mean, stdev)
        #if value != 0:
        normvalue = (float(value)-float(mean))/float(stdev)
        normdict[(threadid,postid)] = normvalue
#        if feature == "noofupvotes":
#           print threadid,postid, feature, float(value), mean, stdev, normvalue, len(columndict)

    return normdict

months_conversion = {'januari': '01', 'februari': '02', 'maart': '03', 'april': '04', 'mei': '05', 'juni': '06', 'juli': '07', 'augustus': '08', 'september': '09', 'oktober': '10', 'november': '11', 'no7vember': '11', 'december': '12', 'May': '05'}
postsperthread = dict() # dictionary with threadid as key and posts dictionary ((author,timestamp)->postid) as value

def findQuote (content,thread_id) :
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
            if thread_id in postsperthread:
                postsforthread = postsperthread[thread_id]

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
#MAIN: READ JSON AND EXTRACT FEATURES
'''

openingpost_for_thread = dict() # key is threadid, value is id of opening post
postids_dict = dict() # key is (threadid,postid), value is postid. Needed for pasting the columns at the end
threadids = dict() # key is (threadid,postid), value is threadid. Needed for pasting the columns at the end
threadids_list = list() # needed for feature standardization: length of list is total no of posts
threadids_dict = dict()
postids_per_threadid = dict()
upvotecounts = dict()  # key is (threadid,postid), value is # of upvotes
responsecounts = dict()  # key is (threadid,postid), value is # of replies
cosinesimilaritiesthread = dict()  # key is (threadid,postid), value is cossim with term vector for complete thread
cosinesimilaritiestitle = dict()  # key is (threadid,postid), value is cossim with term vector for title
uniquewordcounts = dict()  # key is (threadid,postid), value is unique word count in post
wordcounts = dict() # key is (threadid,postid), value is word count in post
typetokenratios = dict()  # key is (threadid,postid), value is type-token ratio in post
abspositions = dict() # key is (threadid,postid), value is absolute position in thread
relpositions = dict()  # key is (threadid,postid), value is relative position in thread
relauthorcountsinthreadforpost = dict()  # key is (threadid,postid), value is relative number of posts by author in this thread
relpunctcounts = dict() # key is (threadid,postid), value is relative punctuation count in post
avgwordlengths = dict() # key is (threadid,postid), value is average word length (nr of characters)
avgnrsyllablesinwords = dict() # key is (threadid,postid), value is average word length (nr of syllables)
avgsentlengths = dict() # key is (threadid,postid), value is average word length (nr of words)
readabilities = dict() # key is (threadid,postid), value is readability
bodies = dict()  # key is (threadid,postid), value is content of post
op_source_strings = dict() # key is threadid, value is the value of the 'source' field of the opening post
post_source_strings = dict() # key is (threadid,postid), value is the value of the 'source' field of the comment
abspositions_sent = dict() # key is (threadid, sentid), value is absolute position of sentence in post
relpositions_sent = dict() # key is (threadid, sentid), value is relative  position of sentence in post
cosinesimilaritiesthread_sent = dict() # key is (threadid,sentid), value is cossim with term vector for complete thread
cosinesimilaritiestitle_sent = dict() # key is (threadid,sentid), value is cossim with term vector for title
sentids_per_post = dict() #key is (threadid,postid), value is array of sentence ids
sentence_texts = dict() #key is (threadid,sid), value is sentence text
#print time.clock(), "\t", "go through files"

json_string = ""
with open(json_filename,'r') as json_file:
    for line in json_file:
        json_string += line.rstrip()


parsed_json = json.loads(json_string)

query_words = parsed_json['query_words']
entity_matrix = parsed_json['entity_matrix']
threads = parsed_json['threads']
print ("number of threads:",len(threads))

json_out = open(outfilename, 'w')
summarized_threads = []

threads_small = threads[0:5]

for thread in threads:
#for thread in threads:

    dictionary = dict() # key is word. used as dimensions in term vectors

    termcounts_per_post = dict()  # key is postid, value is dictionary with term -> count
    #termvectorforthread = dict()  # key is term, value is termcount for full thread
    #termvectorfortitle = dict()  # key is term, value is termcount for title
    authorcountsinthread = dict()  # key is authorid, value is number of posts by author in this thread
    post_per_postid = dict() # key is postid, value is complete post dictionary (needed for printing)

    #print(thread)
    threadid = thread['thread_id']

    print ("\n",time.clock(), "\t", threadid)
    print (">>Feature extraction")

    title = ""
    if 'thread_title' in thread:
        title = thread['thread_title']
        titlewords = tokenize(title)
        titledict = dict()
        for tw in titlewords:
            if tw in dictionary: # dictionary over all content
                dictionary[tw] += 1
            else:
                dictionary[tw] = 1
            if tw in titledict:
                titledict[tw] += 1
            else:
                titledict[tw] = 1
    print(threadid,title)
    thread_content = thread['content']
    if not 'message' in thread_content:
        continue
    openingpost = thread_content['message']
    text_of_openingpost = openingpost['text']
    author_of_openingpost = openingpost['author']
    timestamp_of_openingpost = openingpost['time']
    postid_of_openingpost = openingpost['msg_id']
    #print (postid_of_openingpost,text_of_openingpost)
    openingpost_for_thread[threadid] = postid_of_openingpost

    # save all author-time combinations (including of openingpost) for postid lookup
    postsforthread = dict()
    if threadid in postsperthread:
        postsforthread = postsperthread[threadid]
    postsperthread[threadid] = postsforthread

    # In the TNO json, the msg_id of the opening post is equal to the threadid
    category = "" # no category information in json
    #print (text_of_openingpost)
    posts = thread_content['comments']
    noofposts = len(posts)
    print (threadid,"no of comments in this thread:",noofposts)

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
        if threadid in postsperthread:
            postsforthread = postsperthread[threadid]
        postsforthread[(author,timestamp)] = postid
        postsperthread[threadid] = postsforthread

    postcount = 0
    print (time.clock(), "\t", "extract feats from each post")
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
            parentid = findQuote(body,threadid)
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

        postwords = tokenize(body)
        wc = len(postwords)

        sentences = split_into_sentences(body)
        sentlengths = list()

        sentids_for_this_post = []
        sid = 0
        for s in sentences:

            # calculate separate sentence feature values
            sentid = postid+'_s'+str(sid)
            sentids_for_this_post.append(sentid)
            sentence_texts[(threadid,sentid)] = s
            threadids[(threadid,sentid)] = threadid
            postids_dict[(threadid,sentid)] = sentid
            sentwords = tokenize(s)
            nrofwordsinsent = len(sentwords)
            abspos_sent = sid+1
            abspositions_sent[(threadid,sentid)] = abspos_sent
            relpos_sent = abspos_sent/len(sentences)
            relpositions_sent[(threadid,sentid)] = relpos_sent

            sentwords = tokenize(s)
            worddict_sent = dict()
            worddict_post = dict()
            if sentid in termcounts_per_post:
                worddict_sent = termcounts_per_post[sentid]
            if postid in termcounts_per_post:
                worddict_post = termcounts_per_post[postid]
            uniquewords = dict()
            wordlengths = list()
            for word in sentwords:
                uniquewords[word] = 1
                wordlengths.append(len(word))

                if word in worddict_sent:
                    worddict_sent[word] += 1
                else:
                    worddict_sent[word] = 1
                if word in worddict_post:
                    worddict_post[word] += 1
                else:
                    worddict_post[word] = 1

                if word in dictionary: # dictionary over all content
                    dictionary[word] += 1
                else:
                    dictionary[word] = 1
            termcounts_per_post[sentid] = worddict_sent
            termcounts_per_post[postid] = worddict_post
            #print (sentid,termcounts_per_post[sentid])
            #print (postid,termcounts_per_post[postid])


            wordcounts[(threadid,sentid)] = len(sentwords)
            uniquewordcounts[(threadid,sentid)] = len(uniquewords)
            typetokenratio = 0
            if wordcounts[(threadid,sentid)] > 0:
                typetokenratio = float(len(uniquewords)) / float(wordcounts[(threadid,sentid)])
                avgwordlengths[(threadid,postid)] = numpy.mean(wordlengths)
            typetokenratios[(threadid,sentid)] = typetokenratio
            relpunctcounts[(threadid,sentid)] = count_punctuation(s)

            #print s, nrofwordsinsent
            sentlengths.append(nrofwordsinsent)
            sid +=1
        #print (threadid,postid,sentids_for_this_post)
        sentids_per_post[(threadid,postid)] = sentids_for_this_post
        if len(sentences) > 0:
            avgsentlength = numpy.mean(sentlengths)
            avgsentlengths[(threadid,postid)] = avgsentlength
        else:
            avgsentlengths[(threadid,postid)] = 0
        relpunctcount = count_punctuation(body)
        relpunctcounts[(threadid,postid)] = relpunctcount
        #print (body, punctcount)
        wordcounts[(threadid,postid)] = wc
        uniquewords = dict()
        wordlengths = list()
        nrofsyllablesinwords = list()
        worddict = dict()
        for word in postwords:
            #print (word, nrofsyllables(word))
            nrofsyllablesinwords.append(nrofsyllables(word))
            wordlengths.append(len(word))
            uniquewords[word] = 1

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
    print (time.clock(), "\t", "create term vectors")

    dictionary_vector = [] # vector with words.
    termvectorforthread = []
    termvectorfortitle = []
    for term in dictionary:
        if dictionary[term] > 0:
            dictionary_vector.append(term)
            termvectorforthread.append(dictionary[term])
            if term in titledict:
                termvectorfortitle.append(titledict[term])
            else:
                termvectorfortitle.append(0)

    #termvectorforthread = sparse.csr_matrix(termvectorforthread)
    #termvectorfortitle = sparse.csr_matrix(termvectorfortitle)
    #print ("thread:",termvectorforthread, len(termvectorforthread))
    #print ("title",termvectorfortitle, len(termvectorfortitle))

    # add zeroes for terms that are not in the post vector:
    termvectors = dict() # key is postid, value is term vector
    for postid in termcounts_per_post:
        #print (postid)
        worddictforpost = termcounts_per_post[postid]
        termvectorforpost = []
        for term in dictionary_vector:
            if term in worddictforpost:
                termvectorforpost.append(worddictforpost[term])
            else:
                termvectorforpost.append(0)

        #termvectors[postid] = sparse.csr_matrix(termvectorforpost)
        termvectors[postid] = termvectorforpost

        #print (time.clock(), "\t", "calculate cossim for",postid,"dimensionality is",len(termvectors[postid]))

    print (time.clock(), "\t", "calculate cosine similarities")
    for postid in termvectors:
        if "_s" in postid:
            # calculate cossim for sentence itself
            cossimthread_sent = fast_cosine_sim(termvectors[postid], termvectorforthread)
            #cossimthread_sent = alternative_cosine_sim(termvectors[postid], termvectorforthread)
            cossimtitle_sent = fast_cosine_sim(termvectors[postid], termvectorfortitle)
            #cossimtitle_sent = alternative_cosine_sim(termvectors[postid], termvectorfortitle)

            cosinesimilaritiesthread_sent[(threadid,postid)] = cossimthread_sent
            cosinesimilaritiestitle_sent[(threadid,postid)] = cossimtitle_sent
            #print (postid,termvectors[postid],cossimthread_sent)
            #postid_for_sentid = re.sub("_s[0-9]+","",postid)
            #print (postid,postid_for_sentid)
            # and add the cossim of the post it is embedded in as separate feature
            #cossimthread = fast_cosine_sim(termvectors[postid_for_sentid], termvectorforthread)
            #cossimtitle = fast_cosine_sim(termvectors[postid_for_sentid], termvectorfortitle)
            #cosinesimilaritiesthread[(threadid,postid)] = cossimthread
            #cosinesimilaritiestitle[(threadid,postid)] = cossimtitle
        else:
            # if postid is not a sentence then only calculate the cossim for the postid
            cossimthread = fast_cosine_sim(termvectors[postid], termvectorforthread)
            cossimtitle = fast_cosine_sim(termvectors[postid], termvectorfortitle)
            cosinesimilaritiesthread[(threadid,postid)] = cossimthread
            cosinesimilaritiestitle[(threadid,postid)] = cossimtitle

    for postid in postidsforthread:
        if not (threadid,postid) in cosinesimilaritiesthread:
            cosinesimilaritiesthread[(threadid,postid)] = 0.0
        if not (threadid,postid) in cosinesimilaritiestitle:
            cosinesimilaritiestitle[(threadid,postid)] = 0.0
        sentids_for_this_post = sentids_per_post[(threadid,postid)]
        #print(threadid,postid,sentids_for_this_post)
        for sentid in sentids_for_this_post:
            if not (threadid,sentid) in cosinesimilaritiesthread_sent:
                cosinesimilaritiesthread_sent[(threadid,postid)] = 0.0
            if not (threadid,sentid) in cosinesimilaritiestitle_sent:
                cosinesimilaritiestitle_sent[(threadid,postid)] = 0.0
        if not (threadid,postid) in responsecounts:
            # don't store the counts for the openingpost
            #print ("postid not in responsecounts", postid, "opening post:", openingpost_for_thread[threadid])
            responsecounts[(threadid,postid)] = 0.0
        #else:
            #print ("postid in responsecounts",threadid,postid,responsecounts[(threadid,postid)])

    print (time.clock(), "\t", "standardize feat values")
    columns_for_thread = dict()
    columns_for_thread.clear()
    columns_for_thread["threadid"] = threadids
    columns_for_thread["postid"] = postids_dict
    columns_for_thread["abspos_post"] = abspositions
    columns_for_thread["relpos_post"] = relpositions
    columns_for_thread["abspos"] = abspositions  # these two are equal to the two above but the post model has different feature names
    columns_for_thread["relpos"] = relpositions
    columns_for_thread["abspos_sent"] = abspositions_sent
    columns_for_thread["relpos_sent"] = relpositions_sent
    columns_for_thread["noresponses"] = responsecounts
    columns_for_thread["noofupvotes"] = upvotecounts
    columns_for_thread["cosinesimwthread_post"] = cosinesimilaritiesthread # these two are equal to the two above but the post model has different feature names
    columns_for_thread["cosinesimwtitle_post"] = cosinesimilaritiestitle
    columns_for_thread["cosinesimwthread"] = cosinesimilaritiesthread
    columns_for_thread["cosinesimwtitle"] = cosinesimilaritiestitle
    columns_for_thread["cosinesimwthread_sent"] = cosinesimilaritiesthread_sent
    columns_for_thread["cosinesimwtitle_sent"] = cosinesimilaritiestitle_sent
    columns_for_thread["wordcount"] = wordcounts
    columns_for_thread["uniquewordcount"] = uniquewordcounts
    columns_for_thread["ttr"] = typetokenratios
    columns_for_thread["relpunctcount"] = relpunctcounts
    columns_for_thread["avgwordlength"] = avgwordlengths
    columns_for_thread["avgsentlength"] = avgsentlengths
    columns_for_thread["relauthorcountsinthread"] = relauthorcountsinthreadforpost

    columns_std = dict()
    for sum_level in levels:
        featnames = feat_names_per_level[sum_level]
        for featurename in featnames:
            if featurename in columns_for_thread:
                columndict = columns_for_thread[featurename]

                columndict_with_std_values = columndict
                if featurename != "postid" and featurename != "threadid":
                    columndict_with_std_values = standardize_values(columndict,featurename)
                columns_std[featurename] = columndict_with_std_values
            else:
                print ("Feature from model has not been stored as column in the data:",featurename)
            #print (featurename,columns_std[featurename])


    print (">>Summarization")
    print (time.clock(), "\t", "summarize")
    predicted_values_posts = list() # put all predicted values in a list so that we can later take the median
    predicted_values_sents = list() # put all predicted values in a list so that we can later take the median

    for postid in postidsforthread:
        '''
        # first, summarize on the sentence level
        '''

        level = 'sentence'
        featnames = feat_names_per_level[level]
        feat_weights = feat_weights_per_level[level]
        intercept = feat_weights['Intercept']
        #print (level, feat_weights)

        sentence_information = list()
        sentids_for_this_post = sentids_per_post[(threadid,postid)]
        #print (threadid,postid,sentids_for_this_post)

        for sentid in sentids_for_this_post:
            #print (threadid,postid,sentid)

            predicted_outcome = intercept
            sentence_information_for_this_sentence = dict()
            for featurename in featnames:
                if featurename in columns_std:

                    columndict_with_std_values = columns_std[featurename]
                    #print(featurename, columndict_with_std_values)
                    value = 0
                    if (threadid,sentid) in columndict_with_std_values:
                        value = columndict_with_std_values[(threadid,sentid)]
                    else:
                        postid_for_sentid = re.sub("_s[0-9]+","",sentid)
                        if (threadid,postid_for_sentid) in columndict_with_std_values:
                            value = columndict_with_std_values[(threadid,postid_for_sentid)]
                        else:
                            print ("sentence id",sentid,"and postid",postid, "are not in the columndict for feature",featurename)

                    if featurename in feat_weights:
                        weighted_value = feat_weights[featurename]*value
                        predicted_outcome += weighted_value
                        if ":\)" in sentence_texts[(threadid,sentid)]:
                            print (sentence_texts[(threadid,sentid)],featurename,feat_weights[featurename],value,weighted_value)
                    else:
                        print("featurename not in lrm model:",featurename)
                    #predicted[(threadid,postid)] = predicted_outcome

                else:
                    print(("Feature from model has not been stored as column in the standardized data:",featurename))

            predicted_values_sents.append(predicted_outcome)

            #include = 0
            #if predicted_outcome > threshold_per_level[level]:
            #    include = 1

            #sentence_information_for_this_sentence['summary_include'] = include
            sentence_information_for_this_sentence['sentid'] = sentid
            sentence_information_for_this_sentence['summary_predicted'] = predicted_outcome
            sentence_information_for_this_sentence['sentence'] = sentence_texts[(threadid,sentid)]
            #print (threadid,sentid,include)

            #sentence_information[sentid] = sentence_information_for_this_sentence
            sentence_information.append(sentence_information_for_this_sentence)
        post = post_per_postid[postid]
        #print (postid,post)
        post['text'] = sentence_information

        '''
        # then, summarize on the post level
        '''

        level = 'post'
        featnames = feat_names_per_level[level]
        feat_weights = feat_weights_per_level[level]

        post = post_per_postid[postid]
        predicted_outcome = intercept

        for featurename in featnames:
            if featurename in columns_std:

                columndict_with_std_values = columns_std[featurename]
                #print(featurename, columndict_with_std_values)
                value = columndict_with_std_values[(threadid,postid)]

                if featurename in feat_weights:
                    weighted_value = feat_weights[featurename]*value
                    predicted_outcome += weighted_value
                else:
                    print("featurename not in lrm model:",featurename)
                #predicted[(threadid,postid)] = predicted_outcome
            else:
                print(("Feature from model has not been stored as column in the standardized data:",featurename))
        post['summary_predicted'] = predicted_outcome

        predicted_values_posts.append(predicted_outcome)
        #include = 0
        #if predicted_outcome >= threshold_per_level[level]:
        #    include = 1
        #post['summary_include'] = 1
        #print(threadid,postid,include)

        #print(postid,post)

    median_predicted_value_posts = numpy.median(predicted_values_posts)
    median_predicted_value_sents = numpy.median(predicted_values_sents)
    posts_with_decision = list()

    for postid in postidsforthread:
        post = post_per_postid[postid]
        sentence_information = post['text']
        for sentence_information_for_this_sentence in sentence_information:
            predicted_outcome_sent = sentence_information_for_this_sentence['summary_predicted']
            if predicted_outcome_sent > median_predicted_value_sents:
                sentence_information_for_this_sentence['summary_include'] = 1
            else:
                sentence_information_for_this_sentence['summary_include'] = 0
            print(sentence_information_for_this_sentence['summary_include'],sentence_information_for_this_sentence['sentence'], predicted_outcome_sent)
        post['text'] = sentence_information
        predicted_outcome_post = post['summary_predicted']
        if predicted_outcome_post > median_predicted_value_posts:
            post['summary_include'] = 1
        else:
            post['summary_include'] = 0

        posts_with_decision.append(post)

    openingpost['summary_predicted'] = 1 # always include the opening post in the summary
    openingpost['summary_include'] = 1
    thread_content['message'] = openingpost
    thread_content['comments'] = posts_with_decision
    thread['content'] = thread_content
    summarized_threads.append(thread)
    print (time.clock(), "\t", "thread summarized")


parsed_json['threads'] = summarized_threads
json.dump(parsed_json,json_out)

json_out.close()

