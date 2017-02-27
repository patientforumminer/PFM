# encoding: utf-8
import sys
import TagDutchEntities_adapted # the main script
import fuzzy_lookup # for spelling correction
import cluster_w2v # for Word2vec clustering
import lemma_lookup # for lemmatization
import merge_w2v_lemma_results
import summary_file
import pandas as pd
import pickle
import link_entities_GIST
import postprocessing


if __name__ == '__main__':
    data_file = sys.argv[1]
    translation_file = sys.argv[2]

    entity_file = "entity_dictionary.txt"

    # where do you want to save the file?



    # be aware that you will need the following files ar some point:
    # a stopword_list in the current folder
    # - the term frequency dictionary
    # - a Word2vec model
    # - key categories file for merging and selecting categories


    # first run the main script for the initial tagging



    TagDutchEntities_adapted.load_translationdictionary(translation_file)
    TagDutchEntities_adapted.tag_data(data_file, 'None', 'None')
    # entiy_file and current entity dictionary are stored in current folder
    # next produce matched and unmatched entities files which will be stored int he current directory.
    TagDutchEntities_adapted.findUnmatchedEntities(TagDutchEntities_adapted.read_entities(entity_file), data_file)

    # after the initial tagging run the spelling correction script, i.e. fuzzy_lookup.py

    print "Finished initial tagging"

    unmatched_entities_file = 'unmatched_entities.txt'
    term_freq_dict = '/extra_files/term_freq_dict_GIST.txt'
    entity_dict = fuzzy_lookup.read_entities(entity_file)
    unmatched_entities,trie = fuzzy_lookup.prepare_files(entity_file, unmatched_entities_file)
    updated_dict = fuzzy_lookup.run_fuzy_lookup(unmatched_entities,trie, term_freq_dict)
    fuzzy_lookup.update_files(entity_dict, unmatched_entities, updated_dict)
    # this part produces the files spelling_corrected_overview.txt, unmatched_entities_updated_sc.txt, entity_dict_updated_sc.txt
    # in the same directory

    # update the unmatched_entities.txt and matched_entities.txt based on this file

    TagDutchEntities_adapted.load_translationdictionary(translation_file)
    TagDutchEntities_adapted.tag_data(data_file, 'unmatched_entities_updated_sc.txt','entity_dict_updated_sc.txt')
    TagDutchEntities_adapted.findUnmatchedEntities(TagDutchEntities_adapted.read_entities(entity_file), data_file)

    print "Finished spelling correction and updating of files"
    # next: based on the results from the spelling correction run the Word2Vec clustering and the lemma_lookup

    # first lemma_lookup

    unmatched_entities, entity_dict= lemma_lookup.prepare_files(entity_file, unmatched_entities_file)
    lemma_dict = lemma_lookup.run_lemmatization(entity_dict)
    updated_dict = lemma_lookup.run_lemma_lookup(lemma_dict, unmatched_entities, entity_dict)
    # this part produces the files: 'lemmatized_overview.txt'

    print "Finished Lemma lookup"

    # next w2v clustering:

    topn = 8 # define the number of closest neighbors to look at
    th = 3 # what is the minimum number of overlapping categories in order to chose a category?
    w2v_model = 'word2vec/500/w2v_model_VIVA_GIST_BC_500_3' # I guess I should always use this one! the more data the better?
    unmatched_entities,dict, model = cluster_w2v.prepare_files(entity_file, unmatched_entities_file, w2v_model)
    cluster_w2v.run_cluster_w2v(unmatched_entities,dict,model,topn, th)
    # this step produces the files: clustering_overview.txt

    print "Finished Word2vec clustering"
    # next the results from the previous two steps need to be merged, it uses the unmatched entities file from
    # spelling correction step

    w2v_file_sentence = 'clustering_overview.txt'
    lemma_file = 'lemmatized_overview.txt'
    entity_dict,unmatched_entities,w2v_sentence, lemma_dict = merge_w2v_lemma_results.prepare_files(entity_file, unmatched_entities_file, w2v_file_sentence, lemma_file)
    merged_dict = merge_w2v_lemma_results.merge_w2v_lemma(w2v_sentence, lemma_dict)
    merge_w2v_lemma_results.update_files(entity_dict, unmatched_entities, merged_dict)
    # this produces the files unmatched_entities_updated_lemma_w2v.txt, entity_dict_updated_lemma_w2v.txt

    #lastly rerun the main script to get the current entity file, unmatched_entities and matched_entities
    TagDutchEntities_adapted.load_translationdictionary(translation_file)
    TagDutchEntities_adapted.tag_data(data_file, 'unmatched_entities_updated_lemma_w2v.txt', 'entity_dict_updated_lemma_w2v.txt')
    TagDutchEntities_adapted.findUnmatchedEntities(TagDutchEntities_adapted.read_entities(entity_file), data_file)

    print "Finished merging of results and updating files"
    # produce the summary file in csv format

    spelling_file = 'spelling_corrected_overview.txt'
    term_freq = term_freq_dict
    entity_dict,unmatched_entities,w2v_sentence, lemma_dict, spelling_dict, term_freq_dict = summary_file.prepare_files(entity_file, unmatched_entities_file, w2v_file_sentence, lemma_file, spelling_file, term_freq)
    merged_dict = summary_file.merge_all(entity_dict,unmatched_entities,w2v_sentence, lemma_dict, spelling_dict, term_freq_dict)
    # produces summary_file.txt

    # produce a sorted csv file
    summary_file = pd.read_csv('summary_file.txt', sep = '\t', names = ['Entity', 'Frequency', 'Step', 'Category'])
    summary_file['Frequency']= summary_file['Frequency'].apply(pd.to_numeric, errors='ignore')
    summary_file_sorted = summary_file.sort_values(['Frequency', 'Step','Category'], ascending=[False, False, False])
    summary_file_sorted.to_csv('summary_file_sorted.csv')

    print "Finished producing summary_file.csv"

    # produce the extracted categories file for creating the key cateogories
    entity_dict = pd.read_csv('entity_dictionary.txt', sep='\t',names=['entities', 'category'])

    # extract the different categories:

    unique_cat = list(set(list(entity_dict['category'])))
    print "Number of unique categories: " + str(len(unique_cat))

    result_file = open("extracted_categories_GIST.txt", "w")

    sorted_dict = entity_dict.sort_values('category')
    sorted_dict.to_csv('sorted_categories_GIST.csv')

    for i in range(len(unique_cat)):
        num_elem = len(entity_dict[entity_dict['category'] == unique_cat[i]])
        result_file.write(unique_cat[i] + "\t" + str(num_elem) + "\n")

    result_file.close()

    ### build the category dictionary

    extracted_categories = pd.read_csv('extracted_categories_GIST.txt', sep='\t',names=['Category', 'Frequency'])

    # do some preprocessing on the extracted categories:


    # extracted_categories.sort_values('Frequency', ascending = False).to_csv('extracted_cat.csv')

    dict = {'Body Part, Organ, or Organ Component': 'Lichaamsdelen & Organen',
            'Body Location or Region': 'Lichaamsdelen & Organen', 'Body Space or Junction': 'Lichaamsdelen & Organen',
            'Bone': 'Lichaamsdelen & Organen', 'Diagnostic Procedure': 'Diagnostiek',
            'Disease or Syndrome': 'Ziekte of Syndroom', 'Anatomical Abnormality': 'Ziekte of Syndroom',
            'Congential Abnormality': 'Ziekte of Syndroom', 'Neurologic Manifestations': 'Ziekte of Syndroom',
            'Injury or Poisoning': 'Letsel', 'weight': 'Gewicht', 'dosage' : 'Dosering'}

    unwanted_cat = ['finding', 'gene or genome', 'idea or concept', 'quantitative concept', 'geographic area', 'animal',
                    'inorganic chemical', 'qualitative concept', 'intellectual product', 'mammal', 'organization',
                    'experimental model of disease']
    words_of_interest = ['disease', 'diagnostic procedure', 'mental or behavioral dysfunction',
                         'neoplastic process', 'organism function', 'pathologic function',
                         'hazardous or poisonous substance', 'injury or poisoning', 'symptom', 'food',
                         'therapeutic or preventive procedure', 'daily or recreational activity',
                         'biomedical or dental material', 'biomedical occupation or discipline', 'virus', 'bacterium',
                         'fungus', 'pharmacologic substance', 'drug', 'amino acid', 'protein', 'hormone', 'antibiotic',
                         'chemical']
    categories = ['Ziekte of Syndroom', 'Diagnostiek', 'Mentale/Gedrags Dysfunctie',
                  'Neoplastisch Proces', 'Menselijke Functies', 'Pathologieën', 'Giftige Stoffen', 'Letsel',
                  'Symptomen', 'Voedsel', 'Behandelingen', 'Activiteit', 'Biomedisch Material', 'Beroep/Discipline',
                  'Virus, Bacterie & Fungus', 'Virus, Bacterie & Fungus', 'Virus, Bacterie & Fungus',
                  'Vitaminen, Hormonen, Medicijnen, etc.', 'Vitaminen, Hormonen, Medicijnen, etc.',
                  'Vitaminen, Hormonen, Medicijnen, etc.', 'Vitaminen, Hormonen, Medicijnen, etc.',
                  'Vitaminen, Hormonen, Medicijnen, etc.', 'Vitaminen, Hormonen, Medicijnen, etc.',
                  'Vitaminen, Hormonen, Medicijnen, etc.']

    # took category mental process out -> explain in the discussion why

    def test_unwanted(cat, list):
        for elem in list:
            if elem in cat:
                return True

        return False
    def test_unwanted2(cat):
        # second test:
        cat_list = cat.split(";")
        if len(cat_list) > 1:
            if not ("organic chemical" in cat or "protein" in cat):
                return True

        return False


    for idx in range(len(words_of_interest)):
        current = words_of_interest[idx]
        current_df = extracted_categories[extracted_categories['Category'].str.lower().str.contains(current)]
        for cat in current_df['Category']:
            if not cat in dict and not test_unwanted(cat.lower(), unwanted_cat):
                if current == 'pharmacologic substance':
                    if not test_unwanted2(cat.lower()):
                        dict[cat] = categories[idx]
                else:
                    dict[cat] = categories[idx]


    with open("key_categories_GIST.txt", "wb") as myFile:
        pickle.dump(dict, myFile)

    #run the link entities file , it assumes that the json is already in the correct format and only requires
    #the matched entities to be linked to the posts and threads

    entityfile = 'entities_viva.txt'
    key_categories = 'key_categories_GIST.txt'

    entity_dict, cat_dict, entity_count_dict, entity_dict_final = link_entities_GIST.read_entities(entityfile, key_categories)
    link_entities_GIST.store_category_counts(cat_dict, entity_count_dict, entity_dict_final)
    link_entities_GIST.parse_json(data_file)
    # produces entity_dict_updated_sc.txt and entity_summary_count.txt

    # final step: produce the evaluation file
    entity_file = pd.read_csv('entity_summary_count.txt', sep="\t",
                              names=['Matched Entity', 'Category', 'Entity Frequency', 'Category Frequency',
                                     'True Entity?', 'Correct Category?', 'Dont know', 'In Context?', 'Comments'])
    entity_file_sorted = entity_file.sort_values('Entity Frequency', ascending=False)
    entity_file_sorted.to_csv('evaluation_file_GIST.csv')


    #update the entity_file and rerun the linking of entities
    entity_count_file = 'evaluation_file_GIST.csv'
    viva_file = 'entities_viva.txt'
    summary_file = 'summary_file_sorted.csv'

    ent_lst = postprocessing.load_entity_count_file(entity_count_file, summary_file)
    postprocessing.read_entities(viva_file, ent_lst)

    #now do the relinking

    # run the link entities file , it assumes that the json is already in the correct format and only requires
    # the matched entities to be linked to the posts and threads

    entityfile = 'viva_entities_new.txt'

    entity_dict, cat_dict, entity_count_dict, entity_dict_final = link_entities_GIST.read_entities(entityfile,
                                                                                                   key_categories)
    link_entities_GIST.store_category_counts(cat_dict, entity_count_dict, entity_dict_final)
    link_entities_GIST.parse_json(data_file)



    print "Finished linking the matched entities and producing the evaluation file"




