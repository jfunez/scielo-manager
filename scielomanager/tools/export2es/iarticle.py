# coding: utf-8

from lxml import etree

from datetime import datetime
from elasticsearch_dsl import DocType, String, Date, Integer, Nested, MetaField

import packtools
import config

CSS = '/static/css/style_article_html.css'


def article_to_iarticle(model_instance):

    htmls = []
    if model_instance.xml:
        try:
            for lang, output in packtools.HTMLGenerator(model_instance.xml.root_etree, valid_only=False, css=CSS):
                htmls.append({'language': lang, 'source': etree.tostring(output, encoding='utf-8', method='html', doctype=u"<!DOCTYPE html>")})
        except Exception as e:
            print "Article aid: %s, sem html, Error: %s" % (model_instance.aid, e.message)

    if model_instance.issue:
        issue_iid = model_instance.issue.iid
    else:
        issue_iid = None

    if model_instance.journal:
        journal_jid = model_instance.journal.jid
    else:
        journal_jid = None

    result = {
        '_id': model_instance.aid,
        'aid': model_instance.aid,
        'issue_iid': issue_iid,
        'journal_jid': journal_jid,
        'created': model_instance.created_at,
        'updated': model_instance.updated_at,
        'title': model_instance.get_value(model_instance.XPaths.ARTICLE_TITLE),
        'section': model_instance.get_value(model_instance.XPaths.HEAD_SUBJECT),
        'htmls': htmls,
        'domain_key': model_instance.domain_key,
    }
    return result


class IArticle(DocType):

    aid = String(index="not_analyzed")
    issue_iid = String(index="not_analyzed")
    journal_jid = String(index="not_analyzed")
    title = String(index="not_analyzed")
    section = String(index="not_analyzed")
    created = Date()
    updated = Date()
    htmls = Nested(properties={'language': String(index='not_analyzed'),
                               'source': String(index='no')})
    domain_key = String(index="not_analyzed")

    class Meta:
        index = config.INDEX
        dynamic = MetaField('strict')
        doc_type = 'article'
