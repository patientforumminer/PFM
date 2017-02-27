FROM python:2.7
ADD . /gistsearch
WORKDIR gistsearch/src
RUN pip install -r requirements.txt
EXPOSE 5000

CMD python ./gistsearch_web.py categories_en.json categories_nl.json
