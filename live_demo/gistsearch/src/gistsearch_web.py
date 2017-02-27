from gistsearch import Semanticsearch
from Summaries import Summarizer
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify
import logging
from logging.handlers import RotatingFileHandler
from contextlib import closing
import json
import sys


# configuration
DEBUG = True
SECRET_KEY = 'gist'
USERNAME = 'admin'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)

#searcher = Semanticsearch()
categories_en = None
categories_nl = None
@app.route('/')
def show_empty():
	#return render_template('index.html', searchresult={})
	return app.send_static_file('index.html')


@app.route('/send', methods=['POST'])
def send_query():
	q = request.form['query']
	flash(q)
	qar = q.split(" ")
	res = json.loads(searcher.expanded_search(qar))
	flash( " ".join(res['query_words']) )
	return render_template('show_searchresult.html', searchresult=res)
	
	
@app.route('/send_summarized', methods=['POST'])
def send_query_summarized():
	q = request.form['query']
	flash(q)
	qar = q.split(" ")
	res = json.loads(searcher.expanded_search_fullthreads(qar))
	flash( " ".join(res['query_words']) )
	return render_template('show_searchresult_summarized.html', searchresult=res) #to adapt to summarized view
	

@app.route('/get_json', methods=['GET','POST'])
def get_json():
	q = request.args.get('query').lower()
	e = request.args.get('expand')
	i = request.args.get('corpus').lower()
	qar = q.split(" ")
	if e == "1":
		searcher.n_expand = 7
		searcher.n_results = 200
		logging.info('EXPANDED SEARCH with query: \"%s\" on index %s' % (q,i))
		return searcher.expanded_search(qar,i)
	else:
		logging.info('REGULAR SEARCH with query: \"%s\" on index %s' % (q,i))
		return searcher.regular_search(qar,i)
		
@app.route('/get_json_summarized', methods=['GET','POST']) # summarization is now done beforehand
def get_json_summarized():
	q = request.args.get('query').lower()
	i = request.args.get('corpus').lower()
	e = request.args.get('expand')
	qar = q.split(" ")
	if e == "1":
		searcher.n_expand = 7
		searcher.n_results = 200
		logging.info('EXPANDED SUMMARIZED SEARCH with query: \"%s\" on index %s' % (q,i))
		#return summarizer.get_summarized_thread(searcher.expanded_search_fullthreads(qar))
		return searcher.expanded_search_fullthreads(qar,i)
	else:
		logging.info('REGULAR SUMMARIZED SEARCH with query: \"%s\" on index %s' % (q,i))
		#return summarizer.get_summarized_thread(searcher.regular_search_fullthreads(qar))
		return searcher.regular_search_fullthreads(qar,i)


@app.route('/login', methods=['GET', 'POST'])
def login():
	error = None
	if request.method == 'POST':
		if request.form['username'] != app.config['USERNAME']:
			error = 'Invalid username'
		elif request.form['password'] != app.config['PASSWORD']:
			error = 'Invalid password'
		else:
			session['logged_in'] = True
			flash('You are logged in')
			return redirect(url_for('show_empty'))
	return render_template('login.html', error=error)


@app.route('/logout')
def logout():
	session.pop('logged_in', None)
	flash('You are logged out')
	return redirect(url_for('show_empty'))
	
@app.route('/get_categories_en')
def get_categories_en():
	return json.dumps(categories_en)
	#return jsonify(**categories)

@app.route('/get_categories_nl')
def get_categories_nl():
	return json.dumps(categories_nl)

	
if __name__ == '__main__':
	#indexname = sys.argv[1]
	categories_file_en = sys.argv[1]
	categories_file_nl = sys.argv[2]
	with open(categories_file_en, 'r') as fh:
		json_data = fh.read()
		jdata = json.loads(json_data)
		categories_en = jdata
		
	with open(categories_file_nl, 'r') as fh:
		json_data = fh.read()
		jdata = json.loads(json_data)
		categories_nl = jdata
	
	searcher = Semanticsearch()
	summarizer = Summarizer()
	logging.basicConfig(filename='gistsearch.log',level=logging.INFO)
	app.run(host='0.0.0.0')

