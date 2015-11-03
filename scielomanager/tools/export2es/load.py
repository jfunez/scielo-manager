# coding: utf-8
import os
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

IJournal.init()
IIssue.init()
IArticle.init()

for journal in Journal.objects.all():
    ijournal = IJournal(**journal_to_ijournal(journal))
    print 'saving journal', journal.id
    ijournal.save()

for issue in Issue.objects.all():
    try:
        iissue = IIssue(**issue_to_iissue(issue))
        iissue.save()
    except Exception, e:
        print e.message, 'FOR ISSUE: ', issue.pk, e.message
        continue
    else:
        print 'saving issue', issue.id

for article in Article.objects.filter(journal__isnull=False, issue__isnull=False):
    iarticle = IArticle(**article_to_iarticle(article))
    iarticle.save()

    print "Article issue iid: %s" % iarticle.issue_iid
