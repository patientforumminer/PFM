import sys
import pickle
import re
from collections import Counter
from gensim.models import  Word2Vec
reload(sys)
sys.setdefaultencoding('utf-8')

def read_entities(file):
    entity_pattern = re.compile('^(.+)\t(.+)\n$')
    entity_dict = {}
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

def prepare_files(entity_dict_file, unmatched_entities_file, w2v_model):
    entity_dict = read_entities(entity_dict_file)
    unmatched_entities = [unicode(line.rstrip('\n'), "utf-8") for line in open(unmatched_entities_file,'r')]
    model = Word2Vec.load(w2v_model)
    return unmatched_entities,entity_dict, model

def load_extradictionary(extra_dict):
    with open(extra_dict, "rb") as fh:
        extra_dictionary = pickle.load(fh)
        fh.close()
    return extra_dictionary

# get the most common element in a list
def most_common(lst, th):
    if lst:
        data = Counter(lst)
        mc_val = data.most_common()[0][1]

        if mc_val >= th:
            result = [key for key, val in data.items() if val == mc_val]
            return result

def printCat(categories):
    result = ""
    for cat in categories:
        if result != "":
            result = result +  "; "  + cat
        else:
            result = result + cat
    return result

def cluster_w2v(entity,model,dict,topn, th):
    # check if entity is actually in model
    if entity in model:
        topn_words = model.similar_by_word(entity, topn)
        # list of topn similar words
        similar_words = [pair[0] for pair in topn_words]
        # extract categories of most similar words
        categories = []
        counter = 0
        for word in similar_words:
            if counter <= 5:
                if word in dict:
     # among the topn words (10) try to find the top 5 which are stored in the dictionary!
                    counter = counter +1
                    current_cats = dict[word]
                    categories = categories + current_cats.split(';')
            else:
                break
        if categories:
            result_categories = most_common(categories,th)
            if result_categories:
                return result_categories # return closest match

def run_cluster_w2v(unmatched_entities,dict, w2v_model,topn, th):
    with open('clustering_overview.txt', 'w') as fh:
        for entity in unmatched_entities:
            if entity.startswith('-'):
                entity = entity[1:]
            if entity.endswith('-'):
                entity = entity[:-1]

            if entity not in dict: #and entity not in tagged_dict:
                category = cluster_w2v(entity,w2v_model,dict,topn,th)

                if category:
                    dict[entity] = printCat(category) # update the entity dictionary to maximize the number of assigned categories
                    fh.write(entity + "\t" + printCat(category) + "\n")
                elif '-' in entity:
                    entity = entity.replace('--','-')
                    split_w = entity.split('-')
                    len_split = len(split_w)
                    if len_split > 2:
                        for i in range(len_split):
                            if i + 1 < len_split:
                                a = split_w[i]
                                b = split_w[i + 1]
                                if a and b:
                                    split_w.append(a + "-" + b)

                    for word in split_w:
                        if word not in dict:# and word not in tagged_dict:

                            category = cluster_w2v(word, w2v_model, dict, topn, th)
                            if category:
                                dict[word] = printCat(category)  # update the entity dictionary to maximize the number of assigned categories
                                fh.write(word+ "\t" + printCat(category) + "\n")
        fh.close()

def run_cluster_w2v_multiple_iterations(unmatched_entites,dict, w2v_model,topn, th, max_iter):
    iter = 1
    finish = False
    with open('updated_entity_dictionary_w2v_5_3_thread.txt', 'w') as fh:
        while not finish and iter <= max_iter:
            finish = True
            iter = iter + 1
            for entity in unmatched_entities:
                if entity.startswith('-'):
                    entity = entity[1:]
                if entity.endswith('-'):
                    entity = entity[:-1]
                if entity not in dict:
                    category = cluster_w2v(entity,w2v_model,dict,topn,th)
                    if category:
                        dict[entity] = printCat(category) # update the entity dictionary to maximize the number of assigned categories
                        fh.write(entity + "\t" + printCat(category) + "\n")
                        finish = False
                    elif '-' in entity:
                        split_w = entity.split('-')
                        len_split = len(split_w)
                        if len_split > 2:
                            for i in range(len_split):
                                if i + 1 < len_split:
                                    a = split_w[i]
                                    b = split_w[i + 1]
                                    if a and b:
                                        split_w.append(a + "-" + b)

                        for word in split_w:
                            if word not in dict:
                                category = cluster_w2v(word, w2v_model, dict, topn, th)
                                if category:
                                    dict[word] = printCat(
                                        category)  # update the entity dictionary to maximize the number of assigned categories
                                    fh.write(word + "\t" + printCat(category) + "\n")
                                    finish = False
        fh.close()

if __name__ == '__main__':
    topn = 8 # define the number of closest neighbors to look at
    th = 3 # what is the minimum number of overlapping categories in order to chose a category?
    max_iter = 3
    entity_dict_file = sys.argv[1] # a txt file
    unmatched_entities_file = sys.argv[2] # a txt file
    w2v_model = sys.argv[3]
    unmatched_entities,dict, model = prepare_files(entity_dict_file, unmatched_entities_file, w2v_model)
    run_cluster_w2v(unmatched_entities,dict,model,topn, th)
    #run_cluster_w2v_multiple_iterations(unmatched_entities, dict, model, topn, th, max_iter)