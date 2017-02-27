#!/usr/bin/env python
# encoding: utf-8

#=~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~=
#
# import_json_into_elasticsearch.py <json-file> <indexname>
#
# Author: Martijn Spitters, Maya Sappelli TNO
#
# Script to fill an elasticsearch index with data from a json-file
# Assumed content of data: 'msg_id', 'thread_id','text','time','type', 'author', 'thread_title', 'summary_include', 'summary_predicted', 'entities' 
#
# 'summary_include': {-1,0,1} --> indicates wheter the post should be included in the summary (-1 unknown, 0 no, 1 yes), 
#									this is based on summary_predicted with threshold 3.72
# 'summary_predicted': float --> indicates the predicted score of whether the post should be included in the summary
#
#=~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~=
import sys
import os
import re
import ijson
import json
import time
import decimal

from datetime import datetime
from elasticsearch import Elasticsearch

es = Elasticsearch(host='espfm')


def import_data(json_file, indexname):
	for j in ijson.items(json_file, 'item'):
		thread_id = j['thread_id']
		thread_title = j['thread_title']
		
		comments = j['content']['comments']
		comments.append(j['content']['message'])
		
		for i in comments:
			rec = {}
			rec['msg_id'] = i['msg_id']
			rec['thread_id'] = thread_id
			rec['thread_title'] =  thread_title
			for a in ('time','type', 'author', 'summary_include', 'summary_predicted'):
				if a in i:
					if isinstance(i[a], decimal.Decimal):
						rec[a] = float(i[a])
					else:
						rec[a] = i[a]
			if not isinstance(i['text'], basestring):
				new_list = []
				for el in i['text']:
					new_list.append({"sent_summary_include":el['summary_include'], "sent_summary_predicted": float(el['summary_predicted']) , "sentid": el['sentid'], "sentence":el['sentence']})
				rec['text'] = new_list
			else:
				new_list = []
				new_list.append({"sent_summary_include":1, "sent_summary_predicted": 5.31 , "sentid": i['msg_id'], "sentence":i['text']})
				rec['text'] = new_list
			
			if i['entities'] is not None:
				rec['entities'] = [dict(t) for t in set([tuple(d.items()) for d in i['entities']])]
				
			doc = json.dumps(rec)
			
			mid = rec['msg_id']

			try:
				res = es.index(index=indexname, doc_type='post', body=doc, id=mid)
			except:
				print "Something went wrong with inserting the post "
				time.sleep(5)
				
		


if __name__ == '__main__':
	data_file = sys.argv[1]
	indexname = sys.argv[2]
	import_data(open(data_file, 'r'), indexname)

	print "Finished"
