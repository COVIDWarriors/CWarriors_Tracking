# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $

from django.utils.translation import ugettext_lazy as _

from django import forms
from .models import Technician

class loadBatch(forms.Form):
    batchid = forms.CharField(max_length=32,required=False,
                    label=_('Batch identifier (leave blank to generate)'))
    samples = forms.FileField(label=_('Samples file'),required=False)
    techid = forms.ModelChoiceField(queryset=Technician.objects.all(),
                                    label=_('Technician'),initial=0)
    procedure = forms.ModelChoiceField(queryset=Procedure.objects.all(),
                                       label=_('Procedure'),initial=0)
