# encoding: utf-8
import math
import sys
import pickle
import re
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

def read_lemma(file):
    lemma_dict = {}

    with open(file, 'r') as fh:
        for line in fh.readlines():
            line = line.rstrip("\n")
            entity = line.split("\t")[0]
            category = line.split("\t")[2]
            lemma_dict[entity] = category
        fh.close()
    return lemma_dict

def prepare_files(entity_dict_file, unmatched_entities_file, w2v_file_sentence,lemma_file, spelling_file, term_freq):
    entity_dict = read_entities(entity_dict_file)
    unmatched_entities = [unicode(line.rstrip('\n'), "utf-8") for line in open(unmatched_entities_file,'r')]
    w2v_sentence = read_entities(w2v_file_sentence)
    lemma_dict = read_lemma(lemma_file)
    spelling_dict = read_lemma(spelling_file)
    tf_dict = load_extradictionary(term_freq)

    return entity_dict, unmatched_entities, w2v_sentence, lemma_dict, spelling_dict, tf_dict

def merge_all(entity_dict,unmatched_entities,w2v_sentence, lemma_dict, spelling_dict, term_freq_dict):

    with open('summary_file.txt', 'w') as fh:
        for entity in entity_dict:
            where_from = 'database'
            if entity in spelling_dict:
                where_from = 'spelling correction'
            elif entity in lemma_dict:
                where_from = 'lemma lookup'
            elif entity in w2v_sentence:
                where_from = 'word2vec'

            if entity in term_freq_dict:
                tf = str(term_freq_dict[entity])
            else:
                tf = 'unknown'
            category = entity_dict[entity]
            fh.write(entity + "\t" + tf + "\t" + where_from + "\t" + category + "\n")

        for entity in unmatched_entities:

            if entity in term_freq_dict:
                tf = str(term_freq_dict[entity])
            else:
                tf = 'unknown'

            fh.write(entity + "\t" + tf + "\t" + "unmatched" + "\t" + "unmatched" + "\n")
        fh.close()


def load_extradictionary(extra_dict):
    with open(extra_dict, "rb") as fh:
        extra_dictionary = pickle.load(fh)
        fh.close()
    return extra_dictionary

if __name__ == '__main__':
    entity_dict_file = sys.argv[1] # a txt file
    unmatched_entities_file = sys.argv[2] # a txt file
    w2v_file_sentence = sys.argv[3]
    lemma_file = sys.argv[4]
    spelling_file = sys.argv[5]
    term_freq = sys.argv[6]
    entity_dict,unmatched_entities,w2v_sentence, lemma_dict, spelling_dict, term_freq_dict = prepare_files(entity_dict_file, unmatched_entities_file, w2v_file_sentence, lemma_file, spelling_file, term_freq)
    merged_dict = merge_all(entity_dict,unmatched_entities,w2v_sentence, lemma_dict, spelling_dict, term_freq_dict)


