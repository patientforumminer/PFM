FROM python:2.7
ADD . /live_demo
WORKDIR live_demo
RUN pip install -r requirements.txt

# RUN ElasticSearch
#RUN /etc/init.d/elasticsearch start

# Fill database
#CMD ["curl", "-XGET http://localhost:9200/viva/_status"]
#CMD ["python", "./import_json_into_elasticsearch.py live_demo/gistsearch/data/viva/viva_input_data_for_elasticsearch_latest.json viva"]

#CMD python ./import_json_into_elasticsearch.py gistsearch/data/viva/viva_input_data_for_elasticsearch_latest.json viva

CMD python ./import_json_into_elasticsearch.py test.json test