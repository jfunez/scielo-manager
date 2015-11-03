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
