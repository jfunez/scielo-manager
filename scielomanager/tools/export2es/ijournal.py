# coding: utf-8
import json
from datetime import datetime
from elasticsearch_dsl import DocType, String, Date, Integer, Nested, MetaField

import config


def journal_to_ijournal(model_instance):
    journal_collections = []
    for collection in model_instance.collections.all():
        journal_collections.append({
            'acronym': collection.acronym,
            'name': collection.name,
        })

    journal_use_licenses = None
    if model_instance.use_license:
        journal_use_licenses = {
            'license_code': model_instance.use_license.license_code,
            'reference_url': model_instance.use_license.reference_url,
            'disclaimer': model_instance.use_license.disclaimer
        }

    journal_timeline = []
    for status in model_instance.statuses.all().order_by('-since'):
        journal_timeline.append({
            'since': status.since,
            'reason': status.reason,
            'status': status.status
        })

    journal_subject_categories = [sc.term for sc in model_instance.subject_categories.all()]

    journal_study_areas = [sa.study_area for sa in model_instance.study_areas.all()]

    journal_social_networks = []
    if model_instance.twitter_user:
        journal_social_networks = [{
            'network': 'twitter',
            'account': journal.twitter_user,
        }]
    journal_cover_url = None
    if model_instance.cover:
        journal_cover_url = model_instance.cover.url

    journal_logo_url = None
    if model_instance.logo:
        journal_logo_url = model_instance.logo.url

    journal_previous_id = None
    if model_instance.previous_title:
        journal_previous_id = model_instance.previous_title.id

    journal_other_titles = []
    for title in model_instance.other_titles.all():
        journal_other_titles.append({
            'title': title.title,
            'category': title.category,
        })

    journal_current_status = None
    if model_instance.statuses.all():
        journal_current_status = model_instance.statuses.all().order_by('since')[0].status

    journal_missions = []
    for mission in model_instance.missions.all():
        journal_missions.append({
            'language': mission.language.iso_code,
            'description': mission.description,
        })

    result = {
        '_id': model_instance.jid,
        'jid': model_instance.jid,
        'collections': journal_collections,
        'use_licenses': journal_use_licenses,
        'timeline': journal_timeline,
        'national_code': model_instance.national_code,
        'subject_categories': journal_subject_categories,
        'study_areas': journal_study_areas,
        'social_networks': journal_social_networks,
        'title': model_instance.title,
        'title_iso': model_instance.title_iso,
        'short_title': model_instance.short_title,
        'created': model_instance.created,
        'updated': model_instance.updated,
        'acronym': model_instance.acronym,
        'scielo_issn': model_instance.scielo_issn,
        'print_issn': model_instance.print_issn,
        'eletronic_issn': model_instance.eletronic_issn,
        'subject_descriptors': model_instance.subject_descriptors.split('\n'),
        'init_year': model_instance.init_year,
        'init_vol': model_instance.init_vol,
        'init_num': model_instance.init_num,
        'final_num': model_instance.final_num,
        'final_vol': model_instance.final_vol,
        'final_year': model_instance.final_year,
        'copyrighter': model_instance.copyrighter,
        'online_submission_url': model_instance.url_online_submission,
        'cover_url': journal_cover_url,
        'logo_url': journal_logo_url,
        'previous_journal_id': journal_previous_id,
        'other_titles': journal_other_titles,
        'publisher_name': model_instance.publisher_name,
        'publisher_country': model_instance.publisher_country,
        'publisher_state': model_instance.publisher_state,
        'publisher_city': model_instance.publication_city,
        'publisher_address': None,  # TODO: FIX it!
        'publisher_telephone': None,  # TODO: FIX it!
        'current_status': journal_current_status,
        'mission': journal_missions,
    }
    return result


class IJournal(DocType):

    jid = String()
    collections = Nested(properties={'acronym': String(index='not_analyzed'),
                                     'name': String(index='not_analyzed')})
    use_licenses = Nested(properties={'license_code': String(index='not_analyzed'),
                                      'reference_url': String(index='not_analyzed'),
                                      'disclaimer': String(index='not_analyzed')})
    timeline = Nested(properties={'since': Date(),
                                  'reason': String(index='not_analyzed'),
                                  'status': String(index='not_analyzed')})
    national_code = String(index='not_analyzed')
    subject_categories = String(index='not_analyzed')
    study_areas = String(index='not_analyzed')
    social_networks = Nested(properties={'network': String(index='not_analyzed'),
                                         'account': String(index='not_analyzed')})
    title = String()
    title_iso = String()
    short_title = String()
    created = Date()
    updated = Date()
    acronym = String(index='not_analyzed')
    scielo_issn = String(index='not_analyzed')
    print_issn = String(index='not_analyzed')
    eletronic_issn = String(index='not_analyzed')
    subject_descriptors = String(index='not_analyzed')
    init_year = String(index='not_analyzed')
    init_vol = String(index='not_analyzed')
    init_num = String(index='not_analyzed')
    final_num = String(index='not_analyzed')
    final_vol = String(index='not_analyzed')
    final_year = String(index='not_analyzed')
    copyrighter = String(index='not_analyzed')
    online_submission_url = String(index='not_analyzed')
    cover_url = String(index='not_analyzed')
    logo_url = String(index='not_analyzed')
    previous_journal_id = String()
    other_titles = Nested(properties={'title': String(index='not_analyzed'),
                                      'category': String(index='not_analyzed')})
    publisher_name = String(index='not_analyzed')
    publisher_country = String(index='not_analyzed')
    publisher_state = String(index='not_analyzed')
    publisher_city = String(index='not_analyzed')
    publisher_address = String(index='not_analyzed')
    publisher_telephone = String(index='not_analyzed')
    current_status = String(index='not_analyzed')
    mission = Nested(properties={'description': String(index='not_analyzed'),
                                 'language': String(index='not_analyzed')})

    class Meta:
        index = config.INDEX
        dynamic = MetaField('strict')
        doc_type = 'journal'
