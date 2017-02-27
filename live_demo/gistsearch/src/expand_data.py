#!/usr/bin/env python
# encoding: utf-8

#=~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~=
#
# expand_data.py <file with message entities> <directory with facebook message jsons> <dataset-name> <summariesfile> 
#
# Author: Martijn Spitters, Maya Sappelli TNO
#
# Script to read forum data (message,comment structure) from json (FB-format) or xml files (Viva-format)
# It expands the data with entities in the messages --> entity file format = 
# <message-id> \n
# <entity> \t <category>
#
# And with summary indications (if available) --> summary file format tab-seperated columns:
# - threadid: id of opening post in json
# - postid: id of comment in json
# - abspos: position of comment in thread, comment 0 is opening post and always included in summary so not included
# - predicted: predicted value of regresion model (larger is more likely that post will be selected for summary by humans)
# - selected_based_on_threshold: {1,0} that indicates if a post should be included in summary, based on threshold of 3.72 on predicted value (trained on Viva data)
#
# 'summary_include': {-1,0,1} --> indicates wheter the post should be included in the summary (-1 unknown, 0 no, 1 yes), 
#									this is based on summary_predicted with threshold 3.72
# 'summary_predicted': float --> indicates the predicted score of whether the post should be included in the summary
#
#=~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~=

import sys
import os
import re
import json
import bs4 as bs

entity_dict = {}
summaries_dict = {}

def read_summaries(file):
	ignoreheader = True
	with open(file,'r') as fh:
		for line in fh.readlines():
			if ignoreheader:
				ignoreheader = False
			else:
				els = line.split("\t")
				tid = els[0]
				mid = els[1]
				summary = int(els[4].strip())
				summarypred = float(els[3])
				summaries_dict[tid] = {}
				#print "added",tid, mid
				summaries_dict[tid][mid] = {'include_summary':summary, 'summary_predicted_value':summarypred}

def read_entities(file, dataset):
	if "viva" in dataset:
		key_categories = {'Disease':'Ziekte', 'Activity':'Activiteit', 'AnatomicalStructure':'Lichaamsdeel','Species':'bacterieën/virussen', 'ChemicalSubstance':'medicijnen/supplementen', 'ChemicalCompound':'medicijnen/supplementen',  'Eukaryote':'voedsel', 'Food':'voedsel', 'CultivatedVariety':'voedsel', 'Biomolecule':'medicijnen/supplementen'}
		id_pattern = re.compile('^(\d+)\n')
		entity_pattern = re.compile('^(.+)\t(.+)\n$')
	else:
		key_categories = ['Cell or Molecular Dysfunction', 'Body Part, Organ, or Organ Component', 'Disease or Syndrome', 'Therapeutic or Preventive Procedure', 'Neoplastic Process', 'Organic Chemical,Pharmacologic Substance', 'Biologically Active Substance,Pharmacologic Substance','Amino Acid, Peptide, or Protein,Immunologic Factor,Pharmacologic Substance', 'Amino Acid, Peptide, or Protein,Pharmacologic Substance', 'Pharmacologic Substance','Gene or Genome', 'Sign or Symptom', 'Food', 'Diagnostic Procedure', 'Medicines', 'Supplements']
		id_pattern = re.compile('^([\d+\_]+)(\.ti\.\d+)')
		entity_pattern = re.compile('^(\S+)\t(.+)\n$')

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
						if this_id not in entity_dict:
							entity_dict[this_id] = []
						entity_dict[this_id].append({'entity':ent,'category':cat})


		fh.close()						   
		return entity_dict
		
		
def get_entities(i):
	if i in entity_dict:
		return entity_dict[i]
		
def get_summary(threadid, mid):	
	if threadid in summaries_dict:
		#print threadid, mid
		if threadid == mid:
			#print 1,1
			return 1,1
		elif mid in summaries_dict[threadid]:
			#print threadid,mid,summaries_dict[threadid][mid]
			return summaries_dict[threadid][mid]['include_summary'],summaries_dict[threadid][mid]['summary_predicted_value'] 
		else: # assume that message is not relevant, since thread evaluated
			return 0,0
	#print 'no thread', threadid
	return -1, -1 # we don't know



def parse_json_files(indir):
	result = []
	for root, dirs, files in os.walk(indir):
		for f in files:						   
			if f.lower().endswith(".json") and "_comment_" not in f:
				f = os.path.join(root, f)

				with open(f, 'r') as fh:
					json_data = fh.read().encode("utf-8")
					jdata = json.loads(json_data)
					if "id" in jdata and "created_time" in jdata and "message" in jdata: # and len(jdata["message"]) >= 5:
						m_time = jdata["created_time"].encode("utf-8")
						m_id = jdata["id"].encode("utf-8")
						m_txt = jdata["message"].encode("utf-8").replace('\n', ' ')
						m_ent = get_entities(m_id)
						m_sum, m_pred = get_summary(m_id,m_id)
						result.append({'type':'message','id':m_id,'thread_id':m_id,'time':m_time,'text':m_txt,'summary_include':m_sum, 'summary_predicted':m_pred,'entities':m_ent})
						
						

						if "comments" in jdata and "data" in jdata["comments"]:
							for c in jdata["comments"]["data"]:
								if "id" in c and "created_time" in c and "message" in c: # and len(c["message"]) >= 5:
									c_time = c["created_time"].encode("utf-8")
									c_id = c["id"].encode("utf-8")
									c_txt = c["message"].encode("utf-8").replace('\n', ' ')
									c_ent = get_entities(c_id)
									c_sum, c_pred = get_summary(m_id, c_id)
									result.append({'type':'comment','id':c_id,'thread_id':m_id,'time':c_time,'text':c_txt,'summary_include':c_sum, 'summary_predicted':c_pred, 'entities':c_ent})
									
				
					fh.close()
	return json.dumps(result)

def parse_xml_files(indir):
	result = []
	for root, dirs, files in os.walk(indir):
		for f in files:						   
			if f.lower().endswith(".xml"):
				f = os.path.join(root, f)

				with open(f, 'r') as fh:
					content = fh.read()
					soup = bs.BeautifulSoup(content, 'xml')
					threads = soup.findAll('thread')
				
					for thread in threads:
						entity = {'entity':'null','category':thread.category.string}						
						threadid = thread['id']
						posts = thread.posts.findAll('post')
						m_title = thread.title.string.encode("utf-8")
						#print len(posts)
						for post in posts:
							m_time = post.timestamp.string.encode("utf-8")
							m_id = post["id"].encode("utf-8")
							m_txt = post.body.string.encode("utf-8").replace('\n', ' ')
							m_ent = get_entities(threadid + m_id)
							m_auth = post.author.string.encode("utf-8")
							
							
							#m_ent =  entity
							
							m_sum, m_pred = get_summary(threadid, threadid)		
							if m_id=="0":
								result.append({'type':'message','id':threadid,'thread_id':threadid,'time':m_time,'text':m_txt,'author':m_auth, 'thread_title':m_title, 'summary_include':m_sum, 'summary_predicted':m_pred, 'entities':m_ent})
							else:
								c_time = post.timestamp.string.encode("utf-8")
								c_id = threadid + m_id
								c_txt = post.body.string.encode("utf-8").replace('\n', ' ')
								c_auth = post.author.string.encode("utf-8")
								m_ent = get_entities(c_id)
								c_sum, c_pred = get_summary(threadid, c_id)
								#c_ent = entity
								
								result.append({'type':'comment','id':c_id, 'm_id':m_id, 'thread_id':threadid,'time':c_time,'text':c_txt, 'author':c_auth, 'summary_include':c_sum, 'summary_predicted':c_pred, 'entities':m_ent})
				
					fh.close()
	return json.dumps(result)


if __name__ == '__main__':
	# Arguments: <file with message entities> <directory with facebook message jsons> <dataset-name> <summariesfile> 
	entityfile = sys.argv[1]
	indir = sys.argv[2]
	dataset = sys.argv[3]
	summaries = None
	
	entity_dict = read_entities(entityfile, dataset)
	
	if not "None" == sys.argv[4]:
		summariesfile = sys.argv[4]
		summaries =	 read_summaries(summariesfile)
		

	if os.path.isdir(indir):
		if "viva" in dataset:
			result = parse_xml_files(indir)
		else:
			result = parse_json_files(indir)
		print result
	else:
		print "Input directory %s is not a directory." % indir


