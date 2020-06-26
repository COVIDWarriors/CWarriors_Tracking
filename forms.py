# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $

from django.utils.translation import ugettext_lazy as _

from django import forms
from .models import Technician

TECHS=[(t.id,t.name) for t in Technician.objects.all()]

class loadBatch(forms.Form):
    batchid = forms.CharField(max_length=32,required=False,
                    label=_('Batch identifier (leave blank to generate)'))
    samples = forms.FileField(label=_('Samples file'),required=False)
    techid = forms.IntegerField(label=_('Technician'),
                                widget=forms.Select(choices=TECHS))
