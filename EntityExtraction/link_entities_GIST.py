#!/usr/bin/env python
# encoding: utf-8

import sys
import os
import re
import json
import pickle

entity_dict = {}
category_dict = {}
entity_count_dict = {}
entity_dict_final = {}
def read_entities(file, key_categories_file):

	with open(key_categories_file, "rb") as fh:
		key_categories = pickle.load(fh)
		fh.close()

	id_pattern = re.compile('^(\d+)\n')
	entity_pattern = re.compile('^(.+)\t(.+)\n$')

	with open(file,'r') as fh:
		this_id = None
		for line in fh.readlines():
			match_id = id_pattern.search(line)

			if match_id:
				this_id = match_id.group(1)
			else:
				match_entity = entity_pattern.search(line)
				if(match_entity):
					ent = match_entity.group(1)
					cat = match_entity.group(2)
					if cat in key_categories:
						save_cat = key_categories[cat]
						if ent not in entity_count_dict:
							entity_count_dict[ent] = 1
							entity_dict_final[ent] = save_cat
						else:
							entity_count_dict[ent] = entity_count_dict[ent]+1


						if save_cat not in category_dict:
							category_dict[save_cat] = 1
						else:
							category_dict[save_cat] = category_dict[save_cat] + 1

						if this_id not in entity_dict:
							entity_dict[this_id] = []
						entity_dict[this_id].append({'entity':ent,'category':key_categories[cat]})


		fh.close()
		return entity_dict, category_dict, entity_count_dict, entity_dict_final

def store_category_counts(category_dict, entity_count_dict, entity_dict):
	with open('category_counts.txt', 'w') as myfile:
		for cat in category_dict:
			myfile.write(cat + "\t" + str(category_dict[cat]) + "\n")
		myfile.close()

	with open('entity_summary_count.txt', 'w') as myfile:
		for ent in entity_count_dict:
			cat = entity_dict[ent]
			myfile.write(ent + "\t" +entity_dict[ent]+ "\t" + str(entity_count_dict[ent])+ "\t"+ str(category_dict[cat]) + "\n")
		myfile.close()

def get_entities(i):
	if i in entity_dict:
		return entity_dict[i]

def parse_json(data_file):
	new_json = []
	with open(data_file, 'r') as fh:
		json_data = json.loads(fh.read().encode("utf-8"))
		fh.close()

	for idx in json_data:

		# id = idx['id'].encode("utf-8")
		# threadid = idx['thread_id'].encode("utf-8")
		# m_time = str(idx['time']).encode("utf-8")
		# m_id = id
		# m_txt = idx['text'].encode("utf-8").replace('\n', ' ').replace('\r', '')
		# m_ent = get_entities(id)
		# m_auth = str(idx['poster_id']).encode("utf-8")
		# m_title = "no title"
		# m_type = idx['type'].encode("utf-8")

		#result.append({'type': m_type, 'id': m_id, 'thread_id': threadid, 'time': m_time, 'text': m_txt, 'author': m_auth,'thread_title': m_title, 'entities': m_ent})
		id = idx['id'].encode("utf-8")
		idx['entities'] =  get_entities(id)
		new_json.append(idx)

	with open('DATA_json_final.json', 'w') as fp:
		json.dump(new_json, fp)
		fp.close()



if __name__ == '__main__':
	# Arguments: <file with message entities> <directory with message xmls>
	entityfile = sys.argv[1]
	key_categories = sys.argv[2]
	json_data = sys.argv[3]

	entity_dict, cat_dict, entity_count_dict, entity_dict_final = read_entities(entityfile,key_categories)
	store_category_counts(cat_dict, entity_count_dict, entity_dict_final)
	parse_json(json_data)

    # save the result

