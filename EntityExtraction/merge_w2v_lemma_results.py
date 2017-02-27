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

def prepare_files(entity_dict_file, unmatched_entities_file, w2v_file_sentence,lemma_file):
    entity_dict = read_entities(entity_dict_file)
    unmatched_entities = [unicode(line.rstrip('\n'), "utf-8") for line in open(unmatched_entities_file,'r')]
    w2v_sentence = read_entities(w2v_file_sentence)
    lemma_dict = read_lemma(lemma_file)

    return entity_dict, unmatched_entities, w2v_sentence, lemma_dict

def merge_w2v_lemma(w2v, lemma):
    print len(w2v)
    print len(lemma)
    for entity in lemma:
        if entity not in w2v:
            w2v[entity] = lemma[entity]
    print len(w2v)
    return w2v


def update_files(entity_dict, unmatched_entities, updated_dict):
    with open('unmatched_entities_updated_lemma_w2v.txt', 'w') as fh1:

        for entity in unmatched_entities:
            if entity not in updated_dict:
                fh1.write(entity + "\n")
    fh1.close()

    with open('entity_dict_updated_lemma_w2v.txt', 'w') as fh2:
        for entity in entity_dict:
            fh2.write(entity + "\t" + entity_dict[entity] + "\n")
        for entity in updated_dict:
            fh2.write(entity + "\t" + updated_dict[entity] + "\n")

    fh2.close()



if __name__ == '__main__':
    entity_dict_file = sys.argv[1] # a txt file
    unmatched_entities_file = sys.argv[2] # a txt file
    w2v_file_sentence = sys.argv[3]
    lemma_file = sys.argv[4]
    entity_dict,unmatched_entities,w2v_sentence, lemma_dict = prepare_files(entity_dict_file, unmatched_entities_file, w2v_file_sentence, lemma_file)
    merged_dict = merge_w2v_lemma(w2v_sentence, lemma_dict)
    update_files(entity_dict, unmatched_entities, merged_dict)

