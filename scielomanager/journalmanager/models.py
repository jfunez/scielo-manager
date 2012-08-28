# -*- encoding: utf-8 -*-
import urllib
import hashlib

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext as __
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.defaultfilters import slugify

import caching.base

import choices
import helptexts

User.__bases__ = (caching.base.CachingMixin, models.Model)
User.add_to_class('cached_objects', caching.base.CachingManager())


def get_user_collections(user_id):
    """
    Return all the collections of a given user, The returned collections are the collections where the
    user could have access by the collections bar.
    """
    user_collections = User.cached_objects.get(pk=user_id).usercollections_set.all().order_by(
        'collection__name')

    return user_collections


def get_default_user_collections(user_id):
    """
    Return the collection that the user choose as default/active collection.
    """
    user_collections = User.cached_objects.get(pk=user_id).usercollections_set.filter(
        is_default=True).order_by('collection__name')

    if len(user_collections) == 0:
        try:
            user_collections = User.cached_objects.get(pk=user_id).usercollections_set.all().order_by(
                'collection__name')[0]
            user_collections.is_default = True
            user_collections.save()
            return [user_collections]
        except IndexError:
            return None

    return user_collections


class AppCustomManager(caching.base.CachingManager):
    """
    Domain specific model managers.
    """

    def available(self, is_available=True):
        """
        Filter the queryset based on its availability.
        """
        data_queryset = self.get_query_set()

        if not isinstance(is_available, bool):
            try:
                if int(is_available) == 0:
                    is_available = False
                else:
                    is_available = True
            except (ValueError, TypeError):
                is_available = True

        data_queryset = data_queryset.filter(is_trashed=not is_available)

        return data_queryset


class JournalCustomManager(AppCustomManager):

    def all_by_user(self, user, is_available=True, pub_status=None):
        user_collections = get_default_user_collections(user.pk)
        objects_all = self.available(is_available).filter(
            collections__in=[uc.collection for uc in user_collections]).distinct()

        if pub_status:
            if pub_status in [stat[0] for stat in choices.JOURNAL_PUBLICATION_STATUS]:
                objects_all = objects_all.filter(pub_status=pub_status)

        return objects_all

    def recents_by_user(self, user):
        """
        Retrieve the recently modified objects related to the given user.
        """
        user_collections = get_default_user_collections(user.pk)
        recents = self.filter(
            collections__in=[uc.collection for uc in user_collections]).distinct().order_by('-updated')[:5]

        return recents


class SectionCustomManager(AppCustomManager):

    def all_by_user(self, user, is_available=True):
        user_collections = get_default_user_collections(user.pk)
        objects_all = self.available(is_available).filter(
            journal__collections__in=[uc.collection for uc in user_collections]).distinct()
        return objects_all


class IssueCustomManager(AppCustomManager):

    def all_by_user(self, user, is_available=True):
        user_collections = get_default_user_collections(user.pk)
        objects_all = self.available(is_available).filter(
            collections__in=[uc.collection for uc in user_collections]).distinct()
        return objects_all


class InstitutionCustomManager(AppCustomManager):
    """
    Add capabilities to Institution subclasses to retrieve querysets
    based on user's collections.
    """
    def all_by_user(self, user, is_available=True):
        user_collections = get_default_user_collections(user.pk)
        objects_all = self.available(is_available).filter(
            collections__in=[uc.collection for uc in user_collections]).distinct()
        return objects_all


class Language(caching.base.CachingMixin, models.Model):
    """
    Represents ISO 639-1 Language Code and its language name in English. Django
    automaticaly translates language names, if you write them right.

    http://en.wikipedia.org/wiki/ISO_639-1_language_matrix
    """
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    iso_code = models.CharField(_('ISO 639-1 Language Code'), max_length=2)
    name = models.CharField(_('Language Name (in English)'), max_length=64)

    def __unicode__(self):
        return __(self.name)

    class Meta:
        ordering = ['name']


class UserProfile(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    user = models.OneToOneField(User)
    email = models.EmailField(_('E-mail'), blank=False, unique=True, null=False)

    @property
    def gravatar_id(self):
        return hashlib.md5(self.email.lower().strip()).hexdigest()

    @property
    def avatar_url(self):
        params = urllib.urlencode({'s': 25, 'd': 'mm'})
        return '{0}/avatar/{1}?{2}'.format(getattr(settings, 'GRAVATAR_BASE_URL',
            'https://secure.gravatar.com'), self.gravatar_id, params)

    def save(self, force_insert=False, force_update=False):
        self.user.email = self.email
        self.user.save()
        return super(UserProfile, self).save(force_insert, force_update)


class Collection(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    collection = models.ManyToManyField(User, related_name='user_collection',
        through='UserCollections', null=True, blank=True, )
    name = models.CharField(_('Collection Name'), max_length=128, db_index=True, )
    name_slug = models.SlugField(unique=True, db_index=True, blank=True, null=True)
    url = models.URLField(_('Instance URL'), )
    logo = models.ImageField(_('Logo'), upload_to='img/collections_logos', null=True, blank=True, )
    acronym = models.CharField(_('Sigla'), max_length=16, db_index=True, blank=True, )
    country = models.CharField(_('Country'), max_length=32,)
    state = models.CharField(_('State'), max_length=32, null=False, blank=True,)
    city = models.CharField(_('City'), max_length=32, null=False, blank=True,)
    address = models.TextField(_('Address'),)
    address_number = models.CharField(_('Number'), max_length=8,)
    address_complement = models.CharField(_('Complement'), max_length=128, null=False, blank=True,)
    zip_code = models.CharField(_('Zip Code'), max_length=16, null=True, blank=True, )
    phone = models.CharField(_('Phone Number'), max_length=16, null=False, blank=True, )
    fax = models.CharField(_('Fax Number'), max_length=16, null=False, blank=True, )
    email = models.EmailField(_('Email'), )

    def __unicode__(self):
        return unicode(self.name)

    class Meta:
        ordering = ['name']
        permissions = (("list_collection", "Can list Collections"),)

    def save(self, *args, **kwargs):
        self.name_slug = slugify(self.name)
        super(Collection, self).save(*args, **kwargs)


class UserCollections(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    user = models.ForeignKey(User)
    collection = models.ForeignKey(Collection)
    is_default = models.BooleanField(_('Is default'), default=False, null=False, blank=False)
    is_manager = models.BooleanField(_('Is manager of the collection?'), default=False, null=False,
        blank=False)

    class Meta:
        unique_together = ("user", "collection", )


class Institution(caching.base.CachingMixin, models.Model):

    #Custom manager
    objects = AppCustomManager()
    nocacheobjects = models.Manager()

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(_('Institution Name'), max_length=256, db_index=True)
    complement = models.TextField(_('Institution Complements'), blank=True, default="")
    acronym = models.CharField(_('Sigla'), max_length=16, db_index=True, blank=True)
    country = models.CharField(_('Country'), max_length=32)
    state = models.CharField(_('State'), max_length=32, null=False, blank=True)
    city = models.CharField(_('City'), max_length=32, null=False, blank=True)
    address = models.TextField(_('Address'))
    address_number = models.CharField(_('Number'), max_length=8)
    address_complement = models.CharField(_('Address Complement'), max_length=128, null=False, blank=True)
    zip_code = models.CharField(_('Zip Code'), max_length=16, null=True, blank=True)
    phone = models.CharField(_('Phone Number'), max_length=16, null=False, blank=True)
    fax = models.CharField(_('Fax Number'), max_length=16, null=False, blank=True)
    cel = models.CharField(_('Cel Number'), max_length=16, null=False, blank=True)
    email = models.EmailField(_('E-mail'))
    is_trashed = models.BooleanField(_('Is trashed?'), default=False, db_index=True)

    def __unicode__(self):
        return u'%s' % (self.name)

    class Meta:
        ordering = ['name']


class Sponsor(Institution):
    objects = InstitutionCustomManager()
    nocacheobjects = models.Manager()

    collections = models.ManyToManyField(Collection)

    class Meta:
        permissions = (("list_sponsor", "Can list Sponsors"),)

class Journal(caching.base.CachingMixin, models.Model):

    #Custom manager
    objects = JournalCustomManager()
    nocacheobjects = models.Manager()

    #Relation fields
    creator = models.ForeignKey(User, related_name='enjoy_creator', editable=False)
    sponsor = models.ManyToManyField('Sponsor', related_name='journal_sponsor', null=True, blank=True)
    previous_title = models.ForeignKey('Journal', related_name='prev_title', null=True, blank=True)
    use_license = models.ForeignKey('UseLicense')
    collections = models.ManyToManyField('Collection')
    languages = models.ManyToManyField('Language',)
    national_code = models.CharField(_('National Code'), max_length=16, null=True, blank=True)
    abstract_keyword_languages = models.ManyToManyField('Language', related_name="abstract_keyword_languages", )

    #Fields
    title = models.CharField(_('Journal Title'), max_length=256, db_index=True)
    title_iso = models.CharField(_('ISO abbreviated title'), max_length=256, db_index=True)
    short_title = models.CharField(_('Short Title'), max_length=256, db_index=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    acronym = models.CharField(_('Acronym'), max_length=16, blank=False)
    scielo_issn = models.CharField(_('The ISSN used to build the Journal PID.'), max_length=16,
        choices=sorted(choices.SCIELO_ISSN, key=lambda SCIELO_ISSN: SCIELO_ISSN[1]))
    print_issn = models.CharField(_('Print ISSN'), max_length=9)
    eletronic_issn = models.CharField(_('Eletronic ISSN'), max_length=9)
    subject_descriptors = models.CharField(_('Subject / Descriptors'), max_length=512,
        help_text='')
    init_year = models.CharField(_('Initial Date'), max_length=16)
    init_vol = models.CharField(_('Initial Volume'), max_length=16)
    init_num = models.CharField(_('Initial Number'), max_length=16)
    final_year = models.CharField(_('Final Date'), max_length=16, null=True, blank=True)
    final_vol = models.CharField(_('Final Volume'), max_length=16, null=False, blank=True)
    final_num = models.CharField(_('Final Number'), max_length=16, null=False, blank=True)
    frequency = models.CharField(_('Frequency'), max_length=16,
        choices=sorted(choices.FREQUENCY, key=lambda FREQUENCY: FREQUENCY[1]))
    pub_status = models.CharField(_('Publication Status'), max_length=16, blank=True, null=True, default="inprogress",
        choices=choices.PUBLICATION_STATUS)
    pub_status_reason = models.TextField(_('Why the journal status will change?'), blank=True, default="",)
    pub_status_changed_by = models.ForeignKey(User, related_name='pub_status_changed_by', editable=False)
    editorial_standard = models.CharField(_('Editorial Standard'), max_length=64,
        choices=sorted(choices.STANDARD, key=lambda STANDARD: STANDARD[1]))
    ctrl_vocabulary = models.CharField(_('Controlled Vocabulary'), max_length=64,
        choices=choices.CTRL_VOCABULARY)
    pub_level = models.CharField(_('Publication Level'), max_length=64,
        choices=sorted(choices.PUBLICATION_LEVEL, key=lambda PUBLICATION_LEVEL: PUBLICATION_LEVEL[1]))
    secs_code = models.CharField(_('SECS Code'), max_length=64, null=False, blank=True)
    copyrighter = models.CharField(_('Copyrighter'), max_length=254)
    url_online_submission = models.CharField(_('URL of online submission'), max_length=64, null=True, blank=True)
    url_journal = models.CharField(_('URL of the journal'), max_length=64, null=True, blank=True)
    notes = models.TextField(_('Notes'), max_length=254, null=True, blank=True)
    index_coverage = models.TextField(_('Index Coverage'), null=True, blank=True)
    cover = models.ImageField(_('Journal Cover'), upload_to='img/journal_cover/', null=True, blank=True)
    logo = models.ImageField(_('Journal Logomarca'), upload_to='img/journals_logos', null=True, blank=True)
    is_trashed = models.BooleanField(_('Is trashed?'), default=False, db_index=True)
    other_previous_title = models.CharField(_('Other Previous Title'), max_length=255, blank=True)
    editor_address = models.TextField(_('Address'), blank=False,)
    editor_email = models.EmailField(_('E-mail'), blank=False,)
    publisher_name = models.CharField(_('Publisher Name'), max_length=256, blank=False,)
    publisher_country = models.CharField(_('Publisher Country'), max_length=64, blank=False,)
    publisher_state = models.CharField(_('Publisher State'), max_length=64, blank=False,)
    publication_city = models.CharField(_('Publication City'), max_length=64, blank=False,)

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ['title']
        permissions = (("list_journal", "Can list Journals"),)


class JournalPublicationEvents(caching.base.CachingMixin, models.Model):
    """
    Records the status changes for a given Journal.

    Known status:
    * Current
    * Deceased
    * Suspended
    * In progress
    """
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()

    journal = models.ForeignKey(Journal, editable=False, related_name='status_history')
    status = models.CharField(_('Journal Status'), max_length=16,)
    reason = models.TextField(_('Reason'), blank=True, default="",)
    created_at = models.DateTimeField(_('Changed at'), auto_now_add=True)
    changed_by = models.ForeignKey(User, editable=False)

    def __unicode__(self):
        return self.status

    class Meta:
        verbose_name = 'journal publication event'
        verbose_name_plural = 'Journal Publication Events'
        ordering = ['created_at']
        permissions = (("list_publication_events", "Can list Publication Events"),)


class JournalStudyArea(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    journal = models.ForeignKey(Journal, related_name='study_areas')
    study_area = models.CharField(_('Study Area'), max_length=256,
        choices=sorted(choices.SUBJECTS, key=lambda SUBJECTS: SUBJECTS[1]))


class JournalTitle(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    journal = models.ForeignKey(Journal, related_name='other_titles')
    title = models.CharField(_('Title'), null=False, max_length=128)
    category = models.CharField(_('Title Category'), null=False, max_length=128, choices=sorted(choices.TITLE_CATEGORY, key=lambda TITLE_CATEGORY: TITLE_CATEGORY[1]))


class JournalMission(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    journal = models.ForeignKey(Journal, related_name='missions')
    description = models.TextField(_('Mission'))
    language = models.ForeignKey('Language', blank=False, null=True)


class UseLicense(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()

    license_code = models.CharField(_('License Code'), unique=True, null=False, blank=False, max_length=64)
    reference_url = models.URLField(_('License Reference URL'), null=True, blank=True)
    disclaimer = models.TextField(_('Disclaimer'), null=True, blank=True, max_length=512)

    def __unicode__(self):
        return self.license_code

    class Meta:
        ordering = ['license_code']


class TranslatedData(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    translation = models.CharField(_('Translation'), null=True, blank=True, max_length=512)
    language = models.CharField(_('Language'), choices=sorted(choices.LANGUAGE, key=lambda LANGUAGE: LANGUAGE[1]), null=False, blank=False, max_length=32)
    model = models.CharField(_('Model'), null=False, blank=False, max_length=32)
    field = models.CharField(_('Field'), null=False, blank=False, max_length=32)

    def __unicode__(self):
        return self.translation if self.translation is not None else 'Missing trans: {0}.{1}'.format(self.model, self.field)


class SectionTitle(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()

    section = models.ForeignKey('Section', related_name='titles')
    title = models.CharField(_('Title'), max_length=256, null=False)
    language = models.ForeignKey('Language')

    class Meta:
        ordering = ['title']


class Section(caching.base.CachingMixin, models.Model):
    #Custom manager
    objects = SectionCustomManager()
    nocacheobjects = models.Manager()

    journal = models.ForeignKey(Journal)

    code = models.CharField(_('Code'), null=True, blank=True, max_length=16)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_trashed = models.BooleanField(_('Is trashed?'), default=False, db_index=True)

    def __unicode__(self):
        return ' / '.join([sec_title.title for sec_title in self.titles.all().order_by('language')])

    class Meta:
        permissions = (("list_section", "Can list Sections"),)


class Issue(caching.base.CachingMixin, models.Model):

    #Custom manager
    objects = IssueCustomManager()
    nocacheobjects = models.Manager()

    section = models.ManyToManyField(Section, blank=True)
    journal = models.ForeignKey(Journal)
    volume = models.CharField(_('Volume'), max_length=16)
    number = models.CharField(_('Number'), max_length=16)
    suppl_volume = models.CharField(_('Volume Supplement'), null=True, blank=True, max_length=16)
    suppl_number = models.CharField(_('Number Supplement'), null=True, blank=True, max_length=16)
    is_press_release = models.BooleanField(_('Is Press Release?'), default=False, null=False, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    publication_start_month = models.IntegerField(_('Start Month'), choices=choices.MONTHS)
    publication_end_month = models.IntegerField(_('End Month'), choices=choices.MONTHS)
    publication_year = models.IntegerField(_('Year'))
    is_marked_up = models.BooleanField(_('Is Marked Up?'), default=False, null=False, blank=True)
    use_license = models.ForeignKey(UseLicense, null=True)
    total_documents = models.IntegerField(_('Total of Documents'), default=0)
    ctrl_vocabulary = models.CharField(_('Controlled Vocabulary'), max_length=64,
        choices=sorted(choices.CTRL_VOCABULARY, key=lambda CTRL_VOCABULARY: CTRL_VOCABULARY[1]), null=False, blank=True)
    editorial_standard = models.CharField(_('Editorial Standard'), max_length=64,
        choices=sorted(choices.STANDARD, key=lambda STANDARD: STANDARD[1]))
    cover = models.ImageField(_('Issue Cover'), upload_to='img/issue_cover/', null=True, blank=True)
    is_trashed = models.BooleanField(_('Is trashed?'), default=False, db_index=True)
    label = models.CharField(db_index=True, blank=True, null=True, max_length=64)

    @property
    def identification(self):
        suppl_volume = _('suppl.') + self.suppl_volume if self.suppl_volume else ''
        suppl_number = _('suppl.') + self.suppl_number if self.suppl_number else ''

        return "{0} {1} {2}".format(self.number, suppl_volume, suppl_number).strip().replace('spe', 'special').replace('ahead', 'ahead of print')

    def __unicode__(self):
        return "{0} ({1})".format(self.volume, self.identification).replace('()', '')

    @property
    def publication_date(self):
        return '{0} / {1} - {2}'.format(self.publication_start_month,
            self.publication_end_month, self.publication_year)

    def save(self, *args, **kwargs):
        self.label = unicode(self)
        super(Issue, self).save(*args, **kwargs)

    class Meta:
        permissions = (("list_issue", "Can list Issues"),)


class IssueTitle(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()
    issue = models.ForeignKey(Issue)
    language = models.ForeignKey('Language', blank=True, null=True)
    title = models.CharField(_('Title'), max_length=128, null=True, blank=True)


class Supplement(Issue):
    suppl_label = models.CharField(_('Supplement Label'), null=True, blank=True, max_length=256)


class PendedForm(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()

    view_name = models.CharField(max_length=128)
    form_hash = models.CharField(max_length=32)
    user = models.ForeignKey(User, related_name='pending_forms')
    created_at = models.DateTimeField(auto_now=True)


class PendedValue(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()
    nocacheobjects = models.Manager()

    form = models.ForeignKey(PendedForm, related_name='data')
    name = models.CharField(max_length=255)
    value = models.TextField()

####
# Pre and Post save to handle `Journal.pub_status` data modification.
####


@receiver(pre_save, sender=Journal, dispatch_uid='journalmanager.models.journal_pub_status_pre_save')
def journal_pub_status_pre_save(sender, **kwargs):
    """
    Fetch the `pub_status` value from the db before the data is modified.
    """
    try:
        kwargs['instance']._pub_status = Journal.nocacheobjects.get(pk=kwargs['instance'].pk).pub_status
    except Journal.DoesNotExist:
        return None


@receiver(post_save, sender=Journal, dispatch_uid='journalmanager.models.journal_pub_status_post_save')
def journal_pub_status_post_save(sender, instance, created, **kwargs):
    """
    Check if the `pub_status` value is new or has been modified.
    """
    if getattr(instance, '_pub_status', None) and instance.pub_status == instance._pub_status:
        return None

    JournalPublicationEvents.objects.create(journal=instance,
        status=instance.pub_status, changed_by=instance.pub_status_changed_by, reason=instance.pub_status_reason)
