# coding: utf-8
import os
from datetime import datetime
from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import connections
from pprint import pprint
import config
from ijournal import IJournal, journal_to_ijournal
from iissue import IIssue, issue_to_iissue
from iarticle import IArticle

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

# create the mappings in elasticsearch
IJournal.init()
IIssue.init()
# Article.init()

# create and save and journal
# journal = Journal(_id=1,
#                   jid="id do scielo manager",
#                   title='Revista de ElasticSearch XYZ',
#                   created=datetime.now(),
#                   social_networks=[{"network": "twitter", "account": "@jamil"},
#                                    {"network": "twitter", "account": "@juan"}])

# journal.save()

# journal = Journal.get(id=1)

# print journal.title

# s = Search(index="iopac").query("match", title="elasticsearch")

# response = s.execute()

# for hit in response:
#     print(hit.meta.score, hit.title)

# Display cluster health
# print connections.get_connection().cluster.health()

for journal in Journal.objects.all():
    ijournal = IJournal(**journal_to_ijournal(journal))
    print 'saving journal', journal.id
    ijournal.save()

for issue in Issue.objects.all():
    try:
        iissue = IIssue(**issue_to_iissue(issue))
        iissue.save()
    except Exception, e:
        print e.message, 'FOR ISSUE: ', issue.pk
        continue
    else:
        print 'saving issue', issue.id, 'parent: ', iissue.meta.parent


# s = Search(index=config.INDEX).query("match", title="saúde")
# response = s.execute()

# for hit in response:
#     import pdb; pdb.set_trace()
#     print(hit.meta.score, hit.title, hit.issue)
