# coding: utf-8
import os
import json
from datetime import datetime
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.connections import connections
from pprint import pprint
import config
from ijournal import IJournal, journal_to_ijournal
from iissue import IIssue, issue_to_iissue
from iarticle import IArticle, article_to_iarticle

# DJANGO IMPORTS
from django.core.management import setup_environ
from django.core.exceptions import ObjectDoesNotExist

try:
    from scielomanager import settings
except ImportError:
    BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    BASE_PATH_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'scielomanager'))
    from sys import path
    path.append(BASE_PATH)
    path.append(BASE_PATH_APP)

    import settings

setup_environ(settings)

from journalmanager.models import Journal, Issue, Article

# Define a default Elasticsearch client
connections.create_connection(hosts=config.ES_HOSTS)

# Query simples:

# Pesquisar por Journal by collection
# {
#     "query": {
#         "nested": {
#           "path": "collections",
#             "query": {
#                 "match": {
#                     "collections.acronym": "spa"
#                 }
#             }
#         }
#     }
# }
s = Search(index=config.INDEX).query("nested", path="collections", query=Q("match", collections__acronym="spa"))
r = s.execute()

for hit in r:
    print(hit.meta.score, hit.title)

print json.dumps(s.to_dict())

# Pesquisar por um journal através do jid ou PID
print 80 * '*'
print "Get Journal by jid... "
s = Search(index=config.INDEX).query("match", jid="2e9f927cf7df4a9a9b3597fa49158e13")
r = s.execute()

for hit in r:
    print(hit.meta.score, hit.title)

print "DSL: %s" % json.dumps(s.to_dict())
print "Elasticsearch_dsl: %s" % 'query("match", jid="2e9f927cf7df4a9a9b3597fa49158e13")'

# Pesquisar por um article através do iid ou PID
print 80 * '*'
print "Get Article by aid... "
s = Search(index=config.INDEX).query("match", aid="ef9f8a8fd2f04308aac552c9ab39d1ff")
r = s.execute()

for hit in r:
    print(hit.meta.score, hit.aid)

print "DSL: %s" % json.dumps(s.to_dict())
print "Elasticsearch_dsl: %s" % 'query("match", aid="ef9f8a8fd2f04308aac552c9ab39d1ff")'


# Pesquisar atraves do jid de um journal seus issues
print 80 * '*'
print "Get Issues by journal using jid... using size=1000"
s = Search(index=config.INDEX).query("has_parent", parent_type="journal", query=Q("term", jid="e12fc1ffb85d4ec09b6fc60f9da56200")).sort("-year", "-volume", "-number")
s = s[:1000]  # Using from=0 and size=1000
r = s.execute()

for hit in r:
    # print hit
    print(hit.meta.score, hit.iid, hit.label, hit.year)

print "DSL: %s" % json.dumps(s.to_dict())
print "Elasticsearch_dsl: %s" % 'query("has_parent", parent_type="journal", query=Q("term", jid="e12fc1ffb85d4ec09b6fc60f9da56200"))'


# Pesquisar atraves do iid (issue) o seu pai journal
print 80 * '*'
print "Get Journal by issue using iid..."
# Pesquise pelo pai onde o filho é um issue e tem como atributo o iid="5ed510ccf03946ff8b9665a5468279f6"
s = Search(index=config.INDEX).query("has_child", type="issue", query=Q("term", iid="5ed510ccf03946ff8b9665a5468279f6"))
r = s.execute()

for hit in r:
    print(hit.meta.score, hit.jid)

print "DSL: %s" % json.dumps(s.to_dict())
print "Elasticsearch_dsl: %s" % 'query("has_child", type="issue", query=Q("term", iid="5ed510ccf03946ff8b9665a5468279f6"))'


# Pesquisar atraves do iid seus articles
print 80 * '*'
print "Get Articles by issue using iid..."
s = Search(index=config.INDEX).query("has_parent", parent_type="issue", query=Q("term", iid="af7ab671fbd041d9b8387f826c5f9b68"))
r = s.execute()

for hit in r:
    print hit
    print(hit.meta.score, hit.aid)

print "DSL: %s" % json.dumps(s.to_dict())
print "Elasticsearch_dsl: %s" % 'query("has_parent", type="issue", query=Q("term", iid="af7ab671fbd041d9b8387f826c5f9b68"))'
