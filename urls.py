# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: urls.py 44 2020-05-02 18:20:46Z root $

from django.conf.urls import url
from . import views
from .models import Rack

app_name = 'tracing'

racktypes = ''.join(['{0}'.format(t[0]) for t in Rack.TYPE])
urlpatterns = [
    url(r'^create/(?P<racktype>[{0}])$'.format(racktypes), views.fill, name='create'),
    url(r'^fill/(?P<rackid>\d+)$', views.fill, name='fill'),
    url(r'^move/(?P<rackid>\d+)/(?P<robotid>\d+)$', views.move, name='move'),
    url(r'^move/(?P<rackid>\d+)$', views.move, name='move'),
    url(r'^insert/(?P<rackid>\d+)$', views.insert, name='insert'),
    url(r'^show/(?P<rackid>\d+)$', views.show, name='show'),
    url(r'^sample/(?P<sampleid>\d+)$', views.viewsample, name='sample'),
    url(r'^movesample$', views.moveSample, name='movesample'),
    url(r'^start$', views.start, name='start'),
    url(r'^stop$', views.stop, name='stop'),
    url(r'^history$', views.history, name='history'),
    url(r'^upload$', views.upload, name='upload'),
    url(r'^$', views.index, name='inicio'),
]
