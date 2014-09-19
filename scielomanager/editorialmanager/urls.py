#coding: utf-8
from django.conf.urls.defaults import *

from . import views

urlpatterns = patterns('',
    url(r'^$', views.index, name="editorial.index"),

    # Journal related urls
    url(r'^journal/detail/(?P<journal_id>\d+)/$', views.journal_detail, name="editorial.journal.detail"),
    url(r'^journal/(?P<journal_id>\d+)/edit/$', views.edit_journal, name="editorial.journal.edit"),

    # Editorial Manager
    url(r'^board/(?P<journal_id>\d+)/$', views.board, name="editorial.board"),
    url(r'^board/(?P<journal_id>\d+)/members/(?P<issue_id>\d+)/add/$', views.add_board_member, name="editorial.board.add"),
    url(r'^board/(?P<journal_id>\d+)/members/(?P<member_id>\d+)/edit/$', views.edit_board_member, name="editorial.board.edit"),
    url(r'^board/(?P<journal_id>\d+)/members/(?P<member_id>\d+)/delete/$', views.delete_board_member, name="editorial.board.delete"),
)