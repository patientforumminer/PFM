# encoding: utf-8
import marisa_trie
import editdistance
import math
import sys
import pickle
from pattern.nl import singularize, lemma
import re
reload(sys)
sys.setdefaultencoding('utf-8')
from operator import itemgetter

def prepare_files(entity_dict_file, unmatched_entities_file):
    entity_dict = [unicode(line.rstrip('\n'), "utf-8") for line in open(entity_dict_file,'r')]
    unmatched_entities = [unicode(line.rstrip('\n'), "utf-8") for line in open(unmatched_entities_file,'r')]
    entities = []
    categories = []
    for w in entity_dict:
        entity = w.split("\t")[0]
        entities.append(entity)
        category = w.split("\t")[1]
        categories.append(str.encode(str(category)))

    trie = marisa_trie.BytesTrie(zip(entities,categories))
    return unmatched_entities,trie

def load_extradictionary(extra_dict):
    with open(extra_dict, "rb") as fh:
        extra_dictionary = pickle.load(fh)
        fh.close()
    return extra_dictionary


def edits1(word):
    "All edits that are one edit away from `word`."
    letters    = 'abcdefghijklmnopqrstuvwxyz'
    splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
    deletes    = [L + R[1:]               for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
    replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
    inserts    = [L + c + R               for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)

def get_all_substrings(input_string):
  length = len(input_string)
  return [input_string[i:j+1] for i in xrange(length) for j in xrange(i,length)]


def relEditDistance(w1,w2):
    reldist = float(editdistance.eval(w1,w2))/float(len(w1))
    return reldist


def fuzzy_lookup(word, maxRelEdit, tf_dict,trie):
    # 1. produce all words that are one edit distance away
    candidates = edits1(word)
    # next reduce list to all candidates that can be found in the TRIE
    final_candidates = []
    for w in candidates:
        if w in trie:
            if word[0] == w[0]:
                final_candidates.append(w)

    if len(final_candidates) ==1 and relEditDistance(word, final_candidates[0]) <= maxRelEdit:
        return final_candidates[0]
    elif final_candidates:
        edit_distances = []
        edit_distances_weighted = []
        for candidate in final_candidates:
            # if first letter of candidate different from original word: penalize this
            if candidate[0] != word[0]: #first letters are different
                edit_distances.append(maxRelEdit+1)
            else:
                edit_distances.append(relEditDistance(word, candidate))
                edit_distances_weighted.append(relEditDistance(word, candidate) + 0.1*weighting(word, candidate, tf_dict))
        min_dist = min(edit_distances)
        min_dist_weighted = min(edit_distances_weighted)
        if min_dist <= maxRelEdit:
            # print word
            # print final_candidates
            # print edit_distances
            # print edit_distances_weighted
            # print "\n"
            return final_candidates[edit_distances_weighted.index(min_dist_weighted)]
    # otherwise use the TRIE for possible candidates
    else:
        substrings = [w for w in get_all_substrings(word) if len(w) >= math.ceil(len(word) / 3)]
        candidates = []
        distances = []
        for substring in substrings:
            possible_candidates = trie.keys(substring)
            if len(possible_candidates) > 2:
                possible_candidates = possible_candidates[0:2]

            for c in possible_candidates:
                if c in trie and relEditDistance(word,c) <= maxRelEdit:
                    if c[0] == word[0]:
                        candidates.append(c)
                        distances.append(relEditDistance(word,c))
        if candidates:
            return candidates[distances.index(min(distances))]

def common_start(sa, sb):
    """ returns the longest common substring from the beginning of sa and sb """
    def _iter():
        for a, b in zip(sa, sb):
            if a == b:
                yield a
            else:
                return

    return ''.join(_iter())

def weighting(w1, w2, tf_dict):
    # find out whether part of the string is included in in the original word
    # largest matching substring normalized by original word, the larger the better
    lemma_w1 = lemma(w1)
    lemma_w2 = lemma(w2)
    lemma_dist = relEditDistance(lemma_w1, lemma_w2)
    len_longest_common_substring =  len(common_start(w1,w2))/float(len(w1))

    return (lemma_dist + 1/(len_longest_common_substring+0.1))/2


def run_fuzy_lookup(unmatched_entities,trie, dict):
    updated_dict = {}
    tf_dict = load_extradictionary(dict)
    with open('spelling_corrected_overview.txt', 'w') as fh:
        for entity in unmatched_entities: # only correct spelling errors for words that occur very few times in the term frquency dictionary
            if entity in tf_dict and tf_dict[entity] <= 2:
                current_entity = fuzzy_lookup(entity,0.16,tf_dict,trie) #maybe use 0.17 -> better 0.16
                if current_entity:
                    category = trie[current_entity][0]
                    fh.write(entity + "\t" + current_entity + "\t" + category + "\n")
                    updated_dict[entity] = category
        fh.close()
        return updated_dict


def update_files(entity_dict, unmatched_entities, updated_dict):
    with open('unmatched_entities_updated_sc.txt', 'w') as fh1:

        for entity in unmatched_entities:
            if entity not in updated_dict:
                fh1.write(entity + "\n")
    fh1.close()

    with open('entity_dict_updated_sc.txt', 'w') as fh2:
        for entity in entity_dict:
            fh2.write(entity + "\t" + entity_dict[entity] + "\n")
        for entity in updated_dict:
            fh2.write(entity + "\t" + updated_dict[entity] + "\n")

    fh2.close()

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
################################################################################
def test(trie):
    print fuzzy_lookup(u'mena', 0.1)
    if u'girl' in trie:
        print 'ja'
################################################################################

if __name__ == '__main__':
    entity_dict_file = sys.argv[1] # a txt file
    unmatched_entities_file = sys.argv[2] # a txt file
    term_freq_dict = sys.argv[3]
    entity_dict = read_entities(entity_dict_file)
    unmatched_entities,trie = prepare_files(entity_dict_file, unmatched_entities_file)
    updated_dict = run_fuzy_lookup(unmatched_entities,trie, term_freq_dict)
    update_files(entity_dict, unmatched_entities, updated_dict)
    #test(trie)