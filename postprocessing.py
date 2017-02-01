# encoding: utf-8
import sys
import pandas as pd
import re
def load_entity_count_file(file, summary_file):

    entity_file = pd.read_csv(file)
    entity_file_sorted = entity_file.sort_values('Entity Frequency', ascending=False)
    summary = pd.read_csv(summary_file)



    corpus = pd.read_csv('/home/nicole/TNO/PFM/EntityExtraction/DFW.CD', sep = "\\", names = ['IdNum','Word','IdNumLemma','Inl','InlDev','InlMln','InlLog'])



    # cutoff of try 250, 200, 100
    # for each word retrieve all entries, take maximum freq and determine whether to inlcude or not based ono cutoff
    # not if it is a bodypart (those can be very frequent)



    remove_idx = []
    removed_entities = []
    th = 100
    for idx in range(len(entity_file_sorted)):
        ent = entity_file_sorted['Matched Entity'].iloc[idx]
        if entity_file_sorted['Category'].iloc[idx] == 'Lichaamsdelen & Organen':
            continue

        entity = entity_file_sorted['Matched Entity'].iloc[idx]

        current_df = corpus[corpus['Word'] == entity]
        if len(current_df) != 0:
            if sum(current_df['InlMln']) > th:
                removed_entities.append(ent)
                remove_idx.append(idx)



    entity_file_sorted = entity_file_sorted.drop(entity_file_sorted.index[remove_idx])

    steps = []
    for entity in entity_file_sorted['Matched Entity']:
        step = summary[summary['Entity'] == entity]['Step']
        steps.append(step.iloc[0])

    entity_file_sorted['Step'] = steps


    entity_file_sorted.to_csv("evaluation_file_FINAL.csv")

    return removed_entities

id_pattern = re.compile('^(\d+)\n')
entity_pattern = re.compile('^(.+)\t(.+)\n$')

def read_entities(file, ent_lst):
    with open('viva_entities_new.txt', 'w') as myfile:
        with open(file, 'r') as fh:
            this_id = None
            for line in fh.readlines():
                match_id = id_pattern.search(line)
                if match_id:
                    this_id = match_id.group(1)
                    myfile.write(this_id + "\n")
                else:
                    match_entity = entity_pattern.search(line)
                    if (match_entity):
                        ent = match_entity.group(1)
                        cat = match_entity.group(2)
                        if ent not in ent_lst:
                            myfile.write(ent + "\t" + cat + "\n")
        fh.close()
    myfile.close()




if __name__ == '__main__':
    entity_count_file = sys.argv[1]
    viva_file = sys.argv[2]
    summary_file = sys.argv[3]
    ent_lst = load_entity_count_file(entity_count_file, summary_file)
    read_entities(viva_file, ent_lst)