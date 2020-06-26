# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $
from django.shortcuts import render,get_object_or_404
from django.http import HttpResponseRedirect,JsonResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from .models import *
from .forms import loadBatch

import datetime

# Auxiliary methods
def place(tube,rack,position=None):
    """
    Places a tube in the next free position of a rack
    """

    if not position == None:
        # We are placing he tube at a given position
        tube.rack = rack
        tube.row = position[0]
        tube.col = position[1]
        tube.save()
        return True

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
    # No refresh until processing starts on a connected robot
    refresh = False
    if request.session.get('tracing_atwork',False):
        refresh = settings.TRACING_REFRESH

    # Prepare the presentation of the robots for the template
    astations = Robot.objects.filter(station='A')
    bstations = Robot.objects.filter(station='B')
    cstations = Robot.objects.filter(station='C')
    for robot in astations | bstations | cstations:
        if (robot.connected and 
                            len(robot.rack_set.all()) == 0 and
                            not robot.state == 'E'):
            robot.state = 'E'
            robot.save()
        if (robot.connected and 
                            len(robot.rack_set.all()) >= 2 and
                            not robot.state in 'IPF'):
            robot.state = 'I'
            robot.save()

    # Prepare the list of racks that are outside the robots
    forA = [r for r in Rack.objects.filter(robot=None,passed='') 
                    if not r.isEmpty() or r.racktype == r.DEEPWELL]
    # Only Deepwells for B and C
    forB = Rack.objects.filter(robot=None,passed='A',racktype=Rack.DEEPWELL)
    forB = forB | Rack.objects.filter(robot=None,passed='',racktype=Rack.EP)
    forC = Rack.objects.filter(robot=None,passed='B',racktype=Rack.EP)
    forC = forC | Rack.objects.filter(robot=None,passed='',racktype=Rack.PCR)

    # Find robots with appropriate free positions
    freeA = [x for x in Robot.objects.filter(station='A') if x.libre()]
    freeB = [x for x in Robot.objects.filter(station='B') if x.libre()]
    freeC = [x for x in Robot.objects.filter(station='C') if x.libre()]

    return render(request,'tracing/robots.html',{'astations': astations,
                                                 'bstations': bstations,
                                                 'cstations': cstations,
                                                 'racktypes': Rack.TYPE,
                                                 'refresh': refresh,
                                                 'forA': forA, 'forB': forB,
                                                 'forC': forC, 'freeA': freeA,
                                                 'freeB': freeB, 'freeC': freeC})


def move(request,rackid,robotid=None):
    """
    Moves a rack into or out of a robot
    """
    rack = get_object_or_404(Rack,id=rackid)
    log = Log()
    if not robotid:
        # It is going out of current robot
        robot = rack.robot
        # Behaviour for station A
        if robot.station == 'A':
            # Deepwells MUST leave station A first, they are always on tray 5
            if (not rack.racktype == rack.DEEPWELL
                and robot.rack_set.filter(position=5)):
                messages.error(request,_('Deepwell MUST be removed first'))
                return HttpResponseRedirect(reverse('tracing:inicio'))
            # Deepwells must leave station A with all samples in them
            # if there is any
            if (rack.racktype == rack.DEEPWELL and rack.isEmpty()):
                for tray in [4,1,6,3]:
                    r = robot.rack_set.filter(position=tray)
                    if len(r) == 1:
                        for tube in r[0].tube_set.all().order_by('col','row'):
                           place(tube,rack)
        # Behaviour for station B
        if robot.station == 'B':
            # Regardless of the rack leaving the robot first,
            # samples have to leave station B on the EP rack
            # We save database hits ...
            if rack.racktype == rack.DEEPWELL:
                source = [rack]
                destination = Rack.objects.filter(robot=robot,position=1)
            if rack.racktype == rack.EP:
                destination = [rack]
                source = Rack.objects.filter(robot=robot,position=4)
            # Both racks available, move sample from source to destination
            if source and destination:
                if len(source) == 1 and len(destination) == 1:
                    for tube in source[0].tube_set.all().order_by('col','row'):
                        place(tube,destination[0])
                else:
                    messages.error(request,_('Unexpeted error while moving'))
                    return HttpResponseRedirect(reverse('tracing:inicio'))
        # Behaviour for station C
        if robot.station == 'C':
            # Regardless of the rack leaving the robot first,
            # samples have to leave station C on the PCR rack
            # We save database hits ...
            if rack.racktype == rack.EP:
                source = [rack]
                destination = Rack.objects.filter(robot=robot,position=1)
            if rack.racktype == rack.PCR:
                destination = [rack]
                source = Rack.objects.filter(robot=robot,position=4)
            # Both racks available, move sample from source to destination
            if source and destination:
                if len(source) == 1 and len(destination) == 1:
                    for tube in source[0].tube_set.all().order_by('col','row'):
                        place(tube,destination[0])
                        tube.sample.finished = True
                        tube.sample.save()
                else:
                    messages.error(request,_('Unexpeted error while moving'))
                    return HttpResponseRedirect(reverse('tracing:inicio'))
        # Common behaviour for outgoing racks
        messages.success(request,_('{0} removed from {1}').format(rack,robot))
        rack.robot = None
        rack.save()
        log.what = 'O'
    else:
        # Behaviour for racks entering a robot
        robot = get_object_or_404(Robot,id=robotid)
        # Behaviour for station A
        if robot.station == 'A':
            # Deepwells can only be placed at position 5
            if rack.racktype == rack.DEEPWELL:
                if len(robot.rack_set.filter(position=5)) == 1:
                    messages.error(request,
                                   _('Tray 5 on {0} is occupied').format(robot))
                    return HttpResponseRedirect(reverse('tracing:inicio'))
                rack.position = 5
            else:
                # Use first free position
                used = [x.position for x in robot.rack_set.all()
                        if not x.position ==  5]
                empty = [x for x in [4,1,6,3] if x not in used]
                if len(empty) == 0:
                    messages.error(request,
                                   _('No trays available on {0}').format(robot))
                    return HttpResponseRedirect(reverse('tracing:inicio'))
                rack.position = empty[0]
        # Behaviour for station B
        if robot.station == 'B':
            # Deep wells onto tray 4
            if rack.racktype == rack.DEEPWELL:
                if len(robot.rack_set.filter(position=4)) == 1:
                    messages.error(request,
                                   _('Tray 4 on {0} is occupied').format(robot))
                    return HttpResponseRedirect(reverse('tracing:inicio'))
                rack.position = 4
            # Extraction Plate onto tray 1
            if rack.racktype == rack.EP:
                if len(robot.rack_set.filter(position=1)) == 1:
                    messages.error(request,
                                   _('Tray 1 on {0} is occupied').format(robot))
                    return HttpResponseRedirect(reverse('tracing:inicio'))
                rack.position = 1
        # Behaviour for station C
        if robot.station == 'C':
            # Extraction Plate onto tray 4
            if rack.racktype == rack.EP:
                if len(robot.rack_set.filter(position=4)) == 1:
                    messages.error(request,
                                   _('Tray 4 on {0} is occupied').format(robot))
                    return HttpResponseRedirect(reverse('tracing:inicio'))
                rack.position = 4
            # PCR Plate onto tray 1
            if rack.racktype == rack.PCR:
                if len(robot.rack_set.filter(position=1)) == 1:
                    messages.error(request,
                                   _('Tray 1 on {0} is occupied').format(robot))
                    return HttpResponseRedirect(reverse('tracing:inicio'))
                rack.position = 1
        # Common behaviour for IN
        rack.robot = robot
        log.what = 'I'
        messages.success(request,
                _('{0} placed on tray {1} on {2}').format(rack,rack.position,robot))
    # Common behaviour for IN and OUT
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
    if not batchid:
        response = JsonResponse({"error": _("No Batch selected")})
        response.status_code = 404
        return response
    if not identifier:
        response = JsonResponse({"error": _("Wrong Identifier")})
        response.status_code = 404
        return response
    batch = get_object_or_404(Batch,identifier=batchid)
    sample = Sample.objects.filter(batch=batch,code=identifier)
    if batch.preloaded and not len(sample) == 1:
        return JsonResponse({"error":
                             _("Wrong Sample Code {0}:{1}").format(batchid,
                                                                  identifier)},
                            status = 404)
    if len(sample) and sample[0].tube_set.first():
        return JsonResponse({"error":
                             _("Sample {0} Added Already").format(identifier)},
                             status = 404)
    # If we do not have a sample yet, we do not have a pre-loaded batch
    if not batch.preloaded and len(sample) == 0:
        sample = [Sample()]
        sample[0].code = identifier
        sample[0].batch = batch
        sample[0].save()

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

    return JsonResponse({'row': tube.row, 'col': tube.col,
                         'sampleid': sample[0].code})


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
            nextpage = reverse('tracing:fill',kwargs={'rackid': rack.id})
            if int(racktype) in [rack.DEEPWELL, rack.EP, rack.PCR]:
                # "Output" racks start life empty, no need to fill them
                nextpage = reverse('tracing:inicio')
            return HttpResponseRedirect(nextpage)
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

    return render(request,'tracing/rack_fill.html',
                  {'rack': rack, 'grid': grid, 'batch': batch})


def viewsample(request,sampleid):
    """
    Show sample information
    """
    sample = get_object_or_404(Sample,code=sampleid)
    return render(request,'tracing/sample.html',{'sample': sample })


def show(request,rackid):
    """
    Presents a grid with the samples in a rack.
    """
    rack = get_object_or_404(Rack,id=rackid)
    # Fill the grid for presenting on the template
    grid = populate(rack)
    return render(request,'tracing/rack.html',{'rack': rack, 'grid': grid })


def history(request):
    """
    Retrieves logging objects to present the history of a set of racks and samples.
    By default, it shows the activity of the current day.
    """
    batchid = False
    lastdate = Log.objects.first().createdOn.date()
    if request.method == 'GET':
       date = lastdate
    if request.method == 'POST':
        date = request.POST.get('date',lastdate)
        batchid = request.POST.get('batchid',False)
    logs = Log.objects.filter(createdOn__date=date)
    if batchid:
        batch = get_object_or_404(Batch,identifier=batchid)
        logs = logs.filter(rack__batch=batch)

    return render(request,'tracing/logs.html',
                  {'logs': logs, 'date': date, 'batchid': batchid})


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
        return render(request,'tracing/upload.html',{'form': form})
    if not request.method == 'POST':
      messages.error(_('Wrong method'))
      return HttpResponseRedirect(reverse('tracing:inicio'))

    form = loadBatch(request.POST, request.FILES)
    if not form.is_valid():
        return render(request,'tracing/upload.html',{'form': form})

    batch = Batch()
    if form.cleaned_data['batchid']:
        batch.identifier = form.cleaned_data['batchid']
    batch.technician = get_object_or_404(Technician,
                                         id=form.cleaned_data['techid'])
    batch.save()
    # If we do not have a file, it's a "pre-loaded" batch
    if len(request.FILES):
        samples = request.FILES['samples']
        import csv,io
        samples.seek(0)
        lines = csv.DictReader(io.StringIO(samples.read().decode('utf-8')))
        for line in lines:
            sample = Sample()
            sample.batch = batch
            sample.code = line['code']
            sample.save()
    else:
        batch.preloaded = False
        batch.save()
    messages.success(request,
                     _('Batch {0} with {1} samples uploaded successfully').format(
                       batch.identifier,len(batch.sample_set.all())))
    return HttpResponseRedirect(reverse('tracing:inicio'))


@csrf_exempt
def moveSample(request):
    """
    Moves a sample as instructed by the robot where it is really hapening.
    The movement data arrives as a JSON object in the request body like:
    {'source': {'tray': 1, 'row': 'A', 'col': 1}, 
     'destination': {'tray': 2, 'row': 'A', 'col': 1}}
    """

    # We are expecting a POST request, any other type is an error
    if not request.method == 'POST':
       return HttpResponse("Bad method",status=400,content_type="text/plain") 
    # We first verify that the request comes from one of our robots
    # They MUST (RFC 2119) be directly connected to the server
    remoteip = request.META.get('REMOTE_ADDR')
    robot = get_object_or_404(Robot,ip=remoteip)
    if robot.state == 'E':
        return HttpResponse("Robot is empty",status=400,content_type="text/plain") 
    data = json.loads(request.body)
    # Get source rack
    rackO = get_object_or_404(Rack,robot=robot,
                                   position=data['source']['tray'])
    # Get moving tube, acually tubes do not move, but this was first ry code
    tube = get_object_or_404(Tube,rack=rackO,
                                  row=data['source']['row'],
                                  col=data['source']['col'])
    # Get destination rack
    rackD = get_object_or_404(Rack,robot=robot,
                                   position=data['destination']['tray'])

    # Do the move
    place(tube,rackD,(data['destination']['row'],data['destination']['col']))

    # Let's mark robot as processing
    if robot.state == 'I':
        robot.state = 'P'
        robot.save()

    # If input racks are empty, processing has finished
    if robot.state == 'P':
        if robot.station == 'A':
            finished = True
            for r in Rack.objects.filter(robot=robot,position__in=[1,3,4,6]):
                finished = finished and r.isEmpty()
        if robot.station in 'BC':
            r = Rack.objects.get(robot=robot,position=1)
            finished = r.isEmpty()
        if finished:
            robot.state = 'F'
            robot.save()

    return HttpResponse("OK",status=200,content_type="text/plain") 
    

def start(request):
    """
    Starts refreshing the robot display, waiting for movements
    """
    request.session['tracing_atwork'] = True
    return HttpResponseRedirect(reverse('tracing:inicio'))


def stop(request):
    """
    Stops refreshing the robot display and waiting for movements
    """
    # Safewarding, just in case
    if request.session.get('tracing_atwork',False):
        del (request.session['tracing_atwork'])
    return HttpResponseRedirect(reverse('tracing:inicio'))


