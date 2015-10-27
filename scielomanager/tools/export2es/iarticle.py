# coding: utf-8

from datetime import datetime
from elasticsearch_dsl import DocType, String, Date, Integer, Nested, MetaField

import config


def article_to_iarticle(model_instance):

    htmls = {
        'language': 'pt',
        'source': 'htmlpt'
    }

    if model_instance.issue:
        issue_iid = model_instance.issue.iid
    else:
        issue_iid = None

    result = {
        '_parent': issue_iid,
        '_id': model_instance.aid,
        'aid': model_instance.aid,
        'created': model_instance.created_at,
        'updated': model_instance.updated_at,
        'htmls': htmls,
        'domain_key': model_instance.domain_key,
    }
    return result


class IArticle(DocType):

    aid = String(index="not_analyzed")
    created = Date()
    updated = Date()
    htmls = Nested(properties={'language': String(index='not_analyzed'),
                               'source': String(index='not_analyzed')})
    domain_key = String(index="not_analyzed")

    class Meta:
        index = config.INDEX
        parent = MetaField(type='issue')
        dynamic = MetaField('strict')
        doc_type = 'article'
