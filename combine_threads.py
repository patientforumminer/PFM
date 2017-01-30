# coding=utf-8
# python3 combine_threads.py viva_summarized_threads viva_forum_latest_summarized.json
# python3 combine_threads.py bvn_summarized_threads bvn_forum_latest_summarized.json


import sys
import json
import time

filedirname = sys.argv[1]
outfilename = sys.argv[2]

threads = []
import glob
for file in glob.glob(filedirname+"/*[0-9].json"):
	print(file)
	json_string = ""
	with open(file,'r') as json_file:
		for line in json_file:
			json_string += line.rstrip()
	parsed_json = json.loads(json_string)
	threads.append(parsed_json)


json_out = open(outfilename, 'w')
json.dump(threads,json_out)
json_out.close()
	
print (time.clock(), "\t", "thread printed")


