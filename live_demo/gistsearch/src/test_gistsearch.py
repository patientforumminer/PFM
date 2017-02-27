#!/usr/bin/env python
# encoding: utf-8

import sys
import os
import re
import json
import pprint
import itertools

from datetime import datetime
from gistsearch import Semanticsearch


def main():
    pp   = pprint.PrettyPrinter(indent=4)
    q    = sys.argv[1]
    nres = 10

    searcher = Semanticsearch()
    result = searcher.expanded_search(q)

    print json.dumps(result,indent=4)


    

if __name__ == '__main__':
    main()
    


# get a document by its id
#res = es.get(index="gist",id="160543202978_10151558102347979")

# get all documents from a certain thread
#res = es.search(index="gist", body={"query": {"filtered": {"filter": {"term": {"thread_id": "160543202978_10151558102347979"}}}}})

# match a phrase exactly in the text
#res = es.search(index="gist",size=max,body={'query':{'match_phrase':{'text':"inhibitor for PDGFRA"}}})

# match the occurrence of a specific entity
#res = es.search(index="gist",size=max,body={'query':{'match_phrase':{'entities.entity':"KIT"}}})

# filter out all documents which contain the entity KIT
#res = es.search(index="gist",size=max,body={"query": {"filtered": {"filter":{"term": {"entities.entity":"KIT"}}}}})


#print json.dumps(result,indent=4)




