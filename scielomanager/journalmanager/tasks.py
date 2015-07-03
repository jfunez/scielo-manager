# coding: utf-8
""" Tasks do celery para a aplicação `journalmanager`.

  - Todas as tasks que executam `Article.save` devem tomar cuidado com
    problemas de concorrência, haja vista que os callbacks de post save
    devem ser desabilitados em alguns casos, por meio do contexto
    `avoid_circular_signals`.
"""
import os
import io
import logging
import base64
import threading
import contextlib
import datetime
from copy import deepcopy

from lxml import isoschematron, etree
from elasticsearch import Elasticsearch
from django.conf import settings
from django.db.models import Q
from django.db import IntegrityError

from scielomanager.celery import app
from . import models


logger = logging.getLogger(__name__)


ARTICLE_SAVE_MUTEX = threading.Lock()
BASIC_ARTICLE_META_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'basic_article_meta.sch')


# instâncias de isoschematron.Schematron não são thread-safe
ARTICLE_META_SCHEMATRON = isoschematron.Schematron(file=BASIC_ARTICLE_META_PATH)


def get_elasticsearch():
    """Fábrica de clientes do Elasticsearch.

    Essa função é um singleton.
    """
    if not hasattr(get_elasticsearch, 'client'):
        get_elasticsearch.client = Elasticsearch(settings.ELASTICSEARCH_NODES)

    return get_elasticsearch.client


def index_article(id, struct, **kwargs):
    """Indexa `struct` no índice de artigos do catman no Elasticsearch.
    """
    client = get_elasticsearch()
    result = client.index(
            index=settings.ES_ARTICLE_INDEX_NAME,
            doc_type=settings.ES_ARTICLE_DOC_TYPE,
            id=id, body=struct, **kwargs)

    return result


def _gen_es_struct_from_article(article):
    """Retorna `article` em estrutura de dados esperada pelo Elasticsearch.
    """
    paths = article.XPaths

    values_to_struct_mapping = [
        ['abbrev_journal_title', paths.ABBREV_JOURNAL_TITLE],
        ['epub', paths.ISSN_EPUB], ['ppub', paths.ISSN_PPUB],
        ['volume', paths.VOLUME], ['issue', paths.ISSUE],
        ['year', paths.YEAR], ['doi', paths.DOI],
        ['pid', paths.PID], ['head_subject', paths.HEAD_SUBJECT],
        ['article_type', paths.ARTICLE_TYPE],
    ]

    es_struct = {attr: article.get_value(expr)
                 for attr, expr in values_to_struct_mapping}

    article_as_octets = str(article.xml)
    base64_octets = base64.b64encode(article_as_octets)

    partial_struct = {
        'version': article.xml_version,
        'is_aop': article.is_aop,
        'b64_source': base64_octets,
        'source': article_as_octets,
    }

    es_struct.update(partial_struct)

    return es_struct


@contextlib.contextmanager
def avoid_circular_signals(mutex):
    """ Garante a execução de um bloco de código sem o disparo de signals.

    A finalidade deste gerenciador de contexto é de permitir que entidades
    de `models.Article` sejam modificadas e salvas dentro de tasks invocadas
    por signals de `post_save`, sem que esses signals sejam disparados novamente.
    I.e. evita loop de signals.
    """
    try:
        mutex.acquire()
        models.disconnect_article_post_save_signals()
        yield
        models.connect_article_post_save_signals()
    finally:
        mutex.release()


@app.task(ignore_result=True)
def submit_to_elasticsearch(article_pk):
    """ Submete a instância de `journalmanager.models.Article` para indexação
    do Elasticsearch.
    """
    try:
        article = models.Article.objects.get(pk=article_pk)
    except models.Article.DoesNotExist:
        logger.error('Cannot find Article with pk: %s. Skipping the submission to elasticsearch.', article_pk)
        return None

    struct = _gen_es_struct_from_article(article)
    result = index_article(article.aid, struct)

    logger.info('Elasticsearch indexing result for article "%s": %s.',
            article.domain_key, result)

    if result.get('_version') > 0:
        article.es_updated_at = datetime.datetime.now()
        article.es_is_dirty = False
        with avoid_circular_signals(ARTICLE_SAVE_MUTEX):
            article.save()


@app.task(ignore_result=True)
def link_article_to_journal(article_pk):
    """ Tenta associar o artigo ao seu periódico.
    """
    try:
        article = models.Article.nocacheobjects.get(pk=article_pk, journal=None)
    except models.Article.DoesNotExist:
        logger.info('Cannot find unlinked Article with pk: %s. Skipping the linking task.', article_pk)
        return None

    try:
        journal = models.Journal.objects.get(
                Q(print_issn=article.issn_ppub) | Q(eletronic_issn=article.issn_epub))
    except models.Journal.DoesNotExist:
        # Pode ser que os ISSNs do XML estejam invertidos...
        try:
            journal = models.Journal.objects.get(
                    Q(print_issn=article.issn_epub) | Q(eletronic_issn=article.issn_ppub))
        except models.Journal.DoesNotExist:
            logger.info('Cannot find parent Journal for Article with pk: %s. Skipping the linking task.', article_pk)
            return None

    article.journal = journal
    with avoid_circular_signals(ARTICLE_SAVE_MUTEX):
        article.save()

    logger.info('Article "%s" is now linked to journal "%s".',
            article.domain_key, journal.title)

    link_article_to_issue.delay(article_pk)


@app.task(ignore_result=True)
def link_article_to_issue(article_pk):
    """ Tenta associar o artigo ao seu número.
    """
    try:
        article = models.Article.objects.get(pk=article_pk, issue=None, is_aop=False)
    except models.Article.DoesNotExist:
        logger.info('Cannot find unlinked Article with pk: %s. Skipping the linking task.', article_pk)
        return None

    if article.journal is None:
        logger.info('Cannot link Article to issue without having a journal. Article pk: %s. Skipping the linking task.', article_pk)
    else:
        volume = article.get_value(article.XPaths.VOLUME)
        issue = article.get_value(article.XPaths.ISSUE)
        year = article.get_value(article.XPaths.YEAR)

        try:
            issue = article.journal.issue_set.get(
                    volume=volume, number=issue, publication_year=year)
        except models.Issue.DoesNotExist:
            logger.info('Cannot find Issue for Article with pk: %s. Skipping the linking task.', article_pk)
        else:
            article.issue = issue
            with avoid_circular_signals(ARTICLE_SAVE_MUTEX):
                article.save()

            logger.info('Article "%s" is now linked to issue "%s".',
                    article.domain_key, issue.label)

    return None


@app.task(ignore_result=True)
def process_orphan_articles():
    """ Tenta associar os artigos órfãos com periódicos e fascículos.
    """
    orphans = models.Article.objects.filter(issue=None)

    for orphan in orphans:
        if orphan.journal is None:
            link_article_to_journal.delay(orphan.pk)
        else:
            link_article_to_issue.delay(orphan.pk)


@app.task(ignore_result=True)
def process_dirty_articles():
    """ Task (periódica) que garanta a indexação dos artigos sujos.
    """
    dirties = models.Article.objects.filter(es_is_dirty=True)

    for dirty in dirties:
        submit_to_elasticsearch.delay(dirty.pk)


@app.task(throws=(IntegrityError, ValueError))
def create_article_from_string(xml_string):
    """ Cria uma instância de `journalmanager.models.Article`.

    Pode levantar `django.db.IntegrityError` no caso de artigos duplicados,
    TypeError no caso de argumento com tipo diferente de unicode ou
    ValueError no caso de artigos cujos elementos identificadores não estão
    presentes.

    :param xml_string: String de texto unicode.
    :return: aid (article-id) formado por uma string de 32 bytes.
    """
    if not isinstance(xml_string, unicode):
        raise TypeError('Only unicode strings are accepted')

    xml_bstring = xml_string.encode('utf-8')

    try:
        parsed_xml = etree.parse(io.BytesIO(xml_bstring))

    except etree.XMLSyntaxError as exc:
        raise ValueError(u"Syntax error: %s.", exc.message)

    metadata_sch = deepcopy(ARTICLE_META_SCHEMATRON)
    if not metadata_sch.validate(parsed_xml):
        logger.debug('Schematron validation error log: %s.', metadata_sch.error_log)
        raise ValueError('Missing identification elements')

    new_article = models.Article(xml=xml_bstring)
    with ARTICLE_SAVE_MUTEX:
        new_article.save_dirty()

    logger.info('New Article added with aid: %s.', new_article.aid)

    return new_article.aid

