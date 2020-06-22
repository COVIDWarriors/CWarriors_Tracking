# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $
from django.contrib import admin

# Register your models here.
from .models import *

class LogInline(admin.TabularInline):
    model = Log
    extra = 1
    fields = ['createdOn', 'rack', 'what']
    readonly_fields = ('createdOn', 'rack', 'what',)
    hidden_fields = ('modifiedOn','identifier',)


class RobotAdmin(admin.ModelAdmin):
    model = Robot
    inlines = [LogInline]
    #fields = ['identifier','station','ip']
    list_display = ['id','identifier','station','order','ip']
    list_editable = ['station','order','ip']
    list_filter = ['station']
    #list_identifier = ['station','ip']
    list_display_links = ['id','identifier']
    #readonly_fields = ['identifier']
    fieldsets = (
        (None, {'fields': ('identifier','station','order','ip'),},),
    )


admin.site.register(Robot,RobotAdmin)


class TechnicianAdmin(admin.ModelAdmin):
    model = Technician
    list_display = ['id','identifier','name']
    list_display_links = ['id','identifier']
    fieldsets = (
        (None, {'fields': ('name',),},),
    )


admin.site.register(Technician,TechnicianAdmin)


class SampleAdmin(admin.TabularInline):
    model = Sample
    extra = 1
    hidden_fields = ('createdOn','modifiedOn','identifier',)


class BatchAdmin(admin.ModelAdmin):
    model = Batch
    inlines = [SampleAdmin]
    list_display = ['id','identifier','technician','started','finished']
    list_filter = ['technician','started','finished']
    list_editable = ['technician']
    list_display_links = ['id','identifier']
    fieldsets = (
        (None, {'fields': ('technician','started','finished',),},),
    )

admin.site.register(Batch,BatchAdmin)


class TubeAdmin(admin.TabularInline):
    model = Tube
    extra = 1
    hidden_fields = ('createdOn','modifiedOn',)


class RackAdmin(admin.ModelAdmin):
    model = Rack
    inlines = [TubeAdmin]
    list_display = ['id','identifier','racktype','numSamples',
                    'robot','position','createdOn']
    list_filter = ['racktype','robot','position']
    list_editable = ['racktype','robot']
    list_display_links = ['id','identifier']
    fieldsets = (
        (None, {'fields': ('racktype','robot','position'),},),
    )


admin.site.register(Rack,RackAdmin)


class LogAdmin(admin.ModelAdmin):
    model = Log
    list_display = ['id','createdOn','rack','what','robot']
    list_filter = ['createdOn','rack','robot','what']
    list_display_links = ['id']
    fieldsets = (
        (None, {'fields': ('rack','what','robot'),},),
    )


admin.site.register(Log,LogAdmin)


