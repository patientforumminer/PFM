# encoding: utf-8
import sys
import re
from pattern.nl import singularize, lemma

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

def prepare_files(entity_dict_file, unmatched_entities_file):
    entity_dict = read_entities(entity_dict_file)
    unmatched_entities = [unicode(line.rstrip('\n'), "utf-8") for line in open(unmatched_entities_file,'r')]
    return unmatched_entities,entity_dict


def run_lemmatization(entity_dict):
    lemma_dict = {}

    for ent in entity_dict:
        lemma_ent = singularize(ent)
        #lemma_ent = lemma(ent)
        if lemma_ent.replace(" ","") == "":
            lemma_ent = ent
        if not lemma_ent in lemma_dict:
            lemma_dict[lemma_ent] = [ent]
        else:
            old = lemma_dict[lemma_ent]
            lemma_dict[lemma_ent] = old + [ent]

    return lemma_dict

def run_lemma_lookup(lemma_dict, unmatched_entities, entity_dict):
    updated_dict = {}
    with open('lemmatized_overview.txt', 'w') as fh:

        for entity in unmatched_entities:
            if len(entity) >= 4: #more error prone for smaller words
                lemma_entity = singularize(entity)
                #lemma_entity = lemma(entity)
                if lemma_entity in lemma_dict:
                    if len(lemma_dict[lemma_entity]) ==1:
                        entity_match = lemma_dict[lemma_entity][0]
                        cat = entity_dict[entity_match]
                        if len(entity_match) >= 4:
                            updated_dict[entity] = cat
                            fh.write(entity + "\t" + entity_match + "\t" + cat + "\n")

    fh.close()
    return updated_dict


def update_files(entity_dict, unmatched_entities, updated_dict):
    with open('unmatched_entities_updated_lemma.txt', 'w') as fh1:

        for entity in unmatched_entities:
            if entity not in updated_dict:
                fh1.write(entity + "\n")
    fh1.close()

    with open('entity_dict_updated_lemma.txt', 'w') as fh2:
        for entity in entity_dict:
            fh2.write(entity + "\t" + entity_dict[entity] + "\n")
        for entity in updated_dict:
            fh2.write(entity + "\t" + updated_dict[entity] + "\n")

    fh2.close()


if __name__ == '__main__':
    entity_dict_file = sys.argv[1] # a txt file
    unmatched_entities_file = sys.argv[2] # a txt file
    unmatched_entities, entity_dict= prepare_files(entity_dict_file, unmatched_entities_file)
    lemma_dict = run_lemmatization(entity_dict)
    updated_dict = run_lemma_lookup(lemma_dict, unmatched_entities, entity_dict)
    update_files(entity_dict, unmatched_entities, updated_dict)
# update entity_dict accordingly, update unmatched entities