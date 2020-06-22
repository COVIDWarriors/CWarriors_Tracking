# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $
from django.shortcuts import render,get_object_or_404
from django.http import HttpResponseRedirect,JsonResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages

from .models import *
from .forms import loadBatch

import datetime

# Auxiliary methods
def place(tube,rack):
    """
    Places a tube in the next free position of a rack
    """

    # Find the next empty position
    rows = rack.listRows()
    if rack.isEmpty():
        row = 'A'
        col = 1
    else:
        t = rack.tube_set.order_by('col','row').last()
        if rack.ROWCOLS[rack.racktype][0] == t.row:
            # The column is full, move one right, we cannot reach here if the rack is full
            row = 'A'
            col = t.col+1
        else:
            row = rows[rows.index(t.row)+1]
            col = t.col
    tube.rack = rack
    tube.row = row
    tube.col = col
    tube.save()
    return True

def populate(rack):
    # It is easier to organise the tubes here than on the template
    # There should be no empty places between tubes, but better safe that sorry
    grid = []
    for r in rack.listRows():
        for c in rack.listCols():
            grid.append({'row': r , 'col': c[0], 'sample': ''})
    for t in rack.tube_set.all():
        g = [x for x in grid if x['col'] == t.col and x['row'] == t.row]
        if len(g) == 1:
          g[0]['sample'] = t.sample.code
          g[0]['finished'] = t.sample.finished

    return grid


# Create your views here.

def index(request):
    """
    Initial view to represent the robots state.
    """
    # Prepare the presentation of the robots for the template
    # It is easier to fill information here in a dicitionary,
    # than on the template
    astations = []
    astations = Robot.objects.filter(station='A')
    #for robot in Robot.objects.filter(station='A'):
    #    tray = {}
    #    for rack in robot.rack_set.all():
    #        tray[rack.position] = rack
    #    tray['robot'] = robot
    #    astations.append(tray)

    bstations = []
    bstations = Robot.objects.filter(station='B')
    #for robot in Robot.objects.filter(station='B'):
    #    tray = {}
    #    for rack in robot.rack_set.all():
    #        tray[rack.position] = rack
    #    tray['robot'] = robot
    #    bstations.append(tray)

    cstations = []
    cstations = Robot.objects.filter(station='C')
    #for robot in Robot.objects.filter(station='C'):
    #    tray = {}
    #    for rack in robot.rack_set.all():
    #        tray[rack.position] = rack
    #    tray['robot'] = robot
    #    cstations.append(tray)

    # Prepare the list of racks that are outside the robots
    forA = [r for r in Rack.objects.filter(robot=None,passed='') 
                    if not r.isEmpty() or r.racktype == r.DEEPWELL]
    # Only Deepwells for B and C
    forB = Rack.objects.filter(robot=None,passed='A',racktype=Rack.DEEPWELL)
    forC = Rack.objects.filter(robot=None,passed='AB',racktype=Rack.DEEPWELL)

    # Find robots with appropriate free positions
    freeA = [x for x in Robot.objects.filter(station='A') if x.libre()]
    freeB = [x for x in Robot.objects.filter(station='B') if x.libre()]
    freeC = [x for x in Robot.objects.filter(station='C') if x.libre()]

    return render(request,'robots.html',{'astations': astations,
                                         'bstations': bstations,
                                         'cstations': cstations,
                                         'racktypes': Rack.TYPE,
                                         'forA': forA, 'forB': forB, 'forC': forC,
                                         'freeA': freeA, 'freeB': freeB, 'freeC': freeC})


def move(request,rackid,robotid=None):
    """
    Moves a rack into or out of a robot
    """
    rack = get_object_or_404(Rack,id=rackid)
    log = Log()
    if not robotid:
        # It is going out of current robot
        robot = rack.robot
        rack.robot = None
        log.what = 'O'
        # Deepwells MUST leave station A first, they are always on tray 5
        if (robot.station == 'A' and not rack.racktype == rack.DEEPWELL
                                 and robot.rack_set.filter(position=5)):
            messages.error(request,_('Deepwell MUST be removed first'))
            return HttpResponseRedirect(reverse('tracing:inicio'))
        # Deepwells must leave station A with all samples in them if there is any
        if robot.station == 'A' and rack.racktype == rack.DEEPWELL and rack.isEmpty():
            for tray in [4,1,6,3]:
                r = robot.rack_set.filter(position=tray)
                if len(r) == 1:
                    for tube in r[0].tube_set.all().order_by('col','row'):
                        place(tube,rack)
        if robot.station == 'C':
            for tube in rack.tube_set.all():
                tube.sample.finished = True
                tube.sample.save()
        messages.success(request,_('{0} removed from {1}').format(rack,robot))
    else:
        robot = get_object_or_404(Robot,id=robotid)
        # Deepwells can only be placed at position 5
        if rack.racktype == rack.DEEPWELL:
            if len(robot.rack_set.filter(position=5)) == 1:
                messages.error(request,_('Tray 5 on {0} is occupied').format(robot))
                return HttpResponseRedirect(reverse('tracing:inicio'))
            rack.position = 5
        else:
            # Use first free position
            used = [x.position for x in robot.rack_set.all() if not x.position ==  5]
            empty = [x for x in [4,1,6,3] if x not in used]
            if len(empty) == 0:
                messages.error(request,_('No trays available on {0}').format(robot))
                return HttpResponseRedirect(reverse('tracing:inicio'))
            rack.position = empty[0]
        rack.robot = robot
        log.what = 'I'
        messages.success(request,
                _('{0} placed on tray {1} on {2}').format(rack,rack.position,robot))
    rack.save()
    log.robot = robot
    log.rack = rack
    log.save()

    return HttpResponseRedirect(reverse('tracing:inicio'))


def insert(request,rackid):
    """
    Inserts a sample in the next free well in a given rack.
    The algorithm works in column first mode, i.e.: A1,B1,C1,...F12,G12,H12
    """
    
    racks = Rack.objects.filter(pk=rackid)
    if not len(racks) == 1:
        response = JsonResponse({"error": _("Wrong Identifier")})
        response.status_code = 404
        return response
    # We have a single rack as expected
    rack = racks[0]
    if rack.isFull():
        response = JsonResponse({"error": _("Rack is full")})
        response.status_code = 404
        return response
    batchid = request.session.get('batch',0)
    if request.method == 'POST':
       identifier = request.POST.get('identifier',None)
    if not identifier:
        response = JsonResponse({"error": _("Wrong Identifier")})
        response.status_code = 404
        return response
    sample = Sample.objects.filter(batch__identifier=batchid,code=identifier)
    if not len(sample) == 1:
        response = JsonResponse({"error": _("Wrong Identifier")})
        response.status_code = 404
        return response
    if sample[0].tube_set.first():
        response = JsonResponse({"error": _("Sample {0} Added Already").format(identifier)})
        response.status_code = 404
        return response

    # Create a new tube and add the sample
    tube = Tube()
    tube.sample = sample[0] # We used filter, so, we have a QuerySet with one object
    # Place tube in the next free position
    place(tube,rack)
    tube.save()
    # If it is the first sample from a batch, we mark the start of processing
    if not sample[0].batch.started:
        sample[0].batch.started = datetime.datetime.now()
        sample[0].batch.save()

    return JsonResponse({'row': tube.row, 'col': tube.col, 'sampleid': sample[0].code})


def fill(request,rackid=None,racktype=None):
    """
    Creates an empty rack and presents a page to fill it.
    """
    # If method is GET, we need a new rack or want to display one
    if request.method == 'GET':
        if not rackid and not racktype:
            # Nothing, we do not know what to do, back to square one.
            # urls.py should prevent this
            return HttpResponseRedirect(reverse('tracing:inicio'))
        if racktype and not rackid:
            # We need a new empty rack
            rack = Rack()
            rack.racktype = racktype
            rack.save()
            return HttpResponseRedirect(reverse('tracing:fill',kwargs={'rackid': rack.id}))
        if rackid and not racktype:
            # We want a given rack to display and fill
            rack = get_object_or_404(Rack,id=rackid)
            batchid = request.session.get('batch',0)
            if batchid:
                batch = get_object_or_404(Batch,identifier=batchid)
            else:
                batch = None
    if rackid and request.method == 'POST':
        # POSTs set the Batch ID for the samples that will fill the racks
        batchid = request.POST.get('batchid',False)
        # We want a given rack to display and fill
        rack = get_object_or_404(Rack,id=rackid)
        if not batchid:
            messages.error(request,_('No batch identifier'))
        else:
            request.session['batch'] = batchid
            batch = get_object_or_404(Batch,identifier=batchid)

    # Fill the grid for presenting on the template
    grid = populate(rack)

    return render(request,'rack_fill.html',{'rack': rack, 'grid': grid, 'batch': batch})


def viewsample(request,sampleid):
    """
    Show sample information
    """
    sample = get_object_or_404(Sample,code=sampleid)
    return render(request,'sample.html',{'sample': sample })


def show(request,rackid):
    """
    Presents a grid with the samples in a rack.
    """
    rack = get_object_or_404(Rack,id=rackid)
    # Fill the grid for presenting on the template
    grid = populate(rack)
    return render(request,'rack.html',{'rack': rack, 'grid': grid })


def history(request):
    """
    Retrieves logging objects to present the history of a set of racks and samples.
    By default, it shows the activity of the current day.
    """
    batchid = False
    lastdate = Log.objects.last().createdOn.date()
    if request.method == 'GET':
       date = lastdate
    if request.method == 'POST':
        date = request.POST.get('date',lastdate)
        batchid = request.POST.get('batchid',False)
    logs = Log.objects.filter(createdOn__date=date)
    if batchid:
        batch = get_object_or_404(Batch,identifier=batchid)
        logs = logs.filter(rack__batch=batch)

    return render(request,'logs.html',{'logs': logs, 'date': date, 'batchid': batchid})


def upload(request):
    """
    Creates a sample batch from a CSV file (only the "code" field is used)
    First row should look like (ellipsys means other discarded columns):
    ...,code,... OR ...,"code",...
    Subsequent rows shoud look like:
    ...,sample-code,...
    """
    if request.method == 'GET':
        form = loadBatch()
        return render(request,'upload.html',{'form': form})
    if not request.method == 'POST':
      messages.error(_('Wrong method'))
      return HttpResponseRedirect(reverse('tracing:inicio'))

    form = loadBatch(request.POST, request.FILES)
    if not form.is_valid():
        return render(request,'upload.html',{'form': form})

    batch = Batch()
    if form.cleaned_data['batchid']:
        batch.identifier = form.cleaned_data['batchid']
    batch.technician = get_object_or_404(Technician,
                                         id=form.cleaned_data['techid'])
    batch.save()
    import csv,io
    samples = request.FILES['samples']
    samples.seek(0)
    for line in csv.DictReader(io.StringIO(samples.read().decode('utf-8'))):
        sample = Sample()
        sample.batch = batch
        sample.code = line['code']
        sample.save()
    messages.success(request,
                     _('Batch {0} with {1} samples uploaded successfully').format(
                       batch.identifier,len(batch.sample_set.all())))
    return HttpResponseRedirect(reverse('tracing:inicio'))

