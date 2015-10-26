# coding: utf-8

from datetime import datetime
from elasticsearch_dsl import DocType, String, Date, Integer, Nested, MetaField

import config


def issue_to_iissue(model_instance):
    issue_sections = []
    for section in model_instance.section.all():
        subjects = []
        for subject in section.titles.all():
            subjects.append({
                'name': subject.title,
                'language': subject.language.iso_code,
            })

        issue_sections.append({
            # 'order': section.order
            'subjects': subjects
        })

    issue_use_licenses = None
    if model_instance.use_license:
        issue_use_licenses = {
            'license_code': model_instance.use_license.license_code,
            'reference_url': model_instance.use_license.reference_url,
            'disclaimer': model_instance.use_license.disclaimer
        }

    issue_cover_url = None
    if model_instance.cover:
        issue_cover_url = model_instance.cover.url

    result = {
        '_parent': model_instance.journal.jid,
        '_id': model_instance.iid,
        'iid': model_instance.iid,
        'sections': issue_sections,
        'volume': model_instance.volume,
        'number': model_instance.number,
        'created': model_instance.created,
        'updated': model_instance.updated,
        'start_month': model_instance.publication_start_month,
        'end_month': model_instance.publication_end_month,
        'year': model_instance.publication_year,
        'use_licenses': issue_use_licenses,
        'cover_url': issue_cover_url,
        'label': model_instance.label,
        'order': model_instance.order,
        'bibliographic_legend': model_instance.bibliographic_legend,
    }
    return result


class IIssue(DocType):

    iid = String(index="not_analyzed")
    sections = Nested(properties={'order': Integer(index='not_analyzed'),
                                  'subjects': Nested(properties={
                                    "name": String(index='not_analyzed'),
                                    "language": String(index='not_analyzed')})
                                  })
    volume = String(index="not_analyzed")
    number = String(index="not_analyzed")
    created = Date()
    updated = Date()
    start_month = String(index="not_analyzed")
    end_month = String(index="not_analyzed")
    year = String(index="not_analyzed")
    use_licenses = Nested(properties={'license_code': String(index='not_analyzed'),
                                      'reference_url': String(index='not_analyzed'),
                                      'disclaimer': String(index='not_analyzed')})
    cover_url = String(index='not_analyzed')
    label = String(index='not_analyzed')
    order = Integer()
    bibliographic_legend = String(index='not_analyzed')

    class Meta:
        index = config.INDEX
        parent = MetaField(type='journal')
        dynamic = MetaField('strict')
        doc_type = 'issue'
