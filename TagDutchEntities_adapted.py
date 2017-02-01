#!/usr/bin/env python
# encoding: utf-8

#=~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~=
# python 2.7
# TagDutchEntities.py <DBPedia.tts> <dataToTag.json> -
#
#reads a DBpedia.tts to create a translation dictionary with the following structure <http://dbpedia.org/resource/Anemia> <http://www.w3.org/2000/01/rdf-schema#label> "Bloedarmoede"@nl .
#
# Processes a JSON file of messages, and looks up the words in the message in the translation dictionary.
# Executes a SPARQL query to obtain the DBpedia type of the entity
#
# Returns 1) a file with the entity dictionary that was created from the DBpedia and JSON files
# and 	  2) a list of entities per messages id; structured as follows:
# <message-id> \n
# <entity> \t <category>
#
# Author: Maya Sappelli, TNO
#
#
#=~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~=

import sys
import re
import json
import pickle
import MySQLdb
from SPARQLWrapper import SPARQLWrapper, JSON
sparql = SPARQLWrapper("http://dbpedia.org/sparql")
sparql.setReturnFormat(JSON)

sparql_mesh = SPARQLWrapper("https://id.nlm.nih.gov/mesh/sparql")
sparql_mesh.setReturnFormat(JSON)
from nltk import word_tokenize
from collections import Counter
from nltk.corpus import stopwords
stopwords_dutch = stopwords.words('dutch')

reload(sys)
sys.setdefaultencoding('utf-8')

entity_dict = {}
translationNL_EN = {}
noEntityTranslation = {}
database_tracer = {}


stoplist = set()
print("Read stopword list")
with open(r'stoplist_dutch.txt') as stoplist_file:
    for line in stoplist_file:
        stopword = line.rstrip()
        stoplist.add(stopword)


for word in stopwords_dutch:
    if word not in stoplist:
        stoplist.add(word)

stopwords = stoplist



def load_extradictionary(extra_dict):
    with open(extra_dict, "rb") as fh:
        extra_dictionary = pickle.load(fh)
        fh.close()
    return extra_dictionary

# load translation dictionary (based on DBpedia)
def load_translationdictionary(file):
    entity_pattern = re.compile('^<(.+)> <.+> "(.+)"@nl.+$')
    with open(file,'r') as fh:
        for line in fh.readlines():
            #print line
            match_entity = entity_pattern.search(line)
            if match_entity:
                english_url = match_entity.group(1)
                nl_entity = match_entity.group(2)
                #print nl_entity + "\t" + english_url
                translationNL_EN[nl_entity.lower()] = english_url
        fh.close()


# get the most common element in a list
def most_common(lst):
    if lst:
        data = Counter(lst)
        mc_val = data.most_common()[0][1]
        result = [key for key, val in data.items() if val == mc_val]
        return result

def get_ULMS_category(query, ULMS_cur):
    query = repr(query).replace("'", "\'").replace('"','\"')
    ULMS_cur.execute("SELECT sty FROM MRCONSO a, MRSTY b WHERE a.cui = b.cui AND str = {};".format(query))

    categories = []
    for row in ULMS_cur.fetchall():
        category = row[0]
        categories.append(category)
    # choose the majority vote of categories
    #print categories
    return most_common(categories)

def sparql_query_getMeSHCategory(term):
    try:
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
        PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
        PREFIX mesh2015: <http://id.nlm.nih.gov/mesh/2015/>
        PREFIX mesh2016: <http://id.nlm.nih.gov/mesh/2016/>
        SELECT ?d ?dName ?c ?cName
        FROM <http://id.nlm.nih.gov/mesh>
        WHERE
        {
        ?d a meshv:TopicalDescriptor .
        ?d meshv:broaderDescriptor ?c .
        ?d rdfs:label ?dName .
        ?c rdfs:label ?cName
        FILTER(LCASE(str(?dName)) = """+"'"+term+"'"+""")

        }
        """

        sparql_mesh.setQuery(query)	# the previous query as a literal string
        result = sparql_mesh.query().convert()


        categories = []
        for r in result['results']['bindings']:
            if r['dName']['value'] == term.capitalize() and not(r['cName']['value'] == term.capitalize()):
                category = r['cName']['value']
                #return category
                categories.append(category)
        return categories
    except Exception, e:
        print e


# issue SPARQL query to obatain DBPedia type given the resource-url

def sparql_query_getCategory(url):
    # extract most specific type
    try:

        query = """

        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT distinct ?type
        WHERE
        {
        <""" + url + """> rdf:type ?type .
        filter not exists {
            ?subclass ^a  <""" + url + """>;
                rdfs:subClassOf ?type .
            filter ( ?subclass != ?type )
        }
        }

		"""

        sparql.setQuery(query)	# the previous query as a literal string
        result = sparql.query().convert()
        categories = []
        for r in result['results']['bindings']:
            if "http://dbpedia.org/ontology" in r['type']['value']:
                category = r['type']['value'].replace("http://dbpedia.org/ontology/","")
                categories.append(category)
        return categories
    except Exception, e:
        print e

def calc(a,b):
    if not float(b) == float(0):
        return str(float(a)/float(b))
    else:
        return 0


def preprocess_pipeline(text):
    text1 = re.sub(
        r'\b' + r'((\(<{0,1}https|\(<{0,1}http|\[<{0,1}https|\[<{0,1}http|<{0,1}https|<{0,1}http)(:|;| |: )\/\/|www.)[\w\.\/#\?\=\+\;\,\&\%_\n-]+(\.[a-z]{2,4}\]{0,1}\){0,1}|\.html\]{0,1}\){0,1}|\/[\w\.\?\=#\+\;\,\&\%_-]+|[\w\.\?\=#\+\;\,\&\%_-]+|[0-9]+#m[0-9]+)+(\b|\s|\/|\]|\)|>)',
        ' ', text) # habe das leerzeichen hier entfernt
    frac_list = re.findall(r'( [0-9]+\/[0-9]+ )',text1 )
    for num in frac_list:
        a = num.split('/')[0]
        b = num.split('/')[1]
        result = calc(a, b)
        result = round(float(result), 3)
        result = str(result).replace('.', ',')
        text1 = text1.replace(num, result, 1)
    # next remove all special characters but hyphens and x/y where x and y numbers
    text2 = re.sub(r'[\+\*#\!\?;><\^@\|\.=&%\(\)$~_§\\:\…\"\[\]´`\‘\'‘’“…¨]+', ' ', text1) # extra characters: “  think again about paranthesis ‘zomaar’ gebeuren… “medicaliserende” meisje’ ¨ ‘gif’
    text3 = re.sub(r'\/', ' ', text2)
    text4 = re.sub(r'(?<![0-9]),(?![0-9]+)', ' ', text3)

    text5 = re.sub(r',(?=[a-zA-Z])+', ' ', text4)
    text6 = re.sub(r'(?<=[a-zA-Z]),', ' ', text5)

    return text6

def printCat(categories):
    result = ""
    for cat in categories:
        if result != "":
            result = result +  "; "  + cat
        else:
            result = result + cat
    return result

def categorize_reordered(w, translationNL_EN,entity_dict, noEntityTranslation, ULMS_cur):

    # hardcode this assignment
    if w == 'gist':
        entity_dict[w] = 'Neoplastic Process'
        database_tracer[w] = 'Manual'
    # try to catch different cancer diseases:
    elif w.endswith("kanker"):
        entity_dict[w] = 'Neoplastic Process'
        database_tracer[w] = 'Manual'
    elif w.endswith("tumor"):
        entity_dict[w] = 'Neoplastic Process'
        database_tracer[w] = 'Manual'
    else:
        english_url = translationNL_EN[w]
        w_en = english_url.replace("http://dbpedia.org/resource/", "").replace("_(disambiguation)", "")
        w_en = re.sub(r'\(\w+\)', '', w_en)
        w_en = w_en.lower()
        w_en = w_en.replace("_", " ")
        categoriesULMS = get_ULMS_category(w_en, ULMS_cur)


        if categoriesULMS and not (len(categoriesULMS) == 1 and categoriesULMS[0] == 'Finding'):
            entity_dict[w] = printCat(categoriesULMS)
            database_tracer[w] = 'UMLS'

        else:
            categories = sparql_query_getCategory(english_url)

            if categories:
                entity_dict[w] = printCat(categories)
                database_tracer[w] = 'DBpedia'

            else: #mesh lookup is currenlty way toooo slow!
                noEntityTranslation[w] = 1

            # else:
            #     categoriesMESH = sparql_query_getMeSHCategory(w_en)
            #     if categoriesMESH:
            #         entity_dict[w] = printCat(categoriesMESH)
            #         database_tracer[w] = 'MESH'
            #     else:
            #         noEntityTranslation[w]=1

def categorize(w, translationNL_EN,entity_dict, noEntityTranslation, ULMS_cur):

    english_url = translationNL_EN[w]
    categories = sparql_query_getCategory(english_url)

    if categories:
        entity_dict[w] = printCat(categories)

    else:
        w_en = english_url.replace("http://dbpedia.org/resource/","").replace("_(disambiguation)","")
        w_en = re.sub(r'\(\w+\)','', w_en)
        w_en = w_en.lower()
        w_en = w_en.replace("_", " ")
        categoriesULMS = get_ULMS_category(w_en, ULMS_cur)

        if categoriesULMS and not (len(categoriesULMS) == 1 and categoriesULMS[0] == 'Finding'):
            entity_dict[w] = printCat(categoriesULMS)

        elif len(w) < 6:
            noEntityTranslation[w] = 1
        else: # does it really make sense tu put unmatches stuff into noEntityTranslation?
            categoriesMESH = sparql_query_getMeSHCategory(w_en)
            if categoriesMESH:
                entity_dict[w] = printCat(categoriesMESH)
            else:
                noEntityTranslation[w]=1



# looks up the words in a text to see whether a matching translation & DBPedia type can be found
def tag_data(data_file, noEntityTranslation_file, entity_dict_file):

    # in case we just need to add something to an existing entity_dictionary
    if not entity_dict_file == 'None':
        entity_dict = read_entities(entity_dict_file)
    else:
        entity_dict = {}

    if not noEntityTranslation_file == 'None':
        noEntityTranslation = read_unmatched_entites(noEntityTranslation_file)
    else:
        noEntityTranslation = {}

    print len(entity_dict)
    print len(noEntityTranslation)

    # open output file
    with open(data_file, 'r') as fh:
        json_data = json.loads(fh.read().encode("utf-8"))
        fh.close()

    with open('entities_viva.txt','w') as fh:
        ################################ ULMS MySQL database needed for this to work ###################################
        # open the ULMS data base and create curser object
        db = MySQLdb.connect(host="localhost",  # your host, usually localhost
                             user="root",  # your username
                             passwd="!xOYN#?",  # your password
                             db="umls")  # name of the data base

        ULMS_cur = db.cursor()
        ################################ ULMS MySQL database needed for this to work ###################################

        for i in json_data:
            id = i["id"]  # i['thread_id'] +
            fh.write(id + "\n")
            #print i['thread_id'], i["id"]

            preprocessed_text = preprocess_pipeline(str(i['text']).encode('utf-8')) # do I have to encode again as unicode for propper storing?
            preprocessed_text = unicode(preprocessed_text, errors = 'replace')
            preprocessed_text = preprocessed_text.replace('�',' ')
            # search for dosis (x HTP) and weights (x mg/g/kg) and classify by hand
            doses = re.findall(r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}HTP|-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}htp)', preprocessed_text)
            preprocessed_text = re.sub(r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}HTP|-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}htp)',' ', preprocessed_text)

            mgs = re.findall(r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}mg |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}MG )', preprocessed_text)
            preprocessed_text = re.sub(r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}mg |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}MG )', ' ', preprocessed_text)
            gs = re.findall(r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}g |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}G )', preprocessed_text)
            preprocessed_text = re.sub(r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}g |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}G )', ' ',preprocessed_text)
            kgs= re.findall(r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}kg |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}KG )', preprocessed_text)
            preprocessed_text = re.sub(r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}kg |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}KG )', ' ',preprocessed_text)

            for w in doses:
                w = w.lower()
                if not w in entity_dict:
                    entity_dict[w] = 'Amino Acid'

                if w in entity_dict:
                    fh.write(w + "\t" + entity_dict[w] + "\n")

            weights = gs+kgs
            for w in weights:
                w = w.lower()
                if not w in entity_dict:
                    entity_dict[w] = 'weight'

                if w in entity_dict:
                    fh.write(w + "\t" + entity_dict[w] + "\n")

            for w in mgs:
                w= w.lower()
                if not w in entity_dict:
                    entity_dict[w] = 'dosage'
                if w in entity_dict:
                    fh.write(w + "\t" + entity_dict[w] + "\n")


            # tokenize and remove stopwords
            # remove double spaces:
            preprocessed_text = ' '.join(preprocessed_text.split())
            tokenized = word_tokenize(preprocessed_text)

            if tokenized:
                str_words = ' '.join(tokenized)
                content_words_noNum = ''.join(i for i in str_words if not i.isdigit())
                content_words_noNum = re.sub(',', ' ', content_words_noNum)
                words = content_words_noNum.split()
                words = [w for w in words if w.lower() not in stopwords] # better here

                for w in words:
                    w = w.lower()
                    w = w.replace('--', '-')
                    if w.startswith('-'):
                        w = w[1:]
                    if w.endswith('-'):
                        w = w[:-1]

                    if w and w not in stopwords: # check whether string is non-empty
                        w_set = list(set(w.replace(" ", "")))
                        if len(w_set) == 1 and w_set[0] == '-':
                            continue



                        if not w in entity_dict and not w in noEntityTranslation: #need to use lemma?	# how do we deal with spelling errors?!


                            if w in translationNL_EN:
                               categorize_reordered(w, translationNL_EN, entity_dict, noEntityTranslation, ULMS_cur)
                            elif '-' in w:
                                noEntityTranslation[w] =1

                                split_w = w.split('-')
                                len_split = len(split_w)
                                if len_split > 2:
                                    for i in range(len_split):
                                        if i + 1 < len_split:
                                            a = split_w[i]
                                            b = split_w[i + 1]
                                            if a and b:
                                                split_w.append(a + "-" + b)
                                split_w = [w for w in split_w if w not in stopwords]
                                for split in split_w:
                                    if not split.replace(" ", "") == "":
                                        if not split in entity_dict and not split in noEntityTranslation:

                                            if split in translationNL_EN:
                                                categorize_reordered(split, translationNL_EN, entity_dict, noEntityTranslation, ULMS_cur)
                                            else:
                                                noEntityTranslation[split] = 1

                                        if split in entity_dict:
                                            fh.write(split + "\t" + entity_dict[split] + "\n")

                            else:
                                noEntityTranslation[w]=1

                        # in cae we use the extra arguments:
                        if not entity_dict_file == 'None' and not noEntityTranslation_file == 'None':
                            if '-' in w and not w in entity_dict: # but only if whole term wasn't matched already.
                                w = w.replace('--', '-')

                                split_w = w.split('-')
                                len_split = len(split_w)
                                if len_split > 2:
                                    for i in range(len_split):
                                        if i + 1 < len_split:
                                            a = split_w[i]
                                            b = split_w[i + 1]
                                            if a and b:
                                                split_w.append(a + "-" + b)
                                split_w = [w for w in split_w if w not in stopwords]
                                for split in split_w:
                                    if not split.replace(" ", "") == "":
                                        if not split in entity_dict and not split in noEntityTranslation:

                                            if split in translationNL_EN:
                                                categorize_reordered(split, translationNL_EN, entity_dict, noEntityTranslation,
                                                                     ULMS_cur)
                                            else:
                                                noEntityTranslation[split] = 1

                                        if split in entity_dict:
                                            fh.write(split + "\t" + entity_dict[split] + "\n")

                        if w in entity_dict: # this is for the VIVA file!
                            fh.write(w + "\t" + entity_dict[w] + "\n")

            fh.flush()
        # close the ULMS database
        db.close()
        fh.close()

    with open('entity_dictionary.txt','w') as fh:
        for key in entity_dict:
            fh.write(key + "\t" + entity_dict[key]	+ "\n")
        fh.close()

    with open('database_tracer.txt','w') as fh:
        for key in database_tracer:
            fh.write(key + "\t" + database_tracer[key]	+ "\n")
        fh.close()


def read_entities(file):
    entity_pattern = re.compile('^(.+)\t(.+)\n$')

    with open(file,'r') as fh:
        for line in fh.readlines():
            match_entity = entity_pattern.search(line)
            if(match_entity):
                ent = match_entity.group(1)
                cat = match_entity.group(2)
                if not ent in entity_dict:
                    entity_dict[unicode(ent)] = unicode(cat)
        fh.close()
    return entity_dict

def read_unmatched_entites(file):
    unmatched_entities = [unicode(line.rstrip('\n'), "utf-8") for line in open(file, 'r')]
    for entity in unmatched_entities:
        noEntityTranslation[entity] = 1

    return noEntityTranslation


def findUnmatchedEntities(entity_dict, data_file):
    with open(data_file, 'r') as fh:
        json_data = json.loads(fh.read().encode("utf-8"))
        fh.close()

    entities = {}
    noEntityTranslation = {}
    for i in json_data:
        preprocessed_text = preprocess_pipeline(str(i['text']).encode('utf-8'))  # do I have to encode again as unicode for propper storing?
        preprocessed_text = unicode(preprocessed_text, errors='replace')
        preprocessed_text = preprocessed_text.replace('�', ' ')
        # search for dosis (x HTP) and weights (x mg/g/kg) and classify by hand
        doses = re.findall(
            r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}HTP|-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}htp)',
            preprocessed_text)
        preprocessed_text = re.sub(
            r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}HTP|-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}htp)',
            ' ', preprocessed_text)

        mgs = re.findall(
            r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}mg |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}MG )',
            preprocessed_text)
        preprocessed_text = re.sub(
            r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}mg |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}MG )',
            ' ', preprocessed_text)
        gs = re.findall(
            r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}g |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}G )',
            preprocessed_text)
        preprocessed_text = re.sub(
            r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}g |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}G )',
            ' ', preprocessed_text)
        kgs = re.findall(
            r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}kg |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}KG )',
            preprocessed_text)
        preprocessed_text = re.sub(
            r'(-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}kg |-{0,1} {0,1}[0-9]{0,1},{0,1}[0-9]+ {0,1}-{0,1} {0,1}KG )',
            ' ', preprocessed_text)

        for w in doses:
            w = w.lower()
            if w in entity_dict:
                entities[w] = 1
            else:
                noEntityTranslation[w] = 1

        weights = mgs + gs + kgs
        for w in weights:
            w = w.lower()
            if w in entity_dict:
                entities[w] = 1
            else:
                noEntityTranslation[w] = 1

        # tokenize and remove stopwords
        # remove double spaces:
        preprocessed_text = ' '.join(preprocessed_text.split())
        tokenized = word_tokenize(preprocessed_text)
        if tokenized:
            str_words = ' '.join(tokenized)
            content_words_noNum = ''.join(i for i in str_words if not i.isdigit())
            content_words_noNum = re.sub(',', ' ', content_words_noNum)

            words = content_words_noNum.split()
            words = [w for w in words if w.lower() not in stopwords]

            # so this can be considered as the true matched and unmatched entities. it tires to match the whole term and not parts of it individually.
            for w in words:
                w = w.lower()
                w = w.replace('--', '-')
                if w.startswith('-'):
                    w = w[1:]
                if w.endswith('-'):
                    w = w[:-1]
                if w and w not in stopwords:
                    w_set = list(set(w.replace(" ","")))
                    if len(w_set) ==1 and w_set[0] == '-':
                        continue
                    if w in entity_dict:
                        entities[w] = 1
                    # doesn't look at this if it can already match the whole term
                    elif '-' in w:
                        noEntityTranslation[w] = 1

                        split_w = w.split('-')
                        len_split = len(split_w)
                        if len_split > 2:
                            for i in range(len_split):
                                if i + 1 < len_split:
                                    a = split_w[i]
                                    b = split_w[i+1]
                                    if a and b:
                                        split_w.append(a+ "-" + b)
                        split_w = [w for w in split_w if w not in stopwords]
                        for split in split_w:
                            if not split.replace(" ", "") == "":
                                if split in entity_dict:
                                    entities[split] = 1
                                    #print 'here'
                                else:
                                    noEntityTranslation[split] = 1
                    else:
                        noEntityTranslation[w] = 1



    with open('unmatched_entities.txt','w') as fh:
        for key in noEntityTranslation:
            fh.write(key.encode('utf-8') + "\n")
        fh.close()
    with open('matched_entities.txt','w') as fh:
        for key in entities:
            fh.write(key.encode('utf-8') + "\n")
        fh.close()


if __name__ == '__main__':
    data_file = sys.argv[1]
    translation_file = sys.argv[2]
    entity_dict_file = sys.argv[3] # is the goal is to add something to an existing entity dictionary
    unmatched_entities = sys.argv[4]
    entity_file = "entity_dictionary.txt"


    if not "None" in translation_file:
        load_translationdictionary(translation_file)
        tag_data(data_file, unmatched_entities, entity_dict_file) #don't need the extra_dictionary anymore, can also use unmatched entities to speed up the process.
    else:
        findUnmatchedEntities(read_entities(entity_file), data_file)
