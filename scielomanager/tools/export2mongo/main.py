# coding: utf-8
import os
import json
from datetime import datetime
from pprint import pprint
from mongoengine import *
import config

# DJANGO IMPORTS
from django.core.management import setup_environ
from django.core.exceptions import ObjectDoesNotExist

from opac_schema.v1 import models as opac_models

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

import utils
from journalmanager.models import Journal, Issue, Article


connect(config.MONGODB_SETTINGS['name'])


for journal in Journal.objects.all():
    djournal = opac_models.Journal(**utils.journal_to_djournal(journal))
    djournal.save()

    print 'Save journal: ', journal.id, ' with id: ', djournal.id


for issue in Issue.objects.all():
    try:
        iissue = opac_models.Issue(**utils.issue_to_dissue(issue))
        iissue.save()
        print 'Save issue: ', issue.id
    except Exception, e:
        print e.message, 'FOR ISSUE: ', issue.pk, e.message
        continue
    else:
        print 'Save issue: ', issue.id

for article in Article.objects.filter(journal__isnull=False, issue__isnull=False):
    darticle = opac_models.Article(**utils.article_to_darticle(article))

    darticle.save()

    print "Save article:", darticle.aid
