# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $

from django.utils.translation import ugettext_lazy as _

from django import forms
from .models import Technician

# I know this is crap, I'll improve on a future iteration
#TECHS=[(t.id,t.name) for t in Technician.objects.all()]
# Uncomment previous line once database has been created, and remove this and next line
TECHS = [(0,'See forms.py to configure')]

class loadBatch(forms.Form):
    batchid = forms.CharField(max_length=32,required=False,
                    label=_('Batch identifier (leave blank to generate)'))
    samples = forms.FileField(label=_('Samples file'),required=False)
    techid = forms.IntegerField(label=_('Technician'),
                                widget=forms.Select(choices=TECHS))
