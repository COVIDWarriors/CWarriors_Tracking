# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
import time,datetime,uuid

# Create your models here.
class Robot(models.Model):
    TYPES = [('A','A'),('B','B'),('C','C')]
    STATES = [('I',_('Iddle')),('F',_('Finished')),('E',_('Empty')),
              ('P',_('Processing')),('D',_('Not connected'))]
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=True)
    station = models.CharField(max_length=1,verbose_name=_('Station'),
                               db_index=True,choices=TYPES)
    order = models.IntegerField(verbose_name=_('Station order'),
                                db_index=True,default=1)
    ip = models.GenericIPAddressField(verbose_name=_('IP address'),
                                      max_length=255, unique=True)
    connected = models.BooleanField(verbose_name=_('Can communicate with server'),
                                    default=True,db_index=True, editable=True)
    state = models.CharField(max_length=1,verbose_name=_('State'),default='D',
                             db_index=True,choices=STATES)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)


    class Meta:
        ordering = ['station','order','-modifiedOn']


    def __str__(self):
        return '{0}{1} {2}'.format(self.station,self.order,self.ip)


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        # Update state
        if len(self.rack_set.all()) == 0: self.state = 'E' # Empty
        if not len(self.rack_set.all()) == 0 and not self.state in 'FP':
            self.state = 'I' # Iddle
        # If the robot is not connected, states cannot change
        if not self.connected: self.state = 'D'
        super(Robot, self).save()


    def libre(self):
        if self.station == 'A':
            return len(self.rack_set.all()) < 5
        # Stations B and C, have two free positions
        return len(self.rack_set.all()) < 2


    pass


class Technician(models.Model):
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    name = models.CharField(max_length=100,verbose_name=_('Name'),db_index=True)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)


    class Meta:
        ordering = ['name','-modifiedOn']


    def __str__(self):
        return self.name


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        super(Technician, self).save()


    pass


class Procedure(models.Model):
    """
    Basic model to accomodate thermocycler options for Can Ruti
    """
    name = models.CharField(verbose_name=_('name'),
                            max_length=50, db_index=True)
    f1 = models.CharField(verbose_name=_('first fluorophore'),
                          max_length = 20, blank=True, null=True)
    f2 = models.CharField(verbose_name=_('second fluorophore'),
                          max_length = 20, blank=True, null=True)
    f3 = models.CharField(verbose_name=_('third fluorophore'),
                          max_length = 20, blank=True, null=True)
    f4 = models.CharField(verbose_name=_('fourth fluorophore'),
                          max_length = 20, blank=True, null=True)
    f5 = models.CharField(verbose_name=_('fith fluorophore'),
                          max_length = 20, blank=True, null=True)
    path = models.CharField(verbose_name=_('path'),
                            max_length = 200, blank=True, null=True)


    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)


    class Meta:
        verbose_name = _('Procedure')
        verbose_name_plural = _('Procedures')
        ordering = ['name']


    def __str__(self):
        return self.name


class Batch(models.Model):
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    technician = models.ForeignKey(Technician)
    procedure = models.ForeignKey(Procedure, null=True)
    preloaded = models.BooleanField(verbose_name=_('Pre-loaded batch'),
                                    default=True)
    started = models.DateTimeField(_('Processing started on'),
                                   db_index=True,null=True,blank=True)
    finished = models.DateTimeField(_('Processing completed on'),
                                    db_index=True,null=True,blank=True)


    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)

 
    class Meta:
        verbose_name_plural = _('Batches')
        ordering = ['identifier','technician','-modifiedOn']


    def __str__(self):
        return _('{} ({}): {} -> {} by {}').format(self.identifier,
                                                   len(self.sample_set.all()),
                                                   self.started,self.finished,
                                                   self.technician)


    def numSamples(self):
        # Number of processed and total samples
        return '{}/{}'.format(len(self.sample_set.filter(finished=True)),
                              len(self.sample_set.all()))


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        if (len(self.sample_set.filter(finished=False)) == 0 and
            not len(self.sample_set.filter(finished=True)) == 0) :
            self.finished = datetime.datetime.now()
        super(Batch, self).save()


    pass


class Sample(models.Model):
    RESULTS = [('N',_('No')),('Y',_('Yes')),('U',_('Unclear'))]
    LEVELS = [('L',_('Low')),('M',_('Medium')),('H',_('High'))]
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    code = models.CharField(verbose_name=_('Sample code'), max_length=100, db_index=True)
    batch = models.ForeignKey(Batch)
    finished = models.BooleanField(verbose_name=_('Processig completed'),
                                   db_index=True,default=False)
    result = models.CharField(verbose_name=_('Result'), max_length=1, db_index=True,
                              choices=RESULTS, blank=True, null=True, default='')
    igg = models.CharField(verbose_name=_('IgG'), max_length=1, db_index=True,
                           choices=LEVELS, blank=True, null=True, default='')
    igm = models.CharField(verbose_name=_('IgM'), max_length=1, db_index=True,
                           choices=LEVELS, blank=True, null=True, default='')

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)


    class Meta:
        ordering = ['batch','-modifiedOn']


    def __str__(self):
        return _('{0} en {1}').format(self.code,self.batch)


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        super(Sample, self).save()


    pass


class Tray(models.Model):
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    batch = models.ForeignKey(Batch)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)


    class Meta:
        ordering = ['batch','-modifiedOn']


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        super(Tray, self).save()


    pass


#class RackType(models.Model):
#
#    pass


class Rack(models.Model):
    DEEPWELL = 5
    EP = 6
    PCR = 7
    TYPE = [(4,'4x6'),(5,_('Deepwell')),
            (6,_('Extraction Plate')),(7,_('PCR Plate'))]
    POSITION = [(1,'1'),(2,'2'),(3,'3'),(4,'4'),(5,'5'),(6,'6')]
    ROWCOLS = {1:('D',1),2:('D',2),3:('D',4),4:('D',6),5:('H',12),
               6:('H',12),7:('H',12)} 
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    racktype = models.IntegerField(verbose_name=_('Rack type'),
                                   choices=TYPE,db_index=True)
    position = models.IntegerField(choices=POSITION,db_index=True,default=0)
    robot = models.ForeignKey(Robot,null=True,blank=True)
    finished = models.BooleanField(verbose_name=_('Processing completed'),
                                   default=False,db_index=True)
    passed = models.CharField(verbose_name=_('Steps'), max_length=3,
                              blank=True, default='', db_index=True)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)

 
    def listCols(self):
        return [(x,'%d' % x) for x in range(1,self.ROWCOLS[self.racktype][1]+1)]


    def listRows(self):
        return 'ABCDEFGH'[:'ABCDEFGH'.index(self.ROWCOLS[self.racktype][0])+1]


    def isEmpty(self):
        # An empty rack has no tubes :-)
        return len(self.tube_set.all()) == 0


    def isFilling(self):
        # A rack has tubes but not to its full capacity
        size = self.ROWCOLS[self.racktype][1]*(1+ord(self.ROWCOLS[self.racktype][0])-ord('A'))
        return 0 < len(self.tube_set.all()) < size


    def isFull(self):
        # A rack is full if the number of tubes equals number of rows by number of columns
        size = self.ROWCOLS[self.racktype][1]*(1+ord(self.ROWCOLS[self.racktype][0])-ord('A'))
        return len(self.tube_set.all()) == size


    def numSamples(self):
        return len(self.tube_set.all())


    class Meta:
        ordering = ['-modifiedOn']


    def __str__(self):
        if self.robot:
            return _('{0} with {1} samples in {2} tray {3}').format(
                                             self.get_racktype_display(),
                                             self.numSamples(),
                                             self.robot,self.position)
        else:
            return _('{0} with {1} samples {2} [{3}]').format(
                                             self.get_racktype_display(),
                                             self.numSamples(),
                                             self.identifier,self.passed)

    def shortIdent(self):
        return '{0}...{1}'.format(self.identifier[:9],self.identifier[-9:])


    def clean(self):
        if not self.racktype == self.DEEPWELL and self.position == 5:
            raise ValidationError({'tray': _('Only deepwells on tray 5')})
        if self.racktype == self.DEEPWELL and not self.position == 5:
            raise ValidationError({'tray': _('Deepwells only on tray 5')})


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        if self.robot:
            # If a deep well enters directly into a station B,
            # A is considered as passed
            if (self.racktype == self.DEEPWELL and self.robot.station == 'B'
                                               and self.passed == ''):
                self.passed = 'A'
            # If an extraction plate enters directly into a station C,
            # B is considered as passed
            if (self.racktype == self.EP and self.robot.station == 'C'
                                         and self.passed == ''):
                self.passed = 'B'
            if not self.robot.station in self.passed:
                self.passed += self.robot.station
        else:
            # No robot, no position
            self.position = 0
            if self.racktype == self.DEEPWELL and self.passed == 'AB':
                self.finished = True
            if self.racktype == self.EP and self.passed == 'BC':
                self.finished = True
            if self.racktype == self.PCR and self.passed == 'C':
                self.finished = True
            # Others stop at A
            if not self.finished and self.passed == 'A':
                self.finished = True
                
        super(Rack, self).save()


    pass


class Tube(models.Model):
    FILAS = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'),
             ('E', 'E'), ('F', 'F'), ('G', 'G'), ('H', 'H')]
    COLS = [(x,'%d' % x) for x in range(1,13)]
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    row = models.CharField(max_length=1,choices=FILAS,db_index=True)
    col = models.IntegerField(choices=COLS,db_index=True)
    history = models.CharField(max_length=250,default='',
                               blank=True,editable=False)
    rack = models.ForeignKey(Rack)
    sample = models.ForeignKey(Sample)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)

    class Meta:
        ordering = ['createdOn']


    def __str__(self):
        return '{0} {1}:{2} {3}'.format(self.rack,self.row,self.col,
                                        self.sample.code)


    def clean(self):
        if self.row > self.rack.ROWCOLS[self.rack.racktype][0]:
            raise ValidationError({'row':
                                   _('Row %d does not exist' % self.row)})
        if self.col > self.rack.ROWCOLS[self.rack.racktype][1]:
            raise ValidationError({'col':
                                   _('Column %d does not exist' % self.col)})


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        if not self.history == '':
            self.history += ' '
        current = '{0}:{1},{2}'.format(self.rack.identifier,self.row,self.col)
        if current not in self.history:
            self.history += current

        super(Tube, self).save()


    pass


class Log(models.Model):
    DIR = [('I',_('ENTERS')),('O',_('EXITS'))]
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    what = models.CharField(verbose_name=_('In / Out'),
                            max_length=1,choices=DIR,db_index=True)
    robot = models.ForeignKey(Robot)
    rack = models.ForeignKey(Rack)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)

 
    class Meta:
        ordering = ['-createdOn']


    def __str__(self):
        return '{} {} {} {}'.format(self.createdOn,
                                    self.rack,self.what,self.robot)


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        super(Log, self).save()


    pass
