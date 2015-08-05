# WORKING COPY OF SPLAT CODE LIBRARY
# based on routines developed by:
#    Christian Aganze
#    Daniella Bardalez Gagliuffi
#    Adam Burgasser
#    Caleb Choban
#    Ivanna Escala
#    Aishwarya Iyer
#    Yuhui Jin
#    Michael Lopez
#    Alex Mendez
#    Gretel Mercado
#    Jonathan Parra
#    Maitrayee Sahi
#    Adrian Suarez
#    Melisa Tallis
#    Tomoki Tamiya 

#
# CURRENT STATUS (3/12/2015)
# URGENT
# fails when reading in unpublished (online) data
#
# LESS URGENT
# reformat fits files so headers have valid information, and spectra are flux calibrated
# update information for sources in source database
# add help sections to all programs
# plotspectrum => multiplot, multipage files
# proper SQL search for database
# have classifybyindex return individual index classifications (e.g., 'full' keyword)

# imports
import astropy
import base64
import copy
import matplotlib.pyplot as plt
import numpy
import os
import random
import re
import scipy
import string
import sys
import urllib2
import warnings

from astropy.io import ascii, fits            # for reading in spreadsheet
from astropy.table import Table, join            # for reading in table files
from astropy.coordinates import SkyCoord      # coordinate conversion
from astropy import units as u            # standard units
from astropy import constants as const        # physical constants in SI units
from scipy import stats, signal
from scipy.integrate import trapz        # for numerical integration
from scipy.interpolate import interp1d

# local application/library specific import
#import bdevopar as splevol
from splat_plot import *
from splat_model import *

# suppress warnings - probably not an entirely safe approach!
numpy.seterr(all='ignore')
warnings.simplefilter("ignore")
#from splat._version import __version__

#set the SPLAT PATH, either from set environment variable or from sys.path
SPLAT_PATH = './'
if os.environ.get('SPLAT_PATH') != None:
    SPLAT_PATH = os.environ['SPLAT_PATH']
# TO PUT HERE - GET SPLAT PATH FROM PYTHON PATH
elif os.environ.get('PYTHONPATH') != None:
    path = os.environ['PYTHONPATH']
    for i in path.split(':'):
        if 'splat' in i:
            SPLAT_PATH = i
else:
    checkpath = ['splat' in r for r in sys.path]
    if max(checkpath):
        SPLAT_PATH = sys.path[checkpath.index(max(checkpath))]

#################### CONSTANTS ####################
SPLAT_URL = 'http://pono.ucsd.edu/~adam/splat/'
DATA_FOLDER = '/reference/Spectra/'
DB_FOLDER = '/db/'
SOURCES_DB = 'source_data.txt'
SPECTRA_DB = 'spectral_data.txt'
ORIGINAL_DB = 'db_spexprism.txt'

months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
spex_pixel_scale = 0.15            # spatial scale in arcseconds per pixel
uspex_pixel_scale = 0.10            # spatial scale in arcseconds per pixel
spex_wave_range = [0.65,2.45]*u.micron    # default wavelength range
max_snr = 1000.0                # maximum S/N ratio permitted
TMPFILENAME = 'splattmpfile'

spex_stdfiles = { \
    'M0.0': '11335_10505.fits',\
    'M1.0': '11364_10806.fits',\
    'M2.0': '11181_10187.fits',\
    'M3.0': '10823_11422.fits',\
    'M4.0': '12004_10444.fits',\
    'M5.0': '10829_10104.fits',\
    'M6.0': '11182_10188.fits',\
    'M7.0': '10822_11283.fits',\
    'M8.0': '10824_11423.fits',\
    'M9.0': '10821_11058.fits',\
    'L0.0': '10107_10315.fits',\
    'L1.0': '11072_11527.fits',\
    'L2.0': '10600_10957.fits',\
    'L3.0': '10592_11111.fits',\
    'L4.0': '10675_11572.fits',\
    'L5.0': '10351_10583.fits',\
    'L6.0': '10375_10696.fits',\
    'L7.0': '10678_10105.fits',\
    'L8.0': '10115_11254.fits',\
    'L9.0': '10268_10237.fits',\
    'T0.0': '10771_10871.fits',\
    'T1.0': '10767_10591.fits',\
    'T2.0': '10017_10945.fits',\
    'T3.0': '10034_10874.fits',\
    'T4.0': '10143_11632.fits',\
    'T5.0': '10021_11106.fits',\
    'T6.0': '10200_11236.fits',\
    'T7.0': '10159_10513.fits',\
    'T8.0': '10126_10349.fits',\
    'T9.0': '11536_10509.fits'}

# filters
FILTER_FOLDER = '/reference/Filters/'
filters = { \
    '2MASS_J': {'file': 'j_2mass.txt', 'description': '2MASS J-band'}, \
    '2MASS_H': {'file': 'h_2mass.txt', 'description': '2MASS H-band'}, \
    '2MASS_Ks': {'file': 'ks_2mass.txt', 'description': '2MASS Ks-band'}, \
    'MKO_J': {'file': 'j_atm_mko.txt', 'description': 'MKO J-band + atmosphere'}, \
    'MKO_H': {'file': 'h_atm_mko.txt', 'description': 'MKO H-band + atmosphere'}, \
    'MKO_K': {'file': 'k_atm_mko.txt', 'description': 'MKO K-band + atmosphere'}, \
    'MKO_Kp': {'file': 'mko_kp.txt', 'description': 'MKO Kp-band'}, \
    'MKO_Ks': {'file': 'mko_ks.txt', 'description': 'MKO Ks-band'}, \
    'NICMOS_F090M': {'file': 'nic1_f090m.txt', 'description': 'NICMOS F090M'}, \
    'NICMOS_F095N': {'file': 'nic1_f095n.txt', 'description': 'NICMOS F095N'}, \
    'NICMOS_F097N': {'file': 'nic1_f097n.txt', 'description': 'NICMOS F097N'}, \
    'NICMOS_F108N': {'file': 'nic1_f108n.txt', 'description': 'NICMOS F108N'}, \
    'NICMOS_F110M': {'file': 'nic1_f110m.txt', 'description': 'NICMOS F110M'}, \
    'NICMOS_F110W': {'file': 'nic1_f110w.txt', 'description': 'NICMOS F110W'}, \
    'NICMOS_F113N': {'file': 'nic1_f113n.txt', 'description': 'NICMOS F113N'}, \
    'NICMOS_F140W': {'file': 'nic1_f140w.txt', 'description': 'NICMOS F140W'}, \
    'NICMOS_F145M': {'file': 'nic1_f145m.txt', 'description': 'NICMOS F145M'}, \
    'NICMOS_F160W': {'file': 'nic1_f160w.txt', 'description': 'NICMOS F160W'}, \
    'NICMOS_F164N': {'file': 'nic1_f164n.txt', 'description': 'NICMOS F164N'}, \
    'NICMOS_F165M': {'file': 'nic1_f165m.txt', 'description': 'NICMOS F165M'}, \
    'NICMOS_F166N': {'file': 'nic1_f166n.txt', 'description': 'NICMOS F166N'}, \
    'NICMOS_F170M': {'file': 'nic1_f170m.txt', 'description': 'NICMOS F170M'}, \
    'NICMOS_F187N': {'file': 'nic1_f187n.txt', 'description': 'NICMOS F187N'}, \
    'NICMOS_F190N': {'file': 'nic1_f190n.txt', 'description': 'NICMOS F190N'}, \
    'NIRC2_J': {'file': 'nirc2-j.txt', 'description': 'NIRC2 J-band'}, \
    'NIRC2_H': {'file': 'nirc2-h.txt', 'description': 'NIRC2 H-band'}, \
    'NIRC2_Kp': {'file': 'nirc2-kp.txt', 'description': 'NIRC2 Kp-band'}, \
    'NIRC2_Ks': {'file': 'nirc2-ks.txt', 'description': 'NIRC2 Ks-band'}, \
    'WIRC_J': {'file': 'wirc_jcont.txt', 'description': 'WIRC J-cont'}, \
    'WIRC_H': {'file': 'wirc_hcont.txt', 'description': 'WIRC H-cont'}, \
    'WIRC_K': {'file': 'wirc_kcont.txt', 'description': 'WIRC K-cont'}, \
    'WIRC_CO': {'file': 'wirc_co.txt', 'description': 'WIRC CO'}, \
    'WIRC_CH4S': {'file': 'wirc_ch4s.txt', 'description': 'WIRC CH4S'}, \
    'WIRC_CH4L': {'file': 'wirc_ch4l.txt', 'description': 'WIRC CH4L'}, \
    'WIRC_Fe2': {'file': 'wirc_feii.txt', 'description': 'WIRC Fe II'}, \
    'WIRC_BrGamma': {'file': 'wirc_brgamma.txt', 'description': 'WIRC H I Brackett Gamma'}, \
    'WIRC_PaBeta': {'file': 'wirc_pabeta.txt', 'description': 'WIRC H I Paschen Beta'} \
    }

# Index sets
index_sets = ['burgasser','bardalez','tokunaga','reid','geballe','allers','testi','slesnick','mclean','rojas']

# change the command prompt
sys.ps1 = 'splat> '

#####################################################

        
# helper functions from Alex
def lazyprop(fn):
     attr_name = '_lazy_' + fn.__name__
     @property
     def _lazyprop(self):
          if not hasattr(self, attr_name):
                setattr(self, attr_name, fn(self))
          return getattr(self, attr_name)
     return _lazyprop

def Show(fn):
     def _show(self, *args, **kwargs):
          noplot = kwargs.pop('noplot', False)
          quiet = kwargs.pop('quiet', False)
          tmp = fn(self, *args, **kwargs)
#         if not quiet:
#                self.info()
#          if not noplot:
#                self.plot(**kwargs)
          return tmp
     return _show

def Copy(fn):
     def _copy(self, *args, **kwargs):
          out = copy.copy(self)
          return fn(out, *args, **kwargs)
     return _copy


# define the Spectrum class which contains the relevant information
class Spectrum(object):
    '''
    Description:
      Primary class for containing spectral and source data for SpeX Prism Library.

    **Usage**
       >>> import splat
       >>> sp = splat.Spectrum(filename='myspectrum.fits')      # read in a file
       >>> sp = splat.Spectrum('myspectrum.fits')               # same
       >>> sp = splat.Spectrum(10002)                           # read in spectrum with idkey = 10002
       >>> sp = splat.Spectrum(wave=wavearray,flux=fluxarray)   # create objects with wavelength & flux arrays
    '''

    def __init__(self, *args, **kwargs):
# some presets
        sdb = False
        self.model = kwargs.get('model',False)
        self.wlabel = kwargs.get('wlabel',r'Wavelength')
        self.wunit = kwargs.get('wunit',u.micron)
        self.wunit_label = kwargs.get('wunit_label',r'$\mu$m')
        self.flabel = kwargs.get('flabel',r'F$_{\lambda}$')
        self.fscale = kwargs.get('fscale','')
        self.funit = kwargs.get('funit',u.erg/(u.cm**2 * u.s * u.micron))
        self.funit_label = kwargs.get('funit_label',r'erg~cm$^{-2}$~s$^{-1}$~$\mu$m$^{-1}$')
        self.resolution = kwargs.get('resolution',150)    # default placeholder
        self.slitpixelwidth = kwargs.get('slitwidth',3.33)        # default placeholder
        self.slitwidth = self.slitpixelwidth*spex_pixel_scale
        self.header = kwargs.get('header',Table())
        self.filename = kwargs.get('file','')
        self.filename = kwargs.get('filename',self.filename)
        self.idkey = kwargs.get('idkey',False)

# option 1: a filename is given
        if (len(args) > 0):
            if isinstance(args[0],str):
                self.filename = args[0]
        if kwargs.get('file',self.filename) != '':
            self.filename = kwargs.get('file',self.filename)
        if kwargs.get('filename',self.filename) != '':
            self.filename = kwargs.get('filename',self.filename)
        
# option 2: a spectrum ID is given
        if (len(args) > 0):
            if isinstance(args[0],int):
                self.idkey = args[0]
        
        if self.idkey != False:
#            self.idkey = kwargs.get('idkey',self.idkey)
            sdb = keySpectrum(self.idkey)
            if sdb != False:
                self.filename = sdb['DATA_FILE'][0]
        elif self.model == False and self.filename != '':
            t = searchLibrary(file=self.filename)
            if len(t) > 0:
                sdb = t
        else:
            sdb = False

# set up folder - by default this is local data directory
        kwargs['folder'] = kwargs.get('folder',SPLAT_PATH+DATA_FOLDER)
        self.simplefilename = os.path.basename(self.filename)
        self.file = self.filename
        self.name = self.filename
        kwargs['filename'] = self.filename

# option 3: wave and flux are given
        if len(kwargs.get('wave','')) > 0 and len(kwargs.get('flux','')) > 0:
            self.wave = kwargs['wave']
            self.flux = kwargs['flux']
            if len(kwargs.get('noise','')) > 0:
                self.noise = kwargs['noise']
            else:
                self.noise = numpy.array([numpy.nan for i in self.wave])

# read in data from file
        elif self.filename != '':
            try:
                rs = readSpectrum(self.filename,**kwargs)
                self.wave = rs['wave']
                self.flux = rs['flux']
                self.noise = rs['noise']
                self.header = rs['header']
            except:
                raise NameError('\nCould not load up spectral file {:s}'.format(kwargs.get('filename','')))

# empty spectrum vessel (used for copying)
        else:
            self.wave = []
            self.flux = []
            self.noise = []

# process spectral data
        if len(self.wave) > 0:
# convert to numpy arrays
            self.wave = numpy.array(self.wave)
            self.flux = numpy.array(self.flux)
            self.noise = numpy.array(self.noise)
# enforce positivity and non-nan
            if (numpy.nanmin(self.flux) < 0):
                self.flux[numpy.where(self.flux < 0)] = 0.
            self.flux[numpy.isnan(self.flux)] = 0.
# check on noise being too low
            if (numpy.nanmax(self.flux/self.noise) > max_snr):
                self.noise[numpy.where(self.flux/self.noise > max_snr)]=numpy.median(self.noise)
# convert to astropy quantities with units
# assuming input is flam in erg/s/cm2/micron
            if ~isinstance(self.wave,astropy.units.quantity.Quantity):
                self.wave = numpy.array(self.wave)*self.wunit
            if ~isinstance(self.flux,astropy.units.quantity.Quantity):
                self.flux = numpy.array(self.flux)*self.funit
            if ~isinstance(self.wave,astropy.units.quantity.Quantity):
                self.noise = numpy.array(self.noise)*self.funit
# some conversions
            self.flam = self.flux
            self.nu = self.wave.to('Hz',equivalencies=u.spectral())
            self.fnu = self.flux.to('Jy',equivalencies=u.spectral_density(self.wave))
            self.fnunit = u.Jansky
# calculate variance
            self.variance = self.noise**2
            self.dof = numpy.round(len(self.wave)/self.slitpixelwidth)
# signal to noise
            w = numpy.where(self.flux.value > numpy.median(self.flux.value))
            self.snr = numpy.nanmean(self.flux.value[w]/self.noise.value[w])

# preserve original values
            self.wave_original = copy.deepcopy(self.wave)
            self.flux_original = copy.deepcopy(self.flux)
            self.noise_original = copy.deepcopy(self.noise)
            self.variance_original = copy.deepcopy(self.variance)
#        self.resolution = copy.deepcopy(self.resolution)
#        self.slitpixelwidth = copy.deepcopy(self.slitpixelwidth)

# populate information on source and spectrum from database
        if sdb != False:
            for k in sdb.keys():
                setattr(self,k.lower(),sdb[k][0])
            self.shortname = designationToShortName(self.designation)
            self.date = self.observation_date
# convert some data into numbers
            kconv = ['ra','dec','julian_date','median_snr','resolution','airmass',\
            'jmag','jmag_error','hmag','hmag_error','kmag','kmag_error','source_key']
            for k in kconv:
                try:
                    setattr(self,k,float(getattr(self,k)))
                except:
                    setattr(self,k,numpy.nan)
#                print getattr(self,k)
                
# information on model
        if self.model == True:
            self.teff = kwargs.get('teff',numpy.nan)
            self.logg = kwargs.get('logg',numpy.nan)
            self.z = kwargs.get('z',numpy.nan)
            self.fsed = kwargs.get('fsed',numpy.nan)
            self.cld = kwargs.get('cld',numpy.nan)
            self.kzz = kwargs.get('kzz',numpy.nan)
            self.slit = kwargs.get('slit',numpy.nan)
            self.modelset = kwargs.get('set','')
            self.name = self.modelset+' Teff='+str(self.teff)+' logg='+str(self.logg)+' [M/H]='+str(self.logg)
            self.fscale = 'Surface'
        self.history = ['Loaded']

                
    def __copy__(self):
            s = type(self)()
            s.__dict__.update(self.__dict__)
            return s    

# backup version
    def copy(self):
            s = type(self)()
            s.__dict__.update(self.__dict__)
            return s    

    def __repr__(self):
        '''A simple representation of an object is to just give it a name'''
        return 'Spectrum of {}'.format(self.name)

    def __add__(self,other):
        '''Adding two spectra '''
        sp = self.copy()
        f = interp1d(other.wave,other.flux,bounds_error=False,fill_value=0.)
        n = interp1d(other.wave,other.variance,bounds_error=False,fill_value=numpy.nan)
        sp.flux = numpy.add(self.flux,f(self.wave)*other.funit)
        sp.variance = sp.variance+n(self.wave)*(other.funit**2)
        sp.noise = sp.variance**0.5
        sp.flux_original=sp.flux
        sp.noise_original=sp.noise
        sp.variance_original=sp.variance
        sp.name = self.name+' + '+other.name
        return sp

    def __sub__(self,other):
        '''Subtracting two spectra '''
        sp = self.copy()
        f = interp1d(other.wave,other.flux,bounds_error=False,fill_value=0.)
        n = interp1d(other.wave,other.variance,bounds_error=False,fill_value=numpy.nan)
        sp.flux = numpy.subtract(self.flux,f(self.wave)*other.funit)
        sp.variance = sp.variance+n(self.wave)*(other.funit**2)
        sp.noise = sp.variance**0.5
        sp.flux_original=sp.flux
        sp.noise_original=sp.noise
        sp.variance_original=sp.variance
        sp.name = self.name+' - '+other.name
        return sp

    def __mul__(self,other):
        '''Multiplying two spectra'''
        sp = self.copy()
        f = interp1d(other.wave,other.flux,bounds_error=False,fill_value=0.)
        n = interp1d(other.wave,other.variance,bounds_error=False,fill_value=numpy.nan)
        sp.flux = numpy.multiply(self.flux,f(self.wave)*other.funit)
        sp.variance = numpy.multiply(sp.flux**2,(\
            numpy.divide(self.variance.value,sp.flux.value**2)+numpy.divide(n(self.wave),f(self.wave)**2)))
        sp.noise = sp.variance**0.5
        sp.flux_original=sp.flux
        sp.noise_original=sp.noise
        sp.variance_original=sp.variance
        sp.name = self.name+' x '+other.name
        sp.funit = sp.flux.unit
        return sp

    def __div__(self,other):
        '''Dividing two spectra'''
        sp = self.copy()
        f = interp1d(other.wave,other.flux,bounds_error=False,fill_value=0.)
        n = interp1d(other.wave,other.variance,bounds_error=False,fill_value=numpy.nan)
        sp.flux = numpy.divide(self.flux,f(self.wave)*other.funit)
        sp.variance = numpy.multiply(sp.flux**2,(\
            numpy.divide(self.variance.value,sp.flux.value**2)+numpy.divide(n(self.wave),f(self.wave)**2)))
        sp.noise = sp.variance**0.5
# clean up infinities
        sp.flux = numpy.where(numpy.absolute(sp.flux) == numpy.inf, numpy.nan, sp.flux)*u.erg/u.erg      
        sp.noise = numpy.where(numpy.absolute(sp.noise) == numpy.inf, numpy.nan, sp.noise)*u.erg/u.erg     
        sp.variance = numpy.where(numpy.absolute(sp.variance) == numpy.inf, numpy.nan, sp.variance)*u.erg/u.erg       
        sp.flux_original=sp.flux
        sp.noise_original=sp.noise
        sp.variance_original=sp.variance
        sp.name = self.name+' / '+other.name
        sp.funit = sp.flux.unit
        return sp

    def info(self):
          '''Report some information about this spectrum'''
          if (self.model):
              print '\n{} model with the following parmeters:'.format(self.modelset)
              print 'Teff = {}'.format(self.teff)
              print 'logg = {}'.format(self.logg)
              print 'z = {}'.format(self.z)
              print 'fsed = {}'.format(self.fsed)
              print 'cld = {}'.format(self.cld)
              print 'kzz = {}'.format(self.kzz)
              print 'slit = {}\n'.format(self.slit)
          else:
              print '''Spectrum of {0} taken on {1}'''.format(self.name, self.date)
          return

    def flamToFnu(self):
         '''Convert flux density from F_lam to F_nu, the later in Jy'''
         self.funit = u.Jy
         self.flabel = 'F_nu'
         self.flux.to(self.funit,equivalencies=u.spectral_density(self.wave))
         self.noise.to(self.funit,equivalencies=u.spectral_density(self.wave))
         return

    def fluxCalibrate(self,filter,mag,**kwargs):
        '''Calibrate spectrum to input magnitude'''
        absolute = kwargs.get('absolute',False)
        apparent = kwargs.get('apparent',False)
        self.normalize()
        apmag,apmag_e = filterMag(self,filter,**kwargs)
# NOTE: NEED TO INCORPORATE UNCERTAINTY INTO SPECTRAL UNCERTAINTY
        if (~numpy.isnan(apmag)):
            self.scale(10.**(0.4*(apmag-mag)))
            if (absolute):
                self.fscale = 'Absolute'
            if (apparent):
                self.fscale = 'Apparent'
        return

# determine maximum flux, by default in non telluric regions
    def fluxMax(self,**kwargs):
        if kwargs.get('maskTelluric',True):
            return numpy.nanmax(self.flux.value[numpy.where(\
                numpy.logical_or(\
                    numpy.logical_and(self.wave > 0.9*u.micron,self.wave < 1.35*u.micron),
                    numpy.logical_and(self.wave > 1.42*u.micron,self.wave < 1.8*u.micron),
                    numpy.logical_and(self.wave > 1.92*u.micron,self.wave < 2.3*u.micron)))])*self.funit
        else:    
            return numpy.nanmax(self.flux.value[numpy.where(\
                numpy.logical_and(self.wave > 0.9*u.micron,self.wave < 2.3*u.micron))])*self.funit

    def fnuToFlam(self):
         '''Convert flux density from F_nu to F_lam, the later in erg/s/cm2/Hz'''
         self.funit = u.erg/(u.cm**2 * u.s * u.micron)
         self.flabel = 'F_lam'
         self.flux.to(self.funit,equivalencies=u.spectral_density(self.wave))
         self.noise.to(self.funit,equivalencies=u.spectral_density(self.wave))
         self.variance = self.noise**2
         return

    def normalize(self,**kwargs):
        '''Normalize spectrum'''
        self.scale(1./self.fluxMax(**kwargs).value)
        self.fscale = 'Normalized'
        return

    def plot(self,**kwargs):
        plotSpectrum(self,showNoise=True,showZero=True,**kwargs)

    def reset(self):
        '''Reset to original spectrum'''
        self.wave = copy.deepcopy(self.wave_original)
        self.flux = copy.deepcopy(self.flux_original)
        self.noise = copy.deepcopy(self.noise_original)
        self.variance = copy.deepcopy(self.variance_original)
        self.resolution = copy.deepcopy(self.resolution_original)
        self.slitpixelwidth = copy.deepcopy(self.slitpixelwidth_original)
        self.slitwidth = self.slitpixelwidth*spex_pixel_scale
        self.fscale = ''
        return

    def scale(self,factor):
         '''Scale spectrum and noise by a constant factor'''
         self.flux = self.flux*factor
         self.noise = self.noise*factor
         self.variance = self.noise**2
         self.fscale = 'Scaled'
         return
        
    def smooth(self,**kwargs):
        '''Smooth spectrum to a constant slit width (smooth by pixels)'''
        method = kwargs.get('method','hanning')
        kwargs['method'] = method
        swargs = copy.deepcopy(kwargs)
        if (kwargs.get('slitPixelWidth','') != ''):
            del swargs['slitPixelWidth']
            self.smoothToSlitPixelWidth(kwargs['slitPixelWidth'],**swargs)
        elif (kwargs.get('resolution','') != ''):
            del swargs['resolution']
            self.smoothToResolution(kwargs['resolution'],**swargs)
        elif (kwargs.get('slitWidth','') != ''):
            del swargs['slitWidth']
            self.smoothToSlitWidth(kwargs['slitWidth'],**swargs)
        return

    def smoothToResolution(self,resolution,**kwargs):
        '''Smooth spectrum to a constant resolution'''
        overscale = kwargs.get('overscale',10.)
        method = kwargs.get('method','hanning')
        kwargs['method'] = method

# do nothing if requested resolution is higher than current resolution
        if (resolution < self.resolution):
# sample onto a constant resolution grid at 5x current resolution
             r = resolution*overscale
             waveRng = self.waveRange()
             npix = numpy.floor(numpy.log(waveRng[1]/waveRng[0])/numpy.log(1.+1./r))
             wave_sample = [waveRng[0]*(1.+1./r)**i for i in numpy.arange(npix)]
             f = interp1d(self.wave,self.flux,bounds_error=False,fill_value=0.)
             v = interp1d(self.wave,self.variance,bounds_error=False,fill_value=numpy.nan)
             flx_sample = f(wave_sample)*self.funit
             var_sample = v(wave_sample)*self.funit**2
# now convolve a function to smooth resampled spectrum
             window = signal.get_window(method,numpy.round(overscale))
             neff = numpy.sum(window)/numpy.nanmax(window)        # effective number of pixels
             flx_smooth = signal.convolve(flx_sample, window/numpy.sum(window), mode='same')
             var_smooth = signal.convolve(var_sample, window/numpy.sum(window), mode='same')/neff
# resample back to original wavelength grid
             f = interp1d(wave_sample,flx_smooth,bounds_error=False,fill_value=0.)
             v = interp1d(wave_sample,var_smooth,bounds_error=False,fill_value=0.)
             self.flux = f(self.wave)*self.funit
             self.variance = v(self.wave)*self.funit**2
             self.noise = numpy.array([n**0.5 for n in self.variance])
             self.slitpixelwidth = self.slitpixelwidth*self.resolution/resolution
             self.resolution = resolution
             self.slitwidth = self.slitpixelwidth*spex_pixel_scale
             self.history = ['Smoothed to constant resolution {}'.format(self.resolution)]        
        return

    def smoothToSlitPixelWidth(self,width,**kwargs):
        '''Smooth spectrum to a constant slit width (smooth by pixels)'''
        method = kwargs.get('method','hanning')
        kwargs['method'] = method
# do nothing if requested resolution is higher than current resolution
        if (width > self.slitpixelwidth):
# convolve a function to smooth spectrum
            window = signal.get_window(method,numpy.round(width))
            neff = numpy.sum(window)/numpy.nanmax(window)        # effective number of pixels
            self.flux = signal.convolve(self.flux, window/numpy.sum(window), mode='same')
            self.variance = signal.convolve(self.variance, window/numpy.sum(window), mode='same')/neff
            self.noise = numpy.array([n**0.5 for n in self.variance])
            self.resolution = self.resolution*self.slitpixelwidth/width
            self.slitpixelwidth = width
            self.slitwidth = self.slitpixelwidth*spex_pixel_scale
            self.history = ['Smoothed to slit width of {}'.format(self.slitwidth)]        
        return

    def smoothToSlitWidth(self,width,**kwargs):
        method = kwargs.get('method','hanning')
        kwargs['method'] = method
        '''Smooth spectrum to a constant slit width (smooth by pixels)'''
        pwidth = width/spex_pixel_scale
        self.smoothToSlitPixelWidth(pwidth,**kwargs)
        return

    def snr(self):
        '''Compute a representative S/N value'''
        pass
        return

    def surface(self,radius):
         '''Convert to surface fluxes given a radius, assuming at absolute fluxes'''
         pass
         return

    def waveRange(self):
        ii = numpy.where(self.flux.value > 0)
        return [numpy.nanmin(self.wave[ii]), numpy.nanmax(self.wave[ii])]
     
        
                             

# FUNCTIONS FOR SPLAT
def caldateToDate(d):
    '''
    :Purpose: Convert from numeric date to calendar date, and vice-versa.
    :param d: A numeric date of the format '20050412', or a date in the 
                calendar format '2005 Jun 12'
    :Example:
       >>> import splat
       >>> caldate = splat.dateToCaldate('20050612')
       >>> print caldate
       2005 Jun 12
       >>> date = splat.caldateToDate('2005 June 12')
       >>> print date
       20050612
    '''
    return d[:4]+str((months.index(d[5:8])+1)/100.)[2:4]+d[-2:]


def checkFile(filename,**kwargs):
    '''
    :Purpose: Checks if a spectrum file exists in the SPLAT's library.
    :param filename: A string containing the spectrum's filename.
    :Example: 
       >>> import splat
       >>> spectrum1 = 'spex_prism_1315+2334_110404.fits'
       >>> print splat.checkFile(spectrum1)
       True
       >>> spectrum2 = 'fake_name.fits'
       >>> print splat.checkFile(spectrum2)
       False
    '''
    url = kwargs.get('url',SPLAT_URL)+'/Spectra/'
    flag = checkOnline()
    if (flag):
        try:
            open(os.path.basename(filename), 'wb').write(urllib2.urlopen(url+filename).read())
        except urllib2.URLError:
            flag = False
    return flag


def checkAccess(**kwargs):
    '''
    :Purpose: Checks if user has access to unpublished spectra in SPLAT library.
    :Example: 
       >>> import splat
       >>> print splat.checkAccess()
       True
    :Note: Must have the file .splat_access in your home directory with the correct passcode to use.
    '''
    access_file = '.splat_access'
    result = False

    try:
        home = os.environ.get('HOME')
        if home == None:
            home = './'
        bcode = urllib2.urlopen(SPLAT_URL+access_file).read()
        lcode = base64.b64encode(open(home+'/'+access_file,'r').read())
        if (bcode in lcode):        # changed to partial because of EOL variations
            result = True
    except:
        result = False

    if (kwargs.get('report','') != ''):
        if result == True:
            print 'You have full access to all SPLAT data'
        else:
            print 'You have access only to published data'
    return result
    

def checkLocal(file):
    '''
    :Purpose: Checks if a file is present locally or within the SPLAT
                code directory
    :Example:
       >>> import splat
       >>> splat.checkLocal('splat.py')
       True  # found the code
       >>> splat.checkLocal('parameters.txt')
       False  # can't find this file
       >>> splat.checkLocal('SpectralModels/BTSettl08/parameters.txt')
       True  # found it
    '''
    if not os.path.exists(file):
        if not os.path.exists(SPLAT_PATH+file):
            return ''
        else:
            return SPLAT_PATH+file
    else:
        return file


def checkOnline(*args):
    '''
    :Purpose: Checks if SPLAT's URL is accessible from your machine--
                that is, checks if you and the host are online. Alternately
                checks if a given filename is present locally or online
    :Example:
       >>> import splat
       >>> splat.checkOnline()
       True  # SPLAT's URL was detected.
       >>> splat.checkOnline()
       False # SPLAT's URL was not detected.
       >>> splat.checkOnline('SpectralModels/BTSettl08/parameters.txt')
       False # Could not find this online file.
    '''
    if (len(args) != 0):
        if 'http://' in args[0]:
            try:
                open(os.path.basename(TMPFILENAME), 'wb').write(urllib2.urlopen(args[0]).read())
                os.remove(os.path.basename(TMPFILENAME))
                return args[0]
            except urllib2.URLError:
                try:
                    open(os.path.basename(TMPFILENAME), 'wb').write(urllib2.urlopen(SPLAT_URL+args[0]).read())
                    os.remove(os.path.basename(TMPFILENAME))
                    return SPLAT_URL+args[0]
                except:
                    return ''
        else:
            return ''

    else:
        try:
            urllib2.urlopen(SPLAT_URL)
            return SPLAT_URL
        except urllib2.URLError:
            return ''



def classifyByIndex(sp, *args, **kwargs):
    '''
    :Purpose: Determine the spectral type and uncertainty for a spectrum 
                based on indices. Makes use of published index-SpT relations
                from Reid et al. (2001); Testi et al. (2001); Allers et al. 
                (2007); and Burgasser (2007). Returns 2-element tuple 
                containing spectral type (numeric or string) and 
                uncertainty.
    :param sp: Spectrum class object, which should contain wave, flux and 
                 noise array elements.
    :param set: (optional, default='burgasser') named set of indices to measure and compute spectral type 
        - 'allers': H2O from Allers et al.
        - 'burgasser': H2O-J, CH4-J, H2O-H, CH4-H, CH4-K from Burgasser (2007)
        - 'reid':H2O-A and H2O-B from Reid et al.(2001)
        - 'testi': sHJ, sKJ, sH2O_J, sH2O_H1, sH2O_H2, sH2O_K from Testi et al. (2001) 
    :param string: (optional, default=False) return spectral type as a string (uses typeToNum)
    :param round: (optional, default=False)  rounds off to nearest 0.5 subtypes
    :param remeasure: (optional, default=True) force remeasurement of indices
    :param nsamples: (optional, default=100) number of Monte Carlo samples for error computation
    :param nloop: (optional, default=5) number of testing loops to see if spectral type is within a certain range

    :Example: 
       >>> import splat
       >>> spc = splat.getSpectrum(shortname='0559-1404')[0]
       >>> print splat.classifyByIndex(spc, string=True, set='burgasser', round=True)
         ('T4.5', 0.2562934083414341)

    :Note:
        * Need to allow output of individual spectral types from individual indices
    '''
    
    str_flag = kwargs.get('string', True)
    rnd_flag = kwargs.get('round', False)
    rem_flag = kwargs.get('remeasure', True)
    nsamples = kwargs.get('nsamples', 100)
    nloop = kwargs.get('nloop', 5)
    set = kwargs.get('set','burgasser')
    set = kwargs.get('ref',set)
    kwargs['set'] = set
    allowed_sets = ['aganze','burgasser','reid','testi','allers']
    if (set.lower() not in allowed_sets):
        print '\nWarning: index classification method {} not present; returning nan\n\n'.format(set)
        return numpy.nan, numpy.nan

# measure indices if necessary
    if (len(args) != 0):
        indices = args[0]

# Reid et al. (2001, AJ, 121, 1710)
    elif (set.lower() == 'reid'):
        if (rem_flag or len(args) == 0):
            indices = measureIndexSet(sp, **kwargs)
        sptoffset = 20.
        sptfact = 1.
        coeffs = { \
            'H2O-A': {'fitunc': 1.18, 'range': [18,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [-32.1, 23.4]}, \
            'H2O-B': {'fitunc': 1.02, 'range': [18,28], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [-24.9, 20.7]}}

# Testi et al. (2001, ApJ, 522, L147)
    elif (set.lower() == 'testi'):
        if (rem_flag or len(args) == 0):
            indices = measureIndexSet(sp, **kwargs)
        sptoffset = 20.
        sptfact = 10.
        coeffs = { \
            'sHJ': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [-1.87, 1.67]}, \
            'sKJ': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [-1.20, 2.01]}, \
            'sH2O_J': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [1.54, 0.98]}, \
            'sH2O_H1': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [1.27, 0.76]}, \
            'sH2O_H2': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [2.11, 0.29]}, \
            'sH2O_K': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [2.36, 0.60]}}

# Burgasser (2007, ApJ, 659, 655) calibration
    elif (set.lower() == 'burgasser'):
        if (rem_flag or len(args) == 0):
            indices = measureIndexSet(sp, **kwargs)
        sptoffset = 20.
        sptfact = 1.
        coeffs = { \
            'H2O-J': {'fitunc': 0.8, 'range': [20,39], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [1.038e2, -2.156e2,  1.312e2, -3.919e1, 1.949e1]}, \
            'H2O-H': {'fitunc': 1.0, 'range': [20,39], 'spt': 0., 'sptunc': 99., 'mask': 1.,  \
            'coeff': [9.087e-1, -3.221e1, 2.527e1, -1.978e1, 2.098e1]}, \
            'CH4-J': {'fitunc': 0.7, 'range': [30,39], 'spt': 0., 'sptunc': 99., 'mask': 1.,  \
            'coeff': [1.491e2, -3.381e2, 2.424e2, -8.450e1, 2.708e1]}, \
            'CH4-H': {'fitunc': 0.3, 'range': [31,39], 'spt': 0., 'sptunc': 99., 'mask': 1.,  \
            'coeff': [2.084e1, -5.068e1, 4.361e1, -2.291e1, 2.013e1]}, \
            'CH4-K': {'fitunc': 1.1, 'range': [20,37], 'spt': 0., 'sptunc': 99., 'mask': 1.,  \
            'coeff': [-1.259e1, -4.734e0, 2.534e1, -2.246e1, 1.885e1]}}

# Allers et al. (2013, ApJ, 657, 511)
    elif (set.lower() == 'allers'):
        if (rem_flag or len(args) == 0):
            kwargs['set'] = 'mclean'
            i1 = measureIndexSet(sp, **kwargs)
            kwargs['set'] = 'slesnick'
            i2 = measureIndexSet(sp, **kwargs)
            kwargs['set'] = 'allers'
            i3 = measureIndexSet(sp, **kwargs)
            indices = dict(i1.items() + i2.items() + i3.items())
        sptoffset = 10.
        sptfact = 1.
        coeffs = { \
            'H2O': {'fitunc': 0.390, 'range': [15,25], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [24.0476, -104.424, 169.388,-83.5437]}, \
            'H2O-1': {'fitunc': 1.097, 'range': [14,25], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [28.5982, -80.7404, 39.3513, 12.1927]}, \
            'H2OD': {'fitunc': 0.757, 'range': [20,28], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [-97.230, 229.884, -202.245, 79.4477]}, \
            'H2O-2': {'fitunc': 0.501, 'range': [14,22], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [37.5013, -97.8144, 55.4580, 10.8822]}}

# Aganze et al. 2015 (in preparation)
    elif (set.lower() == 'aganze'):
        if (rem_flag or len(args) == 0):
            kwargs['set'] = 'geballe'
            i1 = measureIndexSet(sp, **kwargs)
            kwargs['set'] = 'slesnick'
            i2 = measureIndexSet(sp, **kwargs)
            kwargs['set'] = 'allers'
            i3 = measureIndexSet(sp, **kwargs)
            kwargs['set'] = 'burgasser'
            i4 = measureIndexSet(sp, **kwargs)
            kwargs['set'] = 'reid'
            i5 = measureIndexSet(sp, **kwargs)
            kwargs['set'] = 'tokunaga'
            i6 = measureIndexSet(sp, **kwargs)    
            indices = dict(i1.items() + i2.items() + i3.items()+ i4.items() + i5.items() + i6.items())
            
        sptoffset = 0.0
        sptfact = 1.0
        coeffs = { \
            'H2O': {'fitunc': 0.863, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [ -361.25130485, 1663.93768276, -2870.50724103,  2221.99873698, -638.03203556]}, \
            'H2O-J': {'fitunc': 0.902, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [ -146.21144969 ,  632.34633568,  -1008.79681307,   678.80156994 , -137.92921741]}, \
            'H2O-K': {'fitunc':0.973, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [-21366.79781425,  38630.25299752,  -25984.2424891  ,  7651.46728497,  -805.79462608]}, \
            'K1': {'fitunc':0.878, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [  10.29493194 ,  -62.71016723 ,  115.76162692,   -60.72606292 ,  15.1905955 ]}, \
            'K2': {'fitunc':0.934, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [ -44.78083424 , 225.58312733 ,-428.98225919 ,379.28205312 , -114.74469746]}, \
            'H2O-1': {'fitunc':1.035, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [ -2999.69506898 , 11118.42653046 , -15340.87706264  ,9307.5183138, -2068.63608393]}, \
            'H2O-B': {'fitunc':1.096, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [ -458.07448646 , 1547.35113353 , -1936.51451632 , 1041.95275566  , -178.50240834]}, \
            'H2O-H': {'fitunc':1.041, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [ -767.21126974 , 2786.26168556 , -3762.93498987,   2211.62680244,  -451.54693932]}, \
            'CH4-2.2': {'fitunc': 0.932, 'range': [15,23], 'spt': 0., 'sptunc': 99., 'mask': 1., \
            'coeff': [-331.74150369, 133.08406514  , -0.84614999  , 19.78717161  , 17.18479766]}}

    else:
        sys.stderr.write('\nWarning: '+set.lower()+' SpT-index relation not in classifyByIndex code\n\n')
        return numpy.nan, numpy.nan

    for index in coeffs.keys():
        vals = numpy.polyval(coeffs[index]['coeff'],numpy.random.normal(indices[index][0],indices[index][1],nsamples))*sptfact
        coeffs[index]['spt'] = numpy.nanmean(vals)+sptoffset
        coeffs[index]['sptunc'] = (numpy.nanstd(vals)**2+coeffs[index]['fitunc']**2)**0.5
#        print index, coeffs[index]['spt'], coeffs[index]['range'], coeffs[index]['spt'] < coeffs[index]['range'][0], coeffs[index]['spt'] > coeffs[index]['range'][1]
        if (coeffs[index]['spt'] < coeffs[index]['range'][0] or coeffs[index]['spt'] > coeffs[index]['range'][1]):
            coeffs[index]['mask'] = 0.
        else:
            coeffs[index]['mask'] = 1.
    
    for i in numpy.arange(nloop):
        wts = [coeffs[index]['mask']/coeffs[index]['sptunc']**2 for index in coeffs.keys()]
        if (numpy.nansum(wts) == 0.):
            sys.stderr.write('\nIndices do not fit within allowed ranges\n\n')
            return numpy.nan, numpy.nan            
        vals = [coeffs[index]['mask']*coeffs[index]['spt']/coeffs[index]['sptunc']**2 \
            for index in coeffs.keys()]
        sptn = numpy.nansum(vals)/numpy.nansum(wts)
        sptn_e = 1./numpy.nansum(wts)**0.5
        for index in coeffs.keys():
            if (sptn < coeffs[index]['range'][0] or sptn > coeffs[index]['range'][1]):
                coeffs[index]['mask'] = 0

    
# round off to nearest 0.5 subtypes if desired
    if (rnd_flag):
        sptn = 0.5*numpy.around(sptn*2.)

# change to string if desired
    if (str_flag):
        spt = typeToNum(sptn,uncertainty=sptn_e)
    else:
        spt = sptn

    return spt, sptn_e



def classifyByStandard(sp, *args, **kwargs):
    '''
    :Purpose: ``Determine the spectral type and uncertainty for a 
                spectrum by direct comparison to spectral standards. 
                Standards span M0-T9 and include the standards listed in 
                Kirkpatrick et al. (2010) with addition of UGPS 0722-0540 
                as the T9 standard.  Returns the best match or an F-test 
                weighted mean and uncertainty. There is an option to follow 
                the procedure of Kirkpatrick et al. (2010), fitting only in 
                the 0.9-1.4 micron region``
    :Usage: ``spt,unc = splat.classifyByStandard(sp, \**kwargs)``
    :param sp: ``Spectrum class object, which should contain wave, flux and 
                 noise array elements.``
    :param \**kwargs (optional): - ``'best' = False: return the best fit standard type only``
                        - ``'compareto' = False: compare to a single standard (string or number)``
                        - ``'plot' = False: generate a plot comparing best fit standard to source, can be save to a file using the file keyword``
                        - ``'file' = '': output spectrum plot to a file``
                        - ``'method' = '': set to 'kirkpatrick' to follow the Kirkpatrick et al. (2010) method, fitting only to the 0.9-1.4 micron band``
                        - ``'sptrange' = ['M0','T9']: constraint spectral type range to fit, can be strings or numbers``
                        - ``'string' = True: return spectral type as a string``
                        - ``'verbose' = False: Give lots of feedback``
    :Example:
       >>> import splat
       >>> spc = splat.getSpectrum(shortname='1507-1627')[0]
       >>> print splat.classifyByStandard(spc,string=True,method='kirkpatrick',plot=True)
       ('L4.5', 0.7138959194725174)
    '''
    verbose = kwargs.get('verbose',False)
    method = kwargs.get('method','')
    best_flag = kwargs.get('best',False)
    sptrange = kwargs.get('sptrange',[10,39])
    sptrange = kwargs.get('range',sptrange)
    if not isinstance(sptrange,list):
        sptrange = [sptrange,sptrange]
    if (isinstance(sptrange[0],str) != False):
        sptrange = [typeToNum(sptrange[0]),typeToNum(sptrange[1])]
    unc_sys = 0.5

# if you just want to compare to one standard
    cspt = kwargs.get('compareto',False)
    if (cspt != False):
        if (isinstance(cspt,str) == False):
            cspt = typeToNum(cspt)
# round off
        cspt = typeToNum(numpy.round(typeToNum(cspt)))
        mkwargs = copy.deepcopy(kwargs)
        mkwargs['compareto'] = False
        mkwargs['sptrange'] =[cspt,cspt]
        return classifyByStandard(sp,**mkwargs)
            
#    stdsptnum = numpy.arange(30)+10.
#    stdsptstr = ['M'+str(n) for n in numpy.arange(10)]
#    stdsptstr.append(['L'+str(n) for n in numpy.arange(10)])
#    stdsptstr.append(['T'+str(n) for n in numpy.arange(10)])

    if (method == 'kirkpatrick'):
        comprng = [0.9,1.4]*u.micron         # as prescribed in Kirkpatrick et al. 2010, ApJS, 
    else:
        comprng = [0.7,2.45]*u.micron       # by default, compare whole spectrum

# which comparison statistic to use
    if numpy.isnan(numpy.median(sp.noise)):
        compstat = 'stddev_norm'
    else:
        compstat = 'chisqr'

# compute fitting statistics
    stat = []
    sspt = []
    sfile = []
    for t in numpy.arange(sptrange[0],sptrange[1]+1):
        spstd = Spectrum(file=spex_stdfiles[typeToNum(t)])
        chisq,scale = compareSpectra(sp,spstd,fit_ranges=[comprng],stat=compstat,novar2=True)
        stat.append(chisq)
        sspt.append(t)
        sfile.append(spex_stdfiles[typeToNum(t)])
        if (verbose):
            print spex_stdfiles[typeToNum(t)], typeToNum(t), chisq, scale

# list of sorted standard files and spectral types
    sorted_stdfiles = [x for (y,x) in sorted(zip(stat,sfile))]
    sorted_stdsptnum = [x for (y,x) in sorted(zip(stat,sspt))]

# select either best match or an ftest-weighted average
    if (best_flag or len(stat) == 1):
        sptn = sorted_stdsptnum[0]
        sptn_e = unc_sys
    else:
        try:
            st = stat.value
        except:
            st = stat
        if numpy.isnan(numpy.median(sp.noise)):
            mean,var = weightedMeanVar(sspt,st)
        else:
            mean,var = weightedMeanVar(sspt,st,method='ftest',dof=sp.dof)        
        if (var**0.5 < 1.):
            sptn = numpy.round(mean*2)*0.5
        else:
            sptn = numpy.round(mean)
        sptn_e = (unc_sys**2+var)**0.5

# string or not?
    if (kwargs.get('string', True) == True):
        spt = typeToNum(sptn,uncertainty=sptn_e)
    else:
        spt = sptn

# plot spectrum compared to best spectrum
    if (kwargs.get('plot',False) != False):
        spstd = Spectrum(file=sorted_stdfiles[0])
        chisq,scale = compareSpectra(sp,spstd,fit_ranges=[comprng],stat=compstat)
        spstd.scale(scale)
        plotSpectrum(sp,spstd,colors=['k','r'],\
            title=sp.name+' vs '+typeToNum(sorted_stdsptnum[0])+' Standard',**kwargs)

    return spt, sptn_e
    

def classifyByTemplate(sp, *args, **kwargs):
    '''
    :Purpose: Determine the spectral type and uncertainty for a 
                spectrum by direct comparison to a large set of spectra in
                the library. One can select down the spectra by using the set
                command. Returns the best match or an F-test weighted mean and 
                uncertainty. There is an option to follow  the procedure of 
                Kirkpatrick et al. (2010), fitting only in the 0.9-1.4 micron 
                region. 
    :Usage: result = splat.classifyByTemplate(sp, \*args, \**kwargs)
    :Output: result is a dictionary containing the following keys:
                    - 'result = (Spectral Type, Spectral Type Uncertainty)
                    - 'chisquare' = array of nbest chi-square values
                    - 'name' = array of nbest source names
                    - 'scale' = array of nbest optimal scale factors
                    - 'spectra' = array of nbest Spectrum objects
                    - 'spt' = array of nbest spectral types
                
    :param sp: Spectrum class object, which should contain wave, flux and 
                 noise array elements.
    :param 'best': (optional, default = False) return only the best fit template type``
                    - ``'plot' = False: generate a plot comparing best fit standard to source, can be save to a file using the file keyword``
                    - ``'file' = '': output spectrum plot to a file``
                    - ``'method' = '': set to 'kirkpatrick' to follow the Kirkpatrick et al. (2010) method, fitting only to the 0.9-1.4 micron band``
                    - ``'nbest' = 1: number of best fitting spectra to return
                    - ``'select' = '': string defining which spectral template set you want to compare to; several options which can be combined:``
                        * ``'m dwarf': fit to M dwarfs only``
                        * ``'l dwarf': fit to M dwarfs only``
                        * ``'t dwarf': fit to M dwarfs only``
                        * ``'vlm': fit to M7-T9 dwarfs``
                        * ``'optical': only optical classifications``
                        * ``'high sn': median S/N greater than 100``
                        * ``'young': only young/low surface gravity dwarfs``
                        * ``'companion': only companion dwarfs``
                        * ``'subdwarf': only subdwarfs``
                        * ``'single': only dwarfs not indicated a binaries``
                        * ``'spectral binaries': only dwarfs indicated to be spectral binaries``
                        * ``'standard': only spectral standards (use classifyByStandard instead)``
                    - ``'string' = True: return spectral type as a string``
                    - ``'spt_type' = 'literature': specify which spectral classification type to return; can be 'spex', 'opt', 'nir', or 'lit'
                    - ``'verbose' = False: Give lots of feedback``
    :Example:
       >>> import splat
       >>> spc = splat.getSpectrum(shortname='1507-1627')[0]
       >>> print splat.classifyByTemplate(spc,string=True,set='l dwarf, high sn', spt_type='spex', plot=True)
       ('L4.5', 0.7138959194725174)
    '''

#
    spt_type = kwargs.get('spt_type','literature')
    spt_range = kwargs.get('spt_range',[10.,39.9])
    spt_range = kwargs.get('spt',spt_range)
    nbest = kwargs.get('nbest',1)
    verbose = kwargs.get('verbose',False)
    published = kwargs.get('published','')
    set = kwargs.get('select','')
#   placeholder for a systematic uncertainty term
    unc_sys = 0.
    if (kwargs.get('method','') == 'kirkpatrick'):
        comprng = [0.9,1.4]*u.micron         # as prescribed in Kirkpatrick et al. 2010, ApJS, 
    else:
        comprng = [0.7,2.45]*u.micron       # by default, compare whole spectrum

#  canned searches
#  constrain spectral types
    if ('lit' in spt_type.lower()):
        spt_type = 'LIT_TYPE'
    elif ('opt' in spt_type.lower() or 'optical' in set):
        spt_type = 'OPT_TYPE'
    elif ('nir' in spt_type.lower()):
        spt_type = 'NIR_TYPE'
    else:
        spt_type = 'LIT_TYPE'

    if ('m dwarf' in set.lower()):
        spt_range = [10,19.9]
    if ('l dwarf' in set.lower()):
        spt_range = [20,29.9]
    if ('t dwarf' in set.lower()):
        spt_range = [30,39.9]
    if ('vlm' in set.lower()):
        spt_range = [numpy.max([17,spt_range[0]]),numpy.min([39.9,spt_range[-1]])]
    
#  constrain S/N
    snr = 0.
    if ('high sn' in set.lower()):
        snr = 100.
    snr = kwargs.get('snr',snr)
    
#  don't compare to same spectrum
    try:
        excludefile = [sp.filename]
    except:
        excludefile = []
    if kwargs.get('excludefile',False) != False:
        e = kwargs.get('excludefile')
        if isinstance(e,list):
            excludefile.extend(e)
        else:
            excludefile.append(e)
    try:
        excludekey = [sp.data_key]
    except:
        excludekey = []
    if kwargs.get('excludekey',False) != False:
        e = kwargs.get('excludekey')
        if isinstance(e,list):
            excludekey.extend(e)
        else:
            excludekey.append(e)
    try:
        excludeshortname = [sp.shortname]
    except:
        excludeshortname = []
    if kwargs.get('excludeshortname',False) != False:
        e = kwargs.get('excludeshortname')
        if isinstance(e,list):
            excludeshortname.extend(e)
        else:
            excludeshortname.append(e)
#    print excludefile, excludekey, excludeshortname
    
# other classes
    giant = ''
    if 'giant' in set.lower():
        giant = True
    if 'not giant' in set.lower():
        giant = False
    companion = ''
    if 'companion' in set.lower():
        companion = True
    if 'not companion' in set.lower():
        companion = False
    young = ''
    if 'young' in set.lower():
        young = True
    if 'not young' in set.lower():
        young = False
    binary = ''
    if 'binary' in set.lower():
        binary = True
    if 'not binary' in set.lower():
        binary = False
    spbinary = ''
    if 'spectral binary' in set.lower():
        spbinary = True
    if 'not spectral binary' in set.lower():
        spbinary = False
    
    lib = searchLibrary(excludefile=excludefile,excludekey=excludekey,excludeshortname=excludeshortname, \
        snr=snr,spt_type=spt_type,spt_range=spt_range,published=published, \
        giant=giant,companion=companion,young=young,binary=binary,spbinary=spbinary,output='all',logic='and')
        
#    print [x for x in compsp]
#    elif ('companion' in set):
#        lib = searchLibrary(output='all',excludefile=excludefile,snr=snr,spt=spt,companion=True,published=published,giant=False,logic='and')
#    elif ('young' in set):
#        lib = searchLibrary(output='all',excludefile=excludefile,snr=snr,spt=spt,young=True,published=published,logic='and')
#    elif ('subdwarf' in set):
#        lib = searchLibrary(output='all',excludefile=excludefile,snr=snr,spt=spt,subdwarf=True,published=published,logic='and')
#    elif ('single' in set):
#        lib = searchLibrary(output='all',excludefile=excludefile,snr=snr,spt=spt,spbinary=False,published=published,binary=False,giant=False,logic='and')
#    elif ('spectral binaries' in set):
#        lib = searchLibrary(output='all',excludefile=excludefile,snr=snr,spt=spt,spbinary=True,published=published,logic='and')
#    elif (set != ''):
#        lib = searchLibrary(output='all',excludefile=excludefile,published=published,snr=snr,spt=spt)
#    else:
#        lib = searchLibrary(output='all',excludefile=excludefile,published=published,**kwargs)

#    lib = lib[:][numpy.where(lib[sptref] != '')]
        
# first search for the spectra desired - parameters are set by user
    if len(lib) == 0:
        print '\nNo templates available for comparison\n\n'
        return numpy.nan, numpy.nan

    files = lib['DATA_FILE']
    dkey = lib['DATA_KEY']
    sspt = [typeToNum(s) for s in lib[spt_type]]

    if (verbose):
        print '\nComparing to {} templates\n\n'.format(len(files))
    if len(files) > 100:
        print '\nComparing to {} templates\n\n'.format(len(files))
        print 'This may take some time!\n\n'.format(len(files))

# do comparison
    stat = []
    scl = []
    for i,d in enumerate(dkey):
        s = Spectrum(idkey=d)
        chisq,scale = compareSpectra(sp,s,fit_ranges=[comprng],stat='chisqr',novar2=True)
        stat.append(chisq)
        scl.append(scale)
        if (verbose):
            print keySpectrum(d)['NAME'][0], typeToNum(sspt[i]), chisq, scale
        
# list of sorted standard files and spectral types
    sorted_dkey = [x for (y,x) in sorted(zip(stat,dkey))]
    sorted_spt = [x for (y,x) in sorted(zip(stat,sspt))]
    sorted_scale = [x for (y,x) in sorted(zip(stat,scl))]

# select either best match or an ftest-weighted average
    if (kwargs.get('best',False) or len(stat) == 1):
        sptn = sorted_spt[0]
        sptn_e = unc_sys
    else:
        mean,var = weightedMeanVar(sspt,stat,method='ftest',dof=sp.dof)
# allow 1/2 subtypes if uncertainty is less than 1.0
        if (var**0.5 < 1.):
            sptn = numpy.round(mean*2.)*0.5
        else:
            sptn = numpy.round(mean)
        sptn_e = (unc_sys**2+var)**0.5

# plot spectrum compared to best spectrum
    if (kwargs.get('plot',False) != False):
        s = Spectrum(idkey=sorted_dkey[0])
#        chisq,scale = compareSpectra(s,sp,fit_ranges=[comprng],stat='chisqr',novar2=True)
        s.scale(sorted_scale[0])
        plotSpectrum(sp,s,colors=['k','r'],title=sp.name+' vs '+s.name,**kwargs)

# string or not?
    if (kwargs.get('string', True) == True):
        spt = typeToNum(sptn,uncertainty=sptn_e)
    else:
        spt = sptn

# return dictionary of results
    return {'result': (spt,sptn_e), \
        'chisquare': sorted(stat)[0:nbest], 'spt': sorted_spt[0:nbest], 'scale': sorted_scale[0:nbest], \
        'name': [keySpectrum(d)['NAME'][0] for d in sorted_dkey[0:nbest]], \
        'spectra': [Spectrum(idkey=d) for d in sorted_dkey[0:nbest]]}

 

def classifyGravity(sp, *args, **kwargs):
    '''Determine the gravity classification of a brown dwarf
    using the method of Allers & Liu 2013'''
    
    verbose = kwargs.get('verbose',False)
    
# Chart for determining gravity scores based on gravity sensitive 
# indices as described in the Allers and Liu paper.
# The key to the overall indices dictionary is each index name.
# The key to each index dictionary are the spectral types, which 
# contain the limits for each gravity score.
# To access a value do the following: print grav['FeH-z']['M5'][0] 
# which should return 'nan'
    
# Note: alternate method is Canty et al. (2013, MNRAS, 435, 2650)
# H2(K) index: median[2.16-2.18]/median[2.23-2.25]
   
    grav = {\
        'FeH-z':{'M5.0':[numpy.nan,numpy.nan],'M6.0':[1.068,1.039],'M7.0':[1.103,1.056],'M8.0':[1.146,1.074],'M9.0': [1.167,1.086],'L0.0': [1.204,1.106],'L1.0':[1.252,1.121],'L2.0':[1.298,1.142],'L3.0': [1.357,1.163],'L4.0': [1.370,1.164],'L5.0': [1.258,1.138],'L6.0': [numpy.nan,numpy.nan],'L7.0': [numpy.nan,numpy.nan]},\
        'VO-z': {'M5.0':[numpy.nan,numpy.nan],'M6.0':[numpy.nan,numpy.nan],'M7.0': [numpy.nan,numpy.nan],'M8.0': [numpy.nan,numpy.nan],'M9.0': [numpy.nan,numpy.nan],'L0.0': [1.122,1.256],'L1.0': [1.112,1.251],'L2.0': [1.110,1.232],'L3.0': [1.097,1.187],'L4.0': [1.073,1.118],'L5.0': [numpy.nan,numpy.nan],'L6.0': [numpy.nan,numpy.nan],'L7.0': [numpy.nan,numpy.nan]},\
        'KI-J': {'M5.0': [numpy.nan,numpy.nan], 'M6.0': [1.042,1.028], 'M7.0': [1.059,1.036],'M8.0': [1.077,1.046],'M9.0': [1.085,1.053],'L0.0': [1.098,1.061],'L1.0': [1.114,1.067],'L2.0': [1.133,1.073],'L3.0': [1.135,1.075],'L4.0': [1.126,1.072],'L5.0': [1.094,1.061],'L6.0': [numpy.nan,numpy.nan],'L7.0': [numpy.nan,numpy.nan]},\
        'H-cont': {'M5.0': [numpy.nan,numpy.nan], 'M6.0': [.988,.994], 'M7.0': [.981,.990],'M8.0': [.963,.984],'M9.0': [.949,.979],'L0.0': [.935,.972],'L1.0': [.914,.968],'L2.0': [.906,.964],'L3.0': [.898,.960],'L4.0': [.885,.954],'L5.0': [.869,.949],'L6.0': [.874,.950],'L7.0': [numpy.nan,numpy.nan]}}

# Calculate Allers indices and their uncertainties 
    ind = kwargs.get('indices',False)
    if ind == False:
        ind = measureIndexSet(sp,set='allers')

# Determine the object's NIR spectral type and its uncertainty 
    sptn = kwargs.get('spt',False)
    if sptn == False:
        sptn, spt_e = classifyByIndex(sp,string=False,set='allers')
        if numpy.isnan(sptn):
            print 'Spectral type could not be determined from indices'
            return numpy.nan
    if isinstance(sptn,str):
        sptn = typeToNum(sptn)
    Spt = typeToNum(numpy.floor(sptn))

#Check whether the NIR SpT is within gravity sensitive range values
    if ((sptn < 16.0) or (sptn > 27.0)):
        print 'Spectral type '+typeToNum(sptn)+' outside range for gravity classification'
        return numpy.nan

#Creates an empty array with dimensions 4x1 to fill in later with 5 gravscore values
    gravscore = {}
    medgrav = []

# Use the spt to pick the column that contains the 
# values we want to compare our indices with. 
    for k in grav.keys():
        val = 0.0
        if k == 'VO-z' or k=='H-cont':
            if numpy.isnan(grav[k][Spt][0]):
                val = numpy.nan
            if ind[k][0] >= grav[k][Spt][0]:
                val = 1.0
            if ind[k][0] >= grav[k][Spt][1]:
                val = 2.0
            if verbose:
                print k,ind[k][0], ind[k][1], val 
        if k == 'FeH-z' or k=='KI-J':
            if numpy.isnan(grav[k][Spt][0]):
                val = numpy.nan
            if ind[k][0] <= grav[k][Spt][0]:
                val = 1.0
            if ind[k][0] <= grav[k][Spt][1]:
                val = 2.0
            if verbose:
                print k,ind[k][0], ind[k][1], val 
        gravscore[k] = val
        medgrav.append(val)

# determine median score, or mean if even					
    if (len(numpy.where(numpy.isnan(medgrav) == False))%2 == 0):
        gravscore['score'] = scipy.stats.nanmean(medgrav)        
    else:        
        gravscore['score'] = scipy.stats.nanmedian(medgrav)        

    if gravscore['score'] <= 0.5:
       gravscore['gravity_class'] = 'FLD-G'
    elif gravscore['score'] > 0.5 and gravscore['score'] < 1.5:
       gravscore['gravity_class'] = 'INT-G'
    elif gravscore['score'] >= 1.5:
       gravscore['gravity_class'] = 'VL-G'

# plot spectrum against standard
    if (kwargs.get('plot',False) != False):
        spt,unc = classifyByStandard(sp,compareto=Spt,method='kirkpatrick',**kwargs)
        
# return gravity class or entire dictionary
    if (kwargs.get('allscores',False) == False):
        return gravscore['gravity_class']
    else:
        return gravscore

    
    
def compareSpectra(sp1, sp2, *args, **kwargs):
    '''Compare two spectra against each other'''
    weights = kwargs.get('weights',numpy.zeros(len(sp1.wave)))
    mask = kwargs.get('mask',numpy.zeros(len(sp1.wave)))    # mask = 1 -> ignore
    fit_ranges = kwargs.get('fit_ranges',[spex_wave_range])
    mask_ranges = kwargs.get('mask_ranges',[])
    if ~isinstance(fit_ranges[0],astropy.units.quantity.Quantity):
        mask_ranges*=u.micron
    mask_telluric = kwargs.get('mask_telluric',False)
    mask_standard = kwargs.get('mask_standard',False)
    var_flag = kwargs.get('novar2',True)
    stat = kwargs.get('stat','chisqr')
    minreturn = 1.e-9
    if ~isinstance(fit_ranges[0],astropy.units.quantity.Quantity):
        fit_ranges*=u.micron
    
    if (mask_standard == True):
        mask_telluric == True
        
# create interpolation function for second spectrum
    f = interp1d(sp2.wave,sp2.flux,bounds_error=False,fill_value=0.)
    if var_flag:
        v = interp1d(sp2.wave,sp2.variance*numpy.nan,bounds_error=False,fill_value=numpy.nan)
    else:        
        v = interp1d(sp2.wave,sp2.variance,bounds_error=False,fill_value=numpy.nan)
    
# total variance - funny form to cover for nans
    vtot = numpy.nanmax([sp1.variance.value,sp1.variance.value+v(sp1.wave.value)],axis=0)
 #   vtot = sp1.variance
    
# Mask certain wavelengths
# telluric absorption
    if (mask_telluric):
        mask_ranges.append([0.,0.65]*u.micron)        # meant to clear out short wavelengths
        mask_ranges.append([1.35,1.42]*u.micron)
        mask_ranges.append([1.8,1.92]*u.micron)
        mask_ranges.append([2.45,99.]*u.micron)        # meant to clear out long wavelengths

    if (mask_standard):
        mask_ranges.append([0.,0.8]*u.micron)        # standard short cut
        mask_ranges.append([2.35,99.]*u.micron)        # standard long cut

    for ranges in mask_ranges:
        mask[numpy.where(((sp1.wave >= ranges[0]) & (sp1.wave <= ranges[1])))] = 1

# set the weights    
    for ranges in fit_ranges:
        weights[numpy.where(((sp1.wave >= ranges[0]) & (sp1.wave <= ranges[1])))] = 1
     
# mask flux < 0
    mask[numpy.where(numpy.logical_or(sp1.flux < 0,f(sp1.wave) < 0))] = 1

    weights = weights*(1.-mask)

# comparison statistics

# switch to standard deviation if no uncertainty
    if numpy.isnan(numpy.nanmax(vtot)):
        stat = 'stddev'

# chi^2
    if (stat == 'chisqr'):
# compute scale factor    
        scale = numpy.nansum(weights*sp1.flux.value*f(sp1.wave)/vtot)/ \
            numpy.nansum(weights*f(sp1.wave)*f(sp1.wave)/vtot)
# correct variance
        vtot = numpy.nanmax([sp1.variance.value,sp1.variance.value+v(sp1.wave)*scale**2],axis=0)
        stat = numpy.nansum(weights*(sp1.flux.value-f(sp1.wave)*scale)**2/vtot)
        unit = sp1.funit/sp1.funit

# normalized standard deviation
    elif (stat == 'stddev_norm'):
# compute scale factor    
        scale = numpy.nansum(weights*sp1.flux.value)/ \
            numpy.nansum(weights*f(sp1.wave))
# correct variance
        stat = numpy.nansum(weights*(sp1.flux.value-f(sp1.wave)*scale)**2)/ \
            numpy.median(sp1.flux.value)**2
        unit = sp1.funit/sp1.funit

# standard deviation
    elif (stat == 'stddev'):
# compute scale factor    
        scale = numpy.nansum(weights*sp1.flux.value*f(sp1.wave))/ \
            numpy.nansum(weights*f(sp1.wave)*f(sp1.wave))
# correct variance
        stat = numpy.nansum(weights*(sp1.flux.value-f(sp1.wave)*scale)**2)
        unit = sp1.funit**2

# absolute deviation
    elif (stat == 'absdev'):
# compute scale factor    
        scale = numpy.nansum(weights*sp1.flux.value)/ \
            numpy.nansum(weights*f(sp1.wave))
# correct variance
        stat = numpy.nansum(weights*abs(sp1.flux.value-f(sp1.wave)*scale))
        unit = sp1.funit

# error
    else:
        print 'Error: statistic {} for compareSpectra not available'.format(stat)
        return numpy.nan, numpy.nan

# plot spectrum compared to best spectrum
    if (kwargs.get('plot',False) != False):
        spcomp = sp2.copy()
        spcomp.scale(scale)
        kwargs['colors'] = kwargs.get('colors',['k','r'])
        kwargs['title'] = kwargs.get('title',sp1.name+' vs '+sp2.name)
        plotSpectrum(sp1,spcomp,**kwargs)

    return numpy.nanmax([stat,minreturn])*unit, scale
        

def coordinateToDesignation(c):
    '''Convert RA, Dec into designation string'''
# input is ICRS
    if isinstance(c,SkyCoord):
        cc = c
    else:
        cc = properCoordinates(c)
# input is [RA,Dec] pair in degrees
    return string.replace('J{0}{1}'.format(cc.ra.to_string(unit=u.hour, sep='', precision=2, pad=True), \
        cc.dec.to_string(unit=u.degree, sep='', precision=1, alwayssign=True, pad=True)),'.','')


def dateToCaldate(d):
    '''Convert from numeric date to calendar date'''
    return d[:4]+' '+months[int(d[5:6])-1]+' '+d[-2:]


def designationToCoordinate(value, **kwargs):
    '''Convert a designation into a RA, Dec tuple or ICRS'''
    icrsflag = kwargs.get('icrs',True)

    a = re.sub('[j.:hms]','',value.lower())
    fact = 1.
    spl = a.split('+')
    if len(spl) == 1:
        spl = a.split('-')
        fact = -1.
    ra = 15.*float(spl[0][0:2])
    if (len(spl[0]) > 2):
        ra+=15.*float(spl[0][2:4])/60.
    if (len(spl[0]) > 4):
        ra+=15.*float(spl[0][4:6])/3600.
    if (len(spl[0]) > 6):
        ra+=15.*float(spl[0][6:8])/360000.
    dec = float(spl[1][0:2])
    if (len(spl[0]) > 2):
        dec+=float(spl[1][2:4])/60.
    if (len(spl[0]) > 4):
        dec+=float(spl[1][4:6])/3600.
    if (len(spl[1]) > 6): 
        dec+=float(spl[1][6:8])/360000.
    dec = dec*fact
    if icrsflag:
        return SkyCoord(ra=ra*u.degree, dec=dec*u.degree, frame='icrs')
    else:
        return [ra,dec]


def designationToShortName(value):
    '''Produce a shortened version of designation'''
    if isinstance(value,str):
        a = re.sub('[j.:hms]','',value.lower())
        mrk = '+'
        spl = a.split(mrk)
        if len(spl) == 1:
            mrk = '-'
            spl = a.split(mrk)
        if len(spl) == 2:
            return 'J'+spl[0][0:4]+mrk+spl[1][0:4]
        else:
            return value
    else:
        raise ValueError('\nMust provide a string value for designation\n\n')

        

def fetchDatabase(*args, **kwargs):    
    '''Get the SpeX Database from either online repository or local drive'''
    kwargs['filename'] = kwargs.get('filename',ORIGINAL_DB)
    kwargs['filename'] = kwargs.get('file',kwargs['filename'])
    kwargs['folder'] = kwargs.get('folder',DB_FOLDER)
    url = kwargs.get('url',SPLAT_URL)+kwargs['folder']
    local = kwargs.get('local',True)
    online = kwargs.get('online',not local and checkOnline())
    local = not online
    kwargs['local'] = local
    kwargs['online'] = online
    kwargs['model'] = True

# check that folder/set is present either locally or online
# if not present locally but present online, switch to this mode
# if not present at either raise error
    folder = checkLocal(kwargs['folder'])
    if folder=='':
        folder = checkOnline(kwargs['folder'])
        if folder=='':
            raise NameError('\nCould not find '+kwargs['folder']+' locally or on SPLAT website\n\n')
        else:
            kwargs['folder'] = folder
            kwargs['local'] = False
            kwargs['online'] = True
    else:
        kwargs['folder'] = folder

# locally:
    if kwargs['local']:
        file = checkLocal(kwargs['filename'])
        if file=='':
            file = checkLocal(kwargs['folder']+'/'+kwargs['filename'])
        if file=='':
            raise NameError('\nCould not find '+kwargs['filename']+' locally\n\n')
        else:
            data = ascii.read(file, delimiter='\t',fill_values='-99.',format='tab')

# check if file is present; if so, read it in, otherwise go to interpolated
# online:
    if kwargs['online']:
        file = checkOnline(kwargs['filename'])
        if file=='':
            file = checkOnline(kwargs['folder']+'/'+kwargs['filename'])
        if file=='':
            raise NameError('\nCould not find '+kwargs['filename']+' on the SPLAT website\n\n')
        try:
            open(os.path.basename(TMPFILENAME), 'wb').write(urllib2.urlopen(url+file).read()) 
            kwargs['filename'] = os.path.basename(tmp)
            data = ascii.read(os.path.basename(TMPFILENAME), delimiter='\t',fill_values='-99.',format='tab')
            os.remove(os.path.basename(TMPFILENAME))
        except urllib2.URLError:
            raise NameError('\nHaving a problem reading in '+kwargs['filename']+' on the SPLAT website\n\n')


# clean up blanks and convert numerical values to numbers
    data['RA'][numpy.where(data['RA'] == '')] = '0.'
#    data['ran'] = [float(x) for x in data['ra']]
    data['DEC'][numpy.where(data['DEC'] == '')] = '0.'
#    data['decn'] = [float(x) for x in data['dec']]
    data['2MASS_J'][numpy.where(data['2MASS_J'] == '')] = '99.'
#    data['jmagn'] = [float(x) for x in data['jmag']]
    data['2MASS_H'][numpy.where(data['2MASS_H'] == '')] = '99.'
#    data['hmagn'] = [float(x) for x in data['hmag']]
    data['2MASS_KS'][numpy.where(data['2MASS_KS'] == '')] = '99.'
#    data['kmagn'] = [float(x) for x in data['kmag']]
    data['2MASS_J_UNC'][numpy.where(data['2MASS_J_UNC'] == '')] = '99.'
#    data['jmag_errorn'] = [float(x) for x in data['jmag_error']]
    data['2MASS_H_UNC'][numpy.where(data['2MASS_H_UNC'] == '')] = '99.'
#    data['hmag_errorn'] = [float(x) for x in data['hmag_error']]
    data['2MASS_KS'][numpy.where(data['2MASS_KS_UNC'] == '')] = '99.'
#    data['kmag_errorn'] = [float(x) for x in data['kmag_error']]
    data['RESOLUTION'][numpy.where(data['RESOLUTION'] == '')] = '120'
#    data['resolutionn'] = [float(x) for x in data['resolution']]
    data['AIRMASS'][numpy.where(data['AIRMASS'] == '')] = '1.'
#    data['airmassn'] = [float(x) for x in data['airmass']]
    data['MEDIAN_SNR'][numpy.where(data['MEDIAN_SNR'] == '')] = '0'
#    data['median_snrn'] = [float(x) for x in data['median_snr']]

# convert coordinates to SkyCoord format
#    data['skycoords'] = data['ra']
    s = []
    for i in numpy.arange(len(data['RA'])):
        try:        # to deal with a blank string
            s.append(SkyCoord(ra=float(data['RA'][i])*u.degree,dec=float(data['DEC'][i])*u.degree,frame='icrs'))
        except:
            s.append(SkyCoord(ra=0.*u.degree,dec=0.*u.degree,frame='icrs'))
    data['SKYCOORDS'] = s

# add in RA/Dec (TEMPORARY)
#    ra = []
#    dec = []
#    for x in data['designation']:
#        c = designationToCoordinate(x,ICRS=False)
#        ra.append(c[0])
#        dec.append(c[1])
#    data['ra'] = ra
#    data['dec'] = dec

    data['YOUNG'] = ['young' in x for x in data['LIBRARY']]
    data['SUBDWARF'] = ['subdwarf' in x for x in data['LIBRARY']]
    data['BINARY'] = ['binary' in x for x in data['LIBRARY']]
    data['SPBINARY'] = ['sbinary' in x for x in data['LIBRARY']]
    data['BLUE'] = ['blue' in x for x in data['LIBRARY']]
    data['RED'] = ['red' in x for x in data['LIBRARY']]
    data['GIANT'] = ['giant' in x for x in data['LIBRARY']]
    data['WD'] = ['wd' in x for x in data['LIBRARY']]
    data['STANDARD'] = ['std' in x for x in data['LIBRARY']]
    data['COMPANION'] = ['companion' in x for x in data['LIBRARY']]

# add in shortnames
    data['SHORTNAME'] = [designationToShortName(x) for x in data['DESIGNATION']]

# create literature spt 
    data['LIT_TYPE'] = data['OPT_TYPE']
    w = numpy.where(numpy.logical_and(data['LIT_TYPE'] == '',data['NIR_TYPE'] != ''))
    data['LIT_TYPE'][w] = data['NIR_TYPE'][w]
    sptn = [typeToNum(x) for x in data['LIT_TYPE']]
    w = numpy.where(numpy.logical_and(sptn > 29.,data['NIR_TYPE'] != ''))
    data['LIT_TYPE'][w] = data['NIR_TYPE'][w]
#    w = numpy.where(numpy.logical_and(data['lit_type'] == '',typeToNum(data['spex_type']) > 17.))
#    data['lit_type'][w] = data['spex_type'][w]

    return data


# DEPRECATED
#def filenameToNameDate(filename):
#    '''Extract from a SPLAT filename the source name and observation date'''
#    ind = filename.rfind('.')
#    base = filename[:ind]
#    spl = base.split('_')
#    if (len(spl) < 2):
#        return '', ''
#    else:
#        name = spl[-2]
#        d = spl[-1]
#        try:
#            float(d)
#            date = '20'+d
#        except ValueError:
#            print filename+' does not contain a date'
#            date = ''
#        
#        return name, date
#


def filterMag(sp,filter,*args,**kwargs):
    '''
    :Purpose: ``Determine the photometric magnitude of a source based on the
                spectrum. Spectra are convolved with the filter specified by
                the 'filter' input.  By default this filter is also 
                convolved with a model of Vega to extract Vega magnitudes,
                but the user can also specify AB magnitudes, photon flux or
                energy flux.``
    :Usage: ``mag,unc = splat.filterMag(sp, 'filter name',\*args, \**kwargs)``
    :param sp: ``Spectrum class object, which should contain wave, flux and 
                 noise array elements.``
    :param 'filter mag': ``Name of filter, must be one of the following:``
                    - ``'2MASS J', '2MASS H', '2MASS Ks'``
                    - ``'MKO J', 'MKO H', 'MKO K', MKO Kp', 'MKO Ks'``
                    - ``'NICMOS F090M', 'NICMOS F095N', 'NICMOS F097N', 'NICMOS F108N',`` 
                    - ``'NICMOS F110M', 'NICMOS F110W', 'NICMOS F113N', 'NICMOS F140W',``
                    - ``'NICMOS F145M', 'NICMOS F160W', 'NICMOS F164N', 'NICMOS F165M',``
                    - ``'NICMOS F166N', 'NICMOS F170M', 'NICMOS F187N', 'NICMOS F190N'``
                    - ``'NIRC2 J', 'NIRC2 H', 'NIRC2 Kp', 'NIRC2 Ks'``
                    - ``'WIRC J', 'WIRC H', 'WIRC K', 'WIRC CH4S', 'WIRC CH4L'``
                    - ``'WIRC CO', 'WIRC PaBeta', 'WIRC BrGamma', 'WIRC Fe2'``
    :param \**kwargs (optional): - ``'info' = False: give the filter names available``
                    - ``'custom' = False: specify to a 2 x N vector array specifying the wavelengths and transmissions for a custom filter``
                    - ``'ab' = False: compute AB magnitudes``
                    - ``'vega' = True: compute Vega magnitudes``
                    - ``'energy' = False: compute energy flux``
                    - ``'photon' = False: compute photon flux``
                    - ``'filterFolder' = '': folder containing the filter transmission files``
                    - ``'vegaFile' = '': name of file containing Vega flux file, must be within 'filterFolder'``
                    - ``'nsamples' = 100: number of samples to use in MC error estimation``
    :Example:
       >>> import splat
       >>> spc = splat.getSpectrum(shortname='1507-1627')[0]
       >>> spc.fluxCalibrate('2MASS J',14.5)
       >>> print splat.filterMag(spc,'MKO J')
       (14.345894376898123, 0.027596454828421831)
    '''
# keyword parameters
    filterFolder = kwargs.get('filterFolder',SPLAT_PATH+FILTER_FOLDER)
    if not os.path.exists(filterFolder):
        filterFolder = SPLAT_URL+FILTERFOLDER
    vegaFile = kwargs.get('vegaFile','vega_kurucz.txt')
    info = kwargs.get('info',False)
    custom = kwargs.get('custom',False)
    vega = kwargs.get('vega',True)
    ab = kwargs.get('ab',False)
    photons = kwargs.get('photons',False)
    energy = kwargs.get('energy',False)
    nsamples = kwargs.get('nsamples',100)


# check that requested filter is in list
    f = filter.replace(' ','_')
    if (f not in filters.keys()):
        print 'Filter '+filter+' not included in filterMag'
        info = True
        
# print out what's available
    if (info):
        print 'Filter names:'
        for x in filters.keys():
            print x+': '+filters[x]['description']    
        return numpy.nan, numpy.nan

# Read in filter
    if (custom == False):
        fwave,ftrans = numpy.genfromtxt(filterFolder+filters[f]['file'], comments='#', unpack=True, \
            missing_values = ('NaN','nan'), filling_values = (numpy.nan))
    else:
        fwave,ftrans = custom[0],custom[1]
    fwave = fwave[~numpy.isnan(ftrans)]*u.micron   # temporary fix
    ftrans = ftrans[~numpy.isnan(ftrans)]
                
# interpolate spectrum onto filter wavelength function
    wgood = numpy.where(~numpy.isnan(sp.noise))
    if len(sp.wave[wgood]) > 0:
        d = interp1d(sp.wave[wgood],sp.flux[wgood],bounds_error=False,fill_value=0.)
        n = interp1d(sp.wave[wgood],sp.noise[wgood],bounds_error=False,fill_value=numpy.nan)
# catch for models
    else:
        print filter+': no good points'
        d = interp1d(sp.wave,sp.flux,bounds_error=False,fill_value=0.)
        n = interp1d(sp.wave,sp.flux*1.e-9,bounds_error=False,fill_value=numpy.nan)
        
    result = []
    if (vega):
# Read in Vega spectrum
        vwave,vflux = numpy.genfromtxt(filterFolder+vegaFile, comments='#', unpack=True, \
            missing_values = ('NaN','nan'), filling_values = (numpy.nan))
        vwave = vwave[~numpy.isnan(vflux)]*u.micron
        vflux = vflux[~numpy.isnan(vflux)]*(u.erg/(u.cm**2 * u.s * u.micron))
        vflux.to(sp.funit,equivalencies=u.spectral_density(vwave))
# interpolate Vega onto filter wavelength function
        v = interp1d(vwave,vflux,bounds_error=False,fill_value=0.)
        for i in numpy.arange(nsamples):
#            result.append(-2.5*numpy.log10(trapz(ftrans*numpy.random.normal(d(fwave),n(fwave))*sp.funit,fwave)/trapz(ftrans*v(fwave)*sp.funit,fwave)))
            result.append(-2.5*numpy.log10(trapz(ftrans*(d(fwave)+numpy.random.normal(0,1.)*n(fwave))*sp.funit,fwave)/trapz(ftrans*v(fwave)*sp.funit,fwave)))
        
    if (energy or photons):
        for i in numpy.arange(nsamples):
#            result.append(trapz(ftrans*numpy.random.normal(d(fwave),n(fwave))*sp.funit,fwave))
            result.append(trapz(ftrans*(d(fwave)+numpy.random.normal(0,1.)*n(fwave))*sp.funit,fwave))
        if (photons):
            convert = const.h.to('erg s')*const.c.to('micron/s')
            result = result/convert.value
    if (ab):
        fnu = fwave.to('Hz',equivalencies=u.spectral())
        fconst = 3631*u.jansky
        fconst = fconst.to(sp.fnunit,equivalencies=u.spectral())
        d = interp1d(sp.nu,sp.fnu,bounds_error=False,fill_value=0.)
        n = interp1d(sp.nu,sp.noise,bounds_error=False,fill_value=0.)
        b = trapz((ftrans/fnu)/fconst,fnu)
        for i in numpy.arange(nsamples):
            a = trapz(ftrans*(d(fnu)+numpy.random.normal(0,1)*n(fnu))*sp.fnunit/fnu,fnu)
            result.append(-2.5*numpy.log10(a/b))

    val = numpy.nanmean(result)
    err = numpy.nanstd(result)
    if len(sp.wave[wgood]) == 0:
        err = 0.
    return val,err


def getSpectrum(*args, **kwargs):
    '''
    :Purpose: ``Gets a spectrum from the SPLAT library using various selection criteria.``
    :Usage: ``[sp] = splat.getSpectrum({search commands},**kwargs)``
    :param [sp]: ``array of Spectrum class objects, each of which should contain wave, flux and 
                 noise array elements.``
    :param '{search commands}': ``Various search commands to winnow down the selection:
                    - **name**: search by source name (e.g., name='Gliese 570D')
                    - **shortname**: search be short name (e.g. shortname = 'J1457-2124')
                    - **designation**: search by full designation (e.g., designation = 'J11040127+1959217')
                    - **coordinate**: search around a coordinate by a radius specified by radius keyword (e.g., coordinate=[180.,+30.], radius=10.)
                    - **radius** = 10.: search radius in arcseconds for coordinate search
                    - **spt** or **spex_spt**: search by SpeX spectral type; single value is exact, two-element array gives range (e.g., spt = 'M7' or spt = [24,39])
                    - **opt_spt**: same as spt for literature optical spectral types
                    - **nir_spt**: same as spt for literature NIR spectral types
                    - **jmag, hmag, kmag**: select based on faint limit or range of J, H or Ks magnitudes (e.g., jmag = [12,15])
                    - **snr**: search on minimum or range of S/N ratios (e.g., snr = 30. or snr = [50.,100.])
                    - **young, subdwarf, binary, spbinary, red, blue, giant, wd, standard**: classes to search on (e.g., young=True)
                    - **logic** or **combine** = 'and': search logic, can be 'and' or 'or'
                    - **combine**: same as logic
                    - **date**: search by date (e.g., date = '20040322') or range of dates (e.g., date=[20040301,20040330])
                    - **reference**: search by list of references (bibcodes) (e.g., reference='2011ApJS..197...19K')
    :param \**kwargs (optional): 
                    - **sort** = True: sort results based on Right Ascension
                    - **list** = False: if True, return just a list of the data files (can be done with searchLibrary as well)
                    - **lucky** = False: if True, return one randomly selected spectrum from the selected sample
    :Example:
       >>> import splat
       >>> sp = splat.getSpectrum(shortname='1507-1627')[0]

          Retrieving 1 file

       >>> sparr = splat.getSpectrum(spt='M7')

          Retrieving 120 files

       >>> sparr = splat.getSpectrum(spt='T5',young=True)

		  No files match search criteria
		  
    '''

    result = []
    kwargs['output'] = 'all'
    search = searchLibrary(*args, **kwargs)

    if len(search) > 0:    
        files = []
        for i,x in enumerate(search['DATA_KEY']):
            files.append(str(search['DATA_KEY'][i])+'_'+str(search['SOURCE_KEY'][i])+'.fits')
            
# return just the filenames
        if (kwargs.get('list',False) != False):
            return files
    
        if (len(files) == 1):
            print '\nRetrieving 1 file\n'
            result.append(Spectrum(files[0],header=search[0]))
        else:
            if (kwargs.get('lucky',False) == True):
                print '\nRetrieving 1 lucky file\n'
                ind = random.choice(range(len(files)))
                result.append(Spectrum(files[ind],header=search[ind]))
            else:
                print '\nRetrieving {} files\n'.format(len(files))
                for i,x in enumerate(files):
                    result.append(Spectrum(x,header=search[i:i+1]))
        	
    else:
        if checkAccess() == False:
            sys.stderr.write('\nNo published files match search criteria\n\n')
        else:
            sys.stderr.write('\nNo files match search criteria\n\n')

    return result
        

# simple number checker
def isNumber(s):
    '''check if something is a number'''
    try:
        t = float(s)
        return (True and ~numpy.isnan(t))
    except ValueError:
        return False



def keySource(keys, **kwargs):
    '''keySource takes a source key and returns a table with the source information'''

# vectorize
    if isinstance(keys,list) == False:
        keys = [keys]

    sdb = ascii.read(SPLAT_PATH+DB_FOLDER+SOURCES_DB, delimiter='\t',fill_values='-99.',format='tab')
    sdb['SELECT'] = [x in keys for x in sdb['SOURCE_KEY']]

    if sum(sdb['SELECT']) == 0.:
        print 'No sources found with source key {}'.format(keys[0])
        return False
    else:
        db = sdb[:][numpy.where(sdb['SELECT']==1)]
        return db
   
    
def keySpectrum(keys, **kwargs):
    '''keySpectrum takes a spectrum key and returns a table with the spectrum and source information'''

# vectorize
    if isinstance(keys,list) == False:
        keys = [keys]

    sdb = ascii.read(SPLAT_PATH+DB_FOLDER+SPECTRA_DB, delimiter='\t',fill_values='-99.',format='tab')
    sdb['SELECT'] = [x in keys for x in sdb['DATA_KEY']]

    if sum(sdb['SELECT']) == 0.:
        print 'No spectra found with spectrum key {}'.format(keys[0])
        return False
    else:
        s2db = ascii.read(SPLAT_PATH+DB_FOLDER+SOURCES_DB, delimiter='\t',fill_values='-99.',format='tab')
        db = join(sdb[:][numpy.where(sdb['SELECT']==1)],s2db,keys='SOURCE_KEY')
        return db
   

def loadSpectrum(*args, **kwargs):
    '''deprecated'''
    if kwargs.get('file',False) != False:
        return Spectrum(**kwargs)
    if kwargs.get('filename',False) != False:
        return Spectrum(**kwargs)
    if kwargs.get('idkey',False) != False:
        return Spectrum(**kwargs)

# check primary argument
    if len(args) > 0:
        if isinstance(args[0],str):
            kwargs['filename'] = args[0]    
            return Spectrum(**kwargs)
        if isinstance(args[0],int):
            kwargs['idkey'] = args[0]    
            return Spectrum(**kwargs)

# couldn't find what you're looking for
    raise NameError('\nNo filename or idkey specified in loadSpectrum\n\n')
    return False


def estimateDistance(sp, **kwargs):
    '''Takes the apparent magnitude and either takes or determines the absolute magnitude, 
    then uses the magnitude/distance relation to estimate the distance to the object in parsecs
    Note: the input spectra should be flux calibrated to their empirical apparent magnitudes'''

    mag = kwargs.get('mag', False)
    mag_unc = kwargs.get('mag_unc', 0.)
    absmag = kwargs.get('absmag', False)
    absmag_unc = kwargs.get('absmag_unc', 0.)
    spt = kwargs.get('spt', False)
    spt_unc = kwargs.get('spt_e', 0.)
    nsamples = kwargs.get('nsamples', 100)
    filt = kwargs.get('filter', False)

# if no apparent magnitude then calculate from spectrum
    if (mag == False):
        if (filt == False):
            sys.stderr.write('\nPlease specify the filter used to determine the apparent magnitude\n')
            return numpy.nan, numpy.nan
        mag, mag_unc = filterMag(sp,filt)

# if no spt then calculate from spectrum
    if spt == False:
        spt, spt_unc = classifyByIndex(sp)


# if no absolute magnitude then estimate from spectral type
    if absmag == False:
        if filt == False:
            sys.stderr.write('\nPlease specify the filter used to determine the absolute magnitude\n')
            return numpy.nan, numpy.nan
        absmag, absmag_unc = typeToMag(spt,filt,unc=spt_unc)

# create Monte Carlo sets
    if mag_unc > 0.:
        mags = numpy.random.normal(mag, mag_unc, nsamples)
    else:
        mags = nsamples*[mag]

    if absmag_unc > 0.:
        absmags = numpy.random.normal(absmag, absmag_unc, nsamples)
    else:
        absmags = nsamples*[absmag]
 
# calculate 
    distances = 10.**(numpy.subtract(mags,absmags)/5. + 1.)
    d = numpy.mean(distances)
    unc = numpy.std(distances)
    
    return d, unc


def measureEW(sp, *args, **kwargs):
    '''Routine to measure equivalent widths (EWs) of specified lines'''

# presets
    nsamples = kwargs.get('nsamples',100)
    noiseFlag = kwargs.get('nonoise',False)

# predefined lines
    specline = kwargs.get('line','').replace(' ','').lower()
    if 'nai' in specline:
        if '2.2' in specline:
            wave_line = [2.2020, 2.2120]
            wave_cont = [2.1965, 2.2125, 2.2175]
    elif 'cai' in specline:
        if '2.2' in specline:
            wave_line = [2.2580, 2.2690]
            wave_cont = [2.2510, 2.2580, 2.2705, 2.2760]
    else:
        if len(args) < 2:
            print 'measureEW needs at least two wavelength arrays to measure line and continuum regions'
            return numpy.nan, numpy.nan
        else:
            wave_line = args[0]
            wave_cont = args[1]

    
# create interpolation routines
    w = numpy.where(numpy.isnan(sp.flux) == False)
    f = interp1d(sp.wave.value[w],sp.flux.value[w],bounds_error=False,fill_value=0.)
    w = numpy.where(numpy.isnan(sp.noise) == False)

# note that units are stripped out
    if (numpy.size(w) != 0):
        n = interp1d(sp.wave.value[w],sp.noise.value[w],bounds_error=False,fill_value=numpy.nan)
        noiseFlag = False or noiseFlag
    else:
        n = interp1d(sp.wave.value[:],sp.noise.value[:],bounds_error=False,fill_value=numpy.nan)
        noiseFlag = True or noiseFlag
    
    wLine = (numpy.arange(0,nsamples+1.0)/nsamples)* \
            (numpy.nanmax(wave_line)-numpy.nanmin(wave_line))+numpy.nanmin(wave_line)
    fLine = f(wLine)
    nLine = n(wLine)
    fCont = f(wave_cont)
    nCont = n(wave_cont)
    
    if noiseFlag == True:
#linear fit to continuum
        pCont = numpy.poly1d(numpy.polyfit(wave_cont,fCont,1))
        fContFit = pCont(wLine)
        ew = trapz((numpy.ones(len(fLine))-(fLine/fContFit)), wLine)*1e4 
        return ew*u.angstrom, numpy.nan
#monte carlo
    else:
        ew=[]
        for i in range(nsamples):
#generate simulated fluxes
#            fContVar = fCont+numpy.random.normal(0.,1.)*nCont
#            fLineVar = fLine+numpy.random.normal(0.,1.)*nLine
            fContVar = numpy.random.normal(fCont,nCont)
            fLineVar = numpy.random.normal(fLine,nLine)
        
#linear fit to continuum
            pCont = numpy.poly1d(numpy.polyfit(wave_cont,fContVar,1))
            fContFit = pCont(wLine)
            ew.append(trapz((numpy.ones(len(fLineVar))-(fLineVar/fContFit)), wLine)*1e4)

# some error checking
#            plt.plot(wLine,fContFit,color='r')
#            plt.plot(wLine,fLine,color='k')
#            plt.show()

# following line is more correct but having problem with output
#       return numpy.nanmean(ew)*u.angstrom, numpy.nanstd(ew)*u.angstrom
        return numpy.nanmean(ew), numpy.nanstd(ew)


def measureEWSet(sp,*args,**kwargs):
    set = kwargs.get('set','rojas')

# determine combine method
    if ('rojas' in set.lower()):
        reference = 'EW measures from Rojas-Ayala et al. (2012)'
        names = ['Na I 2.206/2.209','Ca I 2.26']
        ews = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        ews[0],errs[0] = measureEW(sp,[2.2020, 2.2120],[2.1965, 2.2125, 2.2175],**kwargs)
        ews[1],errs[1] = measureEW(sp,[2.2580, 2.2690],[2.2510, 2.2580, 2.2705, 2.2760],**kwargs)
    else:
        print '{} is not one of the sets used for measureIndexSet'.format(set)
        return numpy.nan

# output dictionary of indices
    result = {names[i]: (ews[i],errs[i]) for i in numpy.arange(len(names))}
    result['reference'] = reference
    result['names'] = names
#    result['reference'] = reference
#    return inds,errs,names

    return result


def measureIndex(sp,*args,**kwargs):
    '''Measure an index on a spectrum based on defined methodology
    measure method can be mean, median, integrate
    index method can be ratio = 1/2, valley = 1-2/3, OTHERS
    output is index value and uncertainty'''

# keyword parameters
    method = kwargs.get('method','ratio')
    sample = kwargs.get('sample','integrate')
    nsamples = kwargs.get('nsamples',100)
    noiseFlag = kwargs.get('nonoise',False)
            
# create interpolation functions
    w = numpy.where(numpy.isnan(sp.flux) == False)
    f = interp1d(sp.wave.value[w],sp.flux.value[w],bounds_error=False,fill_value=0.)
    w = numpy.where(numpy.isnan(sp.noise) == False)
# note that units are stripped out
    if (numpy.size(w) != 0):
        s = interp1d(sp.wave.value[w],sp.noise.value[w],bounds_error=False,fill_value=numpy.nan)
        noiseFlag = False
    else:
        s = interp1d(sp.wave.value[:],sp.noise.value[:],bounds_error=False,fill_value=numpy.nan)
        noiseFlag = True
                
# error checking on number of arguments provided
    if (len(args) < 2):
        print 'measureIndex needs at least two samples to function'
        return numpy.nan, numpy.nan
    elif (len(args) < 3 and (method == 'line' or method == 'allers' or method == 'inverse_line')):
        print method+' requires at least 3 sample regions'
        return numpy.nan, numpy.nan

# define the sample vectors
    values = numpy.zeros((len(args),nsamples))

# loop over all sampling regions
    for i,waveRng in enumerate(args):
        xNum = (numpy.arange(0,nsamples+1.0)/nsamples)* \
            (numpy.nanmax(waveRng)-numpy.nanmin(waveRng))+numpy.nanmin(waveRng)
        yNum = f(xNum)
        yNum_e = s(xNum)

# now do MonteCarlo measurement of value and uncertainty
        for j in numpy.arange(0,nsamples):

# sample variance
            if (numpy.isnan(yNum_e[0]) == False):
                yVar = yNum+numpy.random.normal(0.,1.)*yNum_e
# NOTE: I'M NOT COMFORTABLE WITH ABOVE LINE - SEEMS TO BE TOO COARSE OF UNCERTAINTY
# BUT FOLLOWING LINES GIVE UNCERTAINTIES THAT ARE WAY TOO SMALL
#                yVar = numpy.random.normal(yNum,yNum_e)
#                yVar = yNum+numpy.random.normal(0.,1.,len(yNum))*yNum_e
            else:
                yVar = yNum
            
# choose function for measuring indices
            if (sample == 'integrate'):
                values[i,j] = trapz(yVar,xNum)
            elif (sample == 'average'):
                values[i,j] = numpy.nanmean(yVar)
            elif (sample == 'median'):
                values[i,j] = numpy.median(yVar)
            elif (sample == 'maximum'):
                values[i,j] = numpy.nanmax(yVar)
            elif (sample == 'minimum'):
                values[i,j] = numpy.nanmin(yVar)
            else:
                values[i,j] = numpy.nanmean(yVar)

# compute index based on defined method
# default is a simple ratio
    if (method == 'ratio'):
        vals = values[0,:]/values[1,:]
    elif (method == 'line'):
        vals = 0.5*(values[0,:]+values[1,:])/values[2,:]
    elif (method == 'inverse_line'):
        vals = 2.*values[0,:]/(values[1,:]+values[2,:])
    elif (method == 'change'):
        vals = 2.*(values[0,:]-values[1,:])/(values[0,:]+values[1,:])
    elif (method == 'allers'):
        vals = (((numpy.mean(args[0])-numpy.mean(args[1]))/(numpy.mean(args[2])-numpy.mean(args[1])))*values[2,:] \
            + ((numpy.mean(args[2])-numpy.mean(args[0]))/(numpy.mean(args[2])-numpy.mean(args[1])))*values[1,:]) \
            /values[0,:]
    else:
        vals = values[0,:]/values[1,:]
            
# output mean, standard deviation
    if (noiseFlag):
        return numpy.nanmean(vals), numpy.nan
    else:
        return numpy.nanmean(vals), numpy.nanstd(vals)


# wrapper function for measuring specific sets of indices

def measureIndexSet(sp,**kwargs):

# keyword parameters
    set = kwargs.get('set','burgasser')

# determine combine method
    if ('burgasser' in set.lower()):
        reference = 'Indices from Burgasser et al. (2006)'
        refcode = 'BUR06'
        names = ['H2O-J','CH4-J','H2O-H','CH4-H','H2O-K','CH4-K','K-J']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[1.14,1.165],[1.26,1.285],method='ratio',sample='integrate',**kwargs)
        inds[1],errs[1] = measureIndex(sp,[1.315,1.335],[1.26,1.285],method='ratio',sample='integrate',**kwargs)
        inds[2],errs[2] = measureIndex(sp,[1.48,1.52],[1.56,1.60],method='ratio',sample='integrate',**kwargs)
        inds[3],errs[3] = measureIndex(sp,[1.635,1.675],[1.56,1.60],method='ratio',sample='integrate',**kwargs)
        inds[4],errs[4] = measureIndex(sp,[1.975,1.995],[2.08,2.12],method='ratio',sample='integrate',**kwargs)
        inds[5],errs[5] = measureIndex(sp,[2.215,2.255],[2.08,2.12],method='ratio',sample='integrate',**kwargs)
        inds[6],errs[6] = measureIndex(sp,[2.06,2.10],[1.25,1.29],method='ratio',sample='integrate',**kwargs)
    elif ('bardalez' in set.lower()):
        reference = 'Indices from Bardalez Gagliuffi et al. (2014)'
        refcode = 'BUR06'
        names = ['H2O-J','CH4-J','H2O-H','CH4-H','H2O-K','CH4-K','K-J','H-dip','K-slope','J-slope','H-bump','H2O-Y']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[1.14,1.165],[1.26,1.285],method='ratio',sample='integrate',**kwargs)
        inds[1],errs[1] = measureIndex(sp,[1.315,1.335],[1.26,1.285],method='ratio',sample='integrate',**kwargs)
        inds[2],errs[2] = measureIndex(sp,[1.48,1.52],[1.56,1.60],method='ratio',sample='integrate',**kwargs)
        inds[3],errs[3] = measureIndex(sp,[1.635,1.675],[1.56,1.60],method='ratio',sample='integrate',**kwargs)
        inds[4],errs[4] = measureIndex(sp,[1.975,1.995],[2.08,2.12],method='ratio',sample='integrate',**kwargs)
        inds[5],errs[5] = measureIndex(sp,[2.215,2.255],[2.08,2.12],method='ratio',sample='integrate',**kwargs)
        inds[6],errs[6] = measureIndex(sp,[2.06,2.10],[1.25,1.29],method='ratio',sample='integrate',**kwargs)
### ADRIAN FILL IN OTHER INDICES HERE - NOTE THAT H-DIP METHOD=INVERSE_LINE, J-CURVE METHOD = LINE

    elif ('tokunaga' in set.lower()):
        reference = 'Indices from Tokunaga & Kobayashi (1999)'
        refcode = 'TOK99'
        names = ['K1','K2']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[2.1,2.18],[1.96,2.04],method='change',sample='average',**kwargs)
        inds[1],errs[1] = measureIndex(sp,[2.2,2.28],[2.1,2.18],method='change',sample='average',**kwargs)
    elif ('reid' in set.lower()):
        reference = 'Indices from Reid et al. (2001)'
        refcode = 'REI01'
        names = ['H2O-A','H2O-B']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[1.33,1.35],[1.28,1.30],method='ratio',sample='average',**kwargs)
        inds[1],errs[1] = measureIndex(sp,[1.47,1.49],[1.59,1.61],method='ratio',sample='average',**kwargs)
    elif ('geballe' in set.lower()):
        reference = 'Indices from Geballe et al. (2002)'
        refcode = 'GEB02'
        names = ['H2O-1.2','H2O-1.5','CH4-2.2']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[1.26,1.29],[1.13,1.16],method='ratio',sample='integrate',**kwargs)
        inds[1],errs[1] = measureIndex(sp,[1.57,1.59],[1.46,1.48],method='ratio',sample='integrate',**kwargs)
        inds[2],errs[2] = measureIndex(sp,[2.08,2.12],[2.215,2.255],method='ratio',sample='integrate',**kwargs)
    elif ('allers' in set.lower()):
        reference = 'Indices from Allers et al. (2007), Allers & Liu (2013)'
        refcode = 'ALL13'
        names = ['H2O','FeH-z','VO-z','FeH-J','KI-J','H-cont']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[1.55,1.56],[1.492,1.502],method='ratio',sample='average',**kwargs)
        inds[1],errs[1] = measureIndex(sp,[0.99135,1.00465],[0.97335,0.98665],[1.01535,1.02865],method='allers',sample='average',**kwargs)
        inds[2],errs[2] = measureIndex(sp,[1.05095,1.06505],[1.02795,1.04205],[1.07995,1.09405],method='allers',sample='average',**kwargs)
        inds[3],errs[3] = measureIndex(sp,[1.19880,1.20120],[1.19080,1.19320],[1.20680,1.20920],method='allers',sample='average',**kwargs)
        inds[4],errs[4] = measureIndex(sp,[1.23570,1.25230],[1.21170,1.22830],[1.26170,1.27830],method='allers',sample='average',**kwargs)
        inds[5],errs[5] = measureIndex(sp,[1.54960,1.57040],[1.45960,1.48040],[1.65960,1.68040],method='allers',sample='average',**kwargs)
    elif ('testi' in set.lower()):
        reference = 'Indices from Testi et al. (2001)'
        refcode = 'TES01'
        names = ['sHJ','sKJ','sH2O-J','sH2O-H1','sH2O-H2','sH2O-K']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[1.265,1.305],[1.6,1.7],method='change',sample='average',**kwargs)
        inds[1],errs[1] = measureIndex(sp,[1.265,1.305],[2.12,2.16],method='change',sample='average',**kwargs)
        inds[2],errs[2] = measureIndex(sp,[1.265,1.305],[1.09,1.13],method='change',sample='average',**kwargs)
        inds[3],errs[3] = measureIndex(sp,[1.60,1.70],[1.45,1.48],method='change',sample='average',**kwargs)
        inds[4],errs[4] = measureIndex(sp,[1.60,1.70],[1.77,1.81],method='change',sample='average',**kwargs)
        inds[5],errs[5] = measureIndex(sp,[2.12,2.16],[1.96,1.99],method='change',sample='average',**kwargs)
    elif ('slesnick' in set.lower()):
        reference = 'Indices from Slesnick et al. (2004)'
        refcode = 'SEL04'
        names = ['H2O-1','H2O-2','FeH']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[1.335,1.345],[1.295,1.305],method='ratio',sample='average',**kwargs)
        inds[1],errs[1] = measureIndex(sp,[2.035,2.045],[2.145,2.155],method='ratio',sample='average',**kwargs)
        inds[2],errs[2] = measureIndex(sp,[1.1935,1.2065],[1.2235,1.2365],method='ratio',sample='average',**kwargs)
    elif ('mclean' in set.lower()):
        reference = 'Indices from McLean et al. (2003)'
        refcode = 'MCL03'
        names = ['H2OD']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        inds[0],errs[0] = measureIndex(sp,[1.951,1.977],[2.062,2.088],method='ratio',sample='average',**kwargs)
    elif ('rojas' in set.lower()):
        reference = 'Indices from Rojas-Ayala et al.(2012)'
        refcode = 'ROJ12'
        names = ['H2O-K2']
        inds = numpy.zeros(len(names))
        errs = numpy.zeros(len(names))
        num, er1= measureIndex(sp,[2.070,2.090],[2.235,2.255],method='ratio',sample='average',**kwargs)
        den, er2= measureIndex(sp,[2.235,2.255],[2.360,2.380],method='ratio',sample='average',**kwargs)
        inds[0]= num/den
        errs[0]= inds[0]*numpy.sqrt((er1/num)**2+(er2/den)**2)    
    else:
        print '{} is not one of the sets used for measureIndexSet'.format(set)
        return numpy.nan

# output dictionary of indices
    result = {names[i]: (inds[i],errs[i]) for i in numpy.arange(len(names))}
#    result['reference'] = reference
#    return inds,errs,names

    return result


def metallicity(sp,**kwargs):
    '''Metallicity measurement using Na I and Ca I lines and H2O-K2 index as described in Rojas-Ayala et al. (2012)'''

    nsamples = kwargs.get('nsamples',100)

    coeff_feh = [-1.039,0.092,0.119]
    coeff_feh_e = [0.17,0.023,0.033]
    feh_unc = 0.100
    coeff_mh = [-0.731,0.066,0.083]
    coeff_mh_e = [0.12,0.016,0.023]
    mh_unc = 0.100

    h2ok2,h2ok2_e = measureIndexSet(sp, set='rojas')['H2O-K2']
    ew = measureEWSet(sp,set='rojas')        
    nai, nai_e = ew['Na I 2.206/2.209']
    cai, cai_e = ew['Ca I 2.26']

    mh = numpy.ones(nsamples)*coeff_mh[0]+\
        (numpy.random.normal(nai,nai_e,nsamples)/numpy.random.normal(h2ok2,h2ok2_e,nsamples))*coeff_mh[1]+\
        (numpy.random.normal(cai,cai_e,nsamples)/numpy.random.normal(h2ok2,h2ok2_e,nsamples))*coeff_mh[2]

    return numpy.nanmean(mh), numpy.sqrt(numpy.nanstd(mh)**2+mh_unc**2)


def properCoordinates(c):
    '''converts various coordinate forms to the proper SkyCoord format'''
    if isinstance(c,SkyCoord):
        return c
    elif isinstance(c,list):
        return SkyCoord(c[0]*u.deg,c[1]*u.deg,frame='icrs')
# input is sexigessimal string
    elif isinstance(c,str):
        return SkyCoord(c,'icrs', unit=(u.hourangle, u.deg))
    else:
        raise ValueError('\nCould not parse input format\n\n')


def readSpectrum(*args,**kwargs):

# keyword parameters
    folder = kwargs.get('folder','')
    catchSN = kwargs.get('catchSN',True)
    local = kwargs.get('local',True)
    online = kwargs.get('online',not local and checkOnline())
    local = not online
    url = kwargs.get('url',SPLAT_URL+DATA_FOLDER)
    kwargs['model'] = False


# filename
    file = kwargs.get('file','')
    file = kwargs.get('filename',file)
    if (len(args) > 0):
        file = args[0]
    kwargs['filename'] = file
    kwargs['model'] = False

# a filename must be passed
    if (kwargs['filename'] == ''):
        raise NameError('\nNeed to pass in filename to read in spectral data (readSpectrum)\n\n')

# first pass: check if file is local
    if online == False:
        file = checkLocal(kwargs['filename'])
        if file=='':
            file = checkLocal(kwargs['folder']+os.path.basename(kwargs['filename']))
            if file=='':
#            print 'Cannot find '+kwargs['filename']+' locally, trying online\n\n'
                local = False

# second pass: download file if necessary
    online = not local
    if online == True:
        file = checkOnline(url+kwargs['filename'])
        if file=='':
            raise NameError('\nCannot find file '+kwargs['filename']+' on SPLAT website\n\n')
        else:
# read in online file                
            file = kwargs['filename']
            try:
#                file = TMPFILENAME+'.'+ftype
                if os.path.exists(os.path.basename(file)):
                    os.remove(os.path.basename(file))
                open(os.path.basename(file), 'wb').write(urllib2.urlopen(url+file).read())
#                print file
#                kwargs['filename'] = os.path.basename(file)
#               sp = Spectrum(**kwargs)
#                os.remove(os.path.basename(tmp))
#                return sp
            except urllib2.URLError:
                raise NameError('\nProblem reading in '+file+' from SPLAT website\n\n')
    
# determine which type of file
    ftype = file.split('.')[-1]

# fits file    
    if (ftype == 'fit' or ftype == 'fits'):
        data = fits.open(file)
        if 'NAXIS3' in data[0].header.keys():
            d = data[0].data[0,:,:]
        else:
            d = data[0].data
        header = data[0].header
        data.close()

# ascii file    
    else:
        try:
            d = numpy.genfromtxt(file, comments='#', unpack=False, \
                missing_values = ('NaN','nan'), filling_values = (numpy.nan)).transpose()
        except ValueError:
            d = numpy.genfromtxt(file, comments=';', unpack=False, \
                 missing_values = ('NaN','nan'), filling_values = (numpy.nan)).transpose()
        header = fits.Header()      # blank header

# delete file if this was an online read
    if online and not local and os.path.exists(os.path.basename(file)):
        os.remove(os.path.basename(file))

# assign arrays to wave, flux, noise
    wave = d[0,:]
    flux = d[1,:]
    if len(d[:,0]) > 2:
        noise = d[2,:]
    else:
        noise = numpy.zeros(len(flux))
        noise[:] = numpy.nan        

# fix places where noise is claimed to be 0
    w = numpy.where(noise == 0.)
    noise[w] = numpy.nan

# fix nans in flux
    w = numpy.where(numpy.isnan(flux) == True)
    flux[w] = 0.

# fix to catch badly formatted files where noise column is S/N                 
#    print flux, numpy.median(flux)
    if (catchSN):
          w = numpy.where(flux > stats.nanmedian(flux))
          if (stats.nanmedian(flux[w]/noise[w]) < 1.):
              noise = flux/noise
              w = numpy.where(numpy.isnan(noise))
              noise[w] = stats.nanmedian(noise)

# clean up
#    if url != '' and not local:
#        os.remove(os.path.basename(TMPFILENAME))

    return {'wave':wave,'flux':flux,'noise':noise,'header':header}



def redden(sp, **kwargs):
    '''
    Description:
      Redden a spectrum based on an either Mie theory or a standard interstellar profile
      using Cardelli, Clayton, and Mathis (1989 ApJ. 345, 245)

    **Usage**

       >>> import splat
       >>> sp = splat.Spectrum(10001)                   # read in a source
       >>> spr = splat.redden(sp,av=5.,rv=3.2)          # redden to equivalent of AV=5

    **Note**
      This routine is still in beta form; only the CCM89 currently works

    '''
    w = sp.wave.value                           # assuming in microns!
    av = kwargs.get('av',0.0)


    if kwargs.get('mie',False):                 # NOT CURRENTLY FUNCTIONING
        a = kwargs.get('a',10.)                 # grain size
        n = kwargs.get('n',1.33)                # complex index of refraction
        x = 2*numpy.pi*a/w
        x0 = 2.*numpy.pi*a/0.55                 # for V-band
        qabs = -4.*x*((n**2-1)/(n**2+2)).imag
        qsca = (8./3.)*(x**4)*(((n**2-1)/(n**2+2))**2).real
#        tau = numpy.pi*(a**2)*(qabs+qsca)
        tau = 1.5*(qabs+qsca)/a    # for constant mass
        qabs0 = -4.*x0*((n**2-1)/(n**2+2)).imag
        qsca0 = (8./3.)*(x0**4)*(((n**2-1)/(n**2+2))**2).real
#        tau0 = numpy.pi*(a**2)*(qabs0+qsca0)
        tau0 = 1.5*(qabs0+qsca0)/a    # for constant mass
        scale = (10.**(-0.4*av))
        absfrac = scale*numpy.exp(numpy.max(tau)-tau)
    else:
        x = 1./w
        a = 0.574*(x**1.61)
        b = -0.527*(x**1.61)
        rv = kwargs.get('rv',3.1)
        absfrac = 10.**(-0.4*av*(a+b/rv))
    
    if kwargs.get('normalize',False):
        absfrac = absfrac/numpy.median(absfrac)
        
    print tau0, min(tau), max(tau), max(absfrac), min(absfrac)
    spabs = splat.Spectrum(wave=w,flux=absfrac)
    return sp*spabs



def searchLibrary(*args, **kwargs):
    '''Search the SpeX database to extract the key reference for that Spectrum
        Note that this is currently only and AND search - need to figure out
        how to a full SQL style search'''

# program parameters
    ref = kwargs.get('output','all')
    radius = kwargs.get('radius',10.)      # search radius in arcseconds
    classes = ['YOUNG','SUBDWARF','BINARY','SPBINARY','RED','BLUE','GIANT','WD','STANDARD','COMPANION']

# logic of search
    logic = 'and'         # default combination
    logic = kwargs.get('combine',logic).lower()
    logic = kwargs.get('logic',logic).lower()
    if (logic != 'and' and logic != 'or'):
        raise ValueError('\nLogical operator '+logic+' not supported\n\n')

# read in source database and add in shortnames and skycoords
    source_db = ascii.read(SPLAT_PATH+DB_FOLDER+SOURCES_DB, delimiter='\t',fill_values='-99.',format='tab')
    source_db['SHORTNAME'] = [designationToShortName(x) for x in source_db['DESIGNATION']]
    
# first search by source parameters
    source_db['SELECT'] = numpy.zeros(len(source_db['RA']))
    count = 0.

# search by source key
    if kwargs.get('sourcekey',False) != False:
        sk = kwargs['sourcekey']
        if isinstance(sk,int):
            sk = [sk]
        for s in sk:
            source_db['SELECT'][numpy.where(source_db['SOURCE_KEY'] == s)] += 1
        count+=1.
# search by name
    if kwargs.get('name',False) != False:
        nm = kwargs['name']
        if isinstance(nm,str):
            nm = [nm]
        for n in nm:
            source_db['SELECT'][numpy.where(source_db['NAME'] == n)] += 1
        count+=1.
# search by shortname
    if kwargs.get('shortname',False) != False:
        sname = kwargs['shortname']
        if isinstance(sname,str):
            sname = [sname]
        for sn in sname:
            if sn[0].lower() != 'j':
                sn = 'J'+sn
            source_db['SELECT'][numpy.where(source_db['SHORTNAME'] == sn)] += 1
        count+=1.
# exclude by shortname
    sname = kwargs.get('excludesource',False)
    sname = kwargs.get('excludeshortname',sname)
    if sname != False and len(sname) > 0:
        if isinstance(sname,str):
            sname = [sname]
        for sn in sname:
            if sn[0].lower() != 'j':
                sn = 'J'+sn
#            t = numpy.sum(source_db['SELECT'][numpy.where(source_db['SHORTNAME'] != sn)])
            source_db['SELECT'][numpy.where(source_db['SHORTNAME'] != sn)] += 1
#            if numpy.sum(source_db['SELECT'][numpy.where(source_db['SHORTNAME'] != sn)]) > t:
#                print 'rejected '+sn
        count+=1.
# search by reference list
    if kwargs.get('reference',False) != False:
        refer = kwargs['reference']
        if isinstance(ref,str):
            refer = [refer]
        for r in refer:
            source_db['SELECT'][numpy.where(source_db['DISCOVERY_REFERENCE'] == r)] += 1
        count+=1.
# search by designation
    if kwargs.get('designation',False) != False:
        desig = kwargs['designation']
        if isinstance(desig,str):
            desig = [desig]
        for d in desig:
            source_db['SELECT'][numpy.where(source_db['DESIGNATION'] == d)] += 1
        count+=1.
# search by coordinate - NOTE: THIS IS VERY SLOW RIGHT NOW
    if kwargs.get('coordinate',False) != False:
        coord = kwargs['coordinate']
        if isinstance(coord,SkyCoord):
            cc = coord
        else:
            cc = properCoordinates(coord)
# calculate skycoords
        s = []
        for i in numpy.arange(len(source_db['RA'])):
            try:        # to deal with a blank string
                s.append(SkyCoord(ra=float(source_db['RA'][i])*u.degree,dec=float(source_db['DEC'][i])*u.degree,frame='icrs'))
            except:
                s.append(SkyCoord(ra=numpy.nan*u.degree,dec=numpy.nan*u.degree,frame='icrs'))
        source_db['SKYCOORDS'] = s
        source_db['SEPARATION'] = [cc.separation(source_db['SKYCOORDS'][i]).arcsecond for i in numpy.arange(len(source_db['SKYCOORDS']))]
        source_db['SELECT'][numpy.where(source_db['SEPARATION'] <= radius)] += 1
        count+=1.

# search by spectral type
    spt_range = kwargs.get('spt_range',False)
    spt_range = kwargs.get('spt',spt_range)
    spt_type = kwargs.get('spt_type','LIT_TYPE')  
    if spt_range != False:
        if spt_type not in ['LIT_TYPE','SPEX_TYPE','OPT_TYPE','NIR_TYPE']:
            spt_type = 'LIT_TYPE'
        if not isinstance(spt_range,list):        # one value = only this type
            spt_range = [spt_range,spt_range]
        if isinstance(spt_range[0],str):          # convert to numerical spt
            spt_range = [typeToNum(spt_range[0]),typeToNum(spt_range[1])]
        source_db['SPTN'] = [typeToNum(x) for x in source_db[spt_type]]
        source_db['SELECT'][numpy.where(numpy.logical_and(source_db['SPTN'] >= spt_range[0],source_db['SPTN'] <= spt_range[1]))] += 1
        count+=1.



# search by magnitude range
    if kwargs.get('jmag',False) != False:
        mag = kwargs['jmag']
        if not isinstance(mag,list):        # one value = faint limit
            mag = [0,mag]
        source_db['JMAGN'] = [float('0'+x) for x in source_db['2MASS_J']]
        source_db['SELECT'][numpy.where(numpy.logical_and(source_db['JMAGN'] >= mag[0],source_db['JMAGN'] <= mag[1]))] += 1
        count+=1.
    if kwargs.get('hmag',False) != False:
        mag = kwargs['hmag']
        if not isinstance(mag,list):        # one value = faint limit
            mag = [0,mag]
        source_db['HMAGN'] = [float('0'+x) for x in source_db['2MASS_H']]
        source_db['SELECT'][numpy.where(numpy.logical_and(source_db['HMAGN'] >= mag[0],source_db['HMAGN'] <= mag[1]))] += 1
        count+=1.
    if kwargs.get('kmag',False) != False:
        mag = kwargs['kmag']
        if not isinstance(mag,list):        # one value = faint limit
            mag = [0,mag]
        source_db['KMAGN'] = [float('0'+x) for x in source_db['2MASS_KS']]
        source_db['SELECT'][numpy.where(numpy.logical_and(source_db['KMAGN'] >= mag[0],source_db['KMAGN'] <= mag[1]))] += 1
        count+=1.


# young
    if (kwargs.get('young','') != ''):
        source_db['YOUNG'] = [i != '' for i in source_db['GRAVITY_CLASS_CRUZ']] or [i != '' for i in source_db['GRAVITY_CLASS_ALLERS']]
        source_db['SELECT'][numpy.where(source_db['YOUNG'] == kwargs.get('young'))] += 1
        count+=1.

# specific gravity class
    flag = kwargs.get('gravity_class','')
    flag = kwargs.get('gravity',flag)
    if (flag != ''):
        source_db['SELECT'][numpy.where(source_db['GRAVITY_CLASS_CRUZ'] == flag)] += 1
        source_db['SELECT'][numpy.where(source_db['GRAVITY_CLASS_ALLERS'] == flag)] += 1
        count+=1.


# specific cluster
    if (kwargs.get('cluster','') != '' and isinstance(kwargs.get('cluster'),str)):
        source_db['CLUSTER_FLAG'] = [i.lower() == kwargs.get('cluster').lower() for i in source_db['CLUSTER']]
        source_db['SELECT'][numpy.where(source_db['CLUSTER_FLAG'] == True)] += 1
        count+=1.

# giant
    if (kwargs.get('giant','') != ''):
#        kwargs['vlm'] = False
        source_db['GIANT'] = [i != '' for i in source_db['LUMINOSITY_CLASS']]
        source_db['SELECT'][numpy.where(source_db['GIANT'] == kwargs.get('giant'))] += 1
        count+=1.

# luminosity class
    if (kwargs.get('giant_class','') != ''):
        source_db['GIANT_FLAG'] = [i.lower() == kwargs.get('giant_class').lower() for i in source_db['GIANT']]
        source_db['SELECT'][numpy.where(source_db['GIANT_FLAG'] == True)] += 1
        count+=1.

# subdwarf
    if (kwargs.get('subdwarf','') != ''):
        source_db['SUBDWARF'] = [i != '' for i in source_db['METALLICITY_CLASS']]
        source_db['SELECT'][numpy.where(source_db['SUBDWARF'] == kwargs.get('subdwarf'))] += 1
        count+=1.

# metallicity class
    if (kwargs.get('subdwarf_class','') != ''):
        source_db['SD_FLAG'] = [i.lower() == kwargs.get('subdwarf_class').lower() for i in source_db['METALLICITY_CLASS']]
        source_db['SELECT'][numpy.where(source_db['SD_FLAG'] == True)] += 1
        count+=1.

# red
    if (kwargs.get('red','') != ''):
        source_db['RED'] = ['red' in i for i in source_db['LIBRARY']]
        source_db['SELECT'][numpy.where(source_db['RED'] == kwargs.get('red'))] += 1
        count+=1.

# blue
    if (kwargs.get('blue','') != ''):
        source_db['BLUE'] = ['blue' in i for i in source_db['LIBRARY']]
        source_db['SELECT'][numpy.where(source_db['BLUE'] == kwargs.get('blue'))] += 1
        count+=1.

# binaries
    if (kwargs.get('binary','') != ''):
        source_db['BINARY_FLAG'] = [i == 'Y' for i in source_db['BINARY']]
        source_db['SELECT'][numpy.where(source_db['BINARY_FLAG'] == kwargs.get('binary'))] += 1
        count+=1.

# spectral binaries
    if (kwargs.get('sbinary','') != ''):
        source_db['SBINARY_FLAG'] = [i == 'Y' for i in source_db['SBINARY']]
        source_db['SELECT'][numpy.where(source_db['SBINARY_FLAG'] == kwargs.get('sbinary'))] += 1
        count+=1.


# companions
    if (kwargs.get('companion','') != ''):
        source_db['COMPANION_FLAG'] = [i != '' for i in source_db['COMPANION_NAME']]
        source_db['SELECT'][numpy.where(source_db['COMPANION_FLAG'] == kwargs.get('companion'))] += 1
        count+=1.

# white dwarfs
    if (kwargs.get('wd','') != ''):
        kwargs['vlm'] = False
        source_db['WHITEDWARF'] = [i == 'WD' for i in source_db['OBJECT_TYPE']]
        source_db['SELECT'][numpy.where(source_db['WHITEDWARF'] == kwargs.get('wd'))] += 1
        count+=1.

# galaxies
    if (kwargs.get('galaxy','') != ''):
        kwargs['vlm'] = False
        source_db['GALAXY'] = [i == 'GAL' for i in source_db['OBJECT_TYPE']]
        source_db['SELECT'][numpy.where(source_db['GALAXY'] == kwargs.get('galaxy'))] += 1
        count+=1.

# carbon stars
    if (kwargs.get('carbon','') != ''):
        kwargs['vlm'] = False
        source_db['CARBON'] = [i == 'C' for i in source_db['OBJECT_TYPE']]
        source_db['SELECT'][numpy.where(source_db['CARBON'] == kwargs.get('carbon'))] += 1
        count+=1.

# VLM dwarfs by default
    if (kwargs.get('vlm',True)):
        source_db['SELECT'][numpy.where(source_db['OBJECT_TYPE'] == 'VLM')] += 1
        count+=1.

# select source keys
    if (count > 0):
        if (logic == 'and'):
            source_db['SELECT'] = numpy.floor(source_db['SELECT']/count)
        elif (logic == 'or'):
            source_db['SELECT'] = numpy.ceil(source_db['SELECT']/count)

        source_keys = source_db['SOURCE_KEY'][numpy.where(source_db['SELECT']==1)]
# no selection made on sources - choose everything
    else:
        source_keys = source_db['SOURCE_KEY']
    

# read in spectral database
    spectral_db = ascii.read(SPLAT_PATH+DB_FOLDER+SPECTRA_DB, delimiter='\t',fill_values='-99.',format='tab')
    spectral_db['SELECT'] = numpy.zeros(len(spectral_db['DATA_KEY']))
    count = 0.
    
    spectral_db['SOURCE_SELECT'] = [x in source_keys for x in spectral_db['SOURCE_KEY']]
    
# search by filename
    file = kwargs.get('file','')
    file = kwargs.get('filename',file)
    if (file != ''):
        if isinstance(file,str):
            file = [file]
        for f in file:
            spectral_db['SELECT'][numpy.where(spectral_db['DATA_FILE'] == f)] += 1
        count+=1.
# exclude by data key
    if kwargs.get('excludekey',False) != False:
        exkey = kwargs['excludekey']
#        print file
        if len(exkey) > 0:
            if isinstance(exkey,str):
                exkey = [exkey]
            for f in exkey:
                spectral_db['SELECT'][numpy.where(spectral_db['DATA_KEY'] != f)] += 1
#                print spectral_db['SELECT'][numpy.where(spectral_db['DATA_KEY'] != f)]
            count+=1.
# exclude by filename
    if kwargs.get('excludefile',False) != False:
        file = kwargs['excludefile']
#        print file
        if len(file) > 0:
            if isinstance(file,str):
                file = [file]
            for f in file:
                spectral_db['SELECT'][numpy.where(spectral_db['DATA_FILE'] != f)] += 1
            count+=1.
# search by observation date range
    if kwargs.get('date',False) != False:
        date = kwargs['date']
        if isinstance(date,str) or isinstance(date,long) or isinstance(date,float) or isinstance(date,int):
            date = [float(date),float(date)]
        elif isinstance(date,list):
            date = [float(date[0]),float(date[-1])]
        else:
            raise ValueError('\nCould not parse date input {}\n\n'.format(date))
        spectral_db['DATEN'] = [float(x) for x in spectral_db['OBSERVATION_DATE']]
        spectral_db['SELECT'][numpy.where(numpy.logical_and(spectral_db['DATEN'] >= date[0],spectral_db['DATEN'] <= date[1]))] += 1
        count+=1.
# search by S/N range
    if kwargs.get('snr',False) != False:
        snr = kwargs['snr']
        if not isinstance(snr,list):        # one value = minimum S/N
            snr = [float(snr),1.e9]
        spectral_db['SNRN'] = [float('0'+x) for x in spectral_db['MEDIAN_SNR']]
        spectral_db['SELECT'][numpy.where(numpy.logical_and(spectral_db['SNRN'] >= snr[0],spectral_db['SNRN'] <= snr[1]))] += 1
        count+=1.

# combine selection logically
    if (count > 0):
        if (logic == 'and'):
            spectral_db['SELECT'] = numpy.floor(spectral_db['SELECT']/count)
        else:
            spectral_db['SELECT'] = numpy.ceil(spectral_db['SELECT']/count)

    else:
        spectral_db['SELECT'] = numpy.ones(len(spectral_db['DATA_KEY']))

# limit access to public data for most users
    if (not checkAccess() or kwargs.get('published',False) or kwargs.get('public',False)):
        spectral_db['SELECT'][numpy.where(spectral_db['PUBLISHED'] != 'Y')] = 0.

# no matches
    if numpy.sum(spectral_db['SELECT']) == 0. or numpy.sum(source_db['SELECT']) == 0.:
#        print 'No spectra in the SPL database match the selection criteria'
        return Table()
    else:

# merge databases
        db = join(spectral_db[:][numpy.where(numpy.logical_and(spectral_db['SELECT']==1,spectral_db['SOURCE_SELECT']==True))],source_db,keys='SOURCE_KEY')
                
        if (ref == 'all'):
            return db
        else:
            return db[ref]



def test():
    '''
    Testing the SPLAT Code.
    '''
    
    test_src = 'Random'

    sys.stderr.write('\n\n>>>>>>>>>>>> TESTING SPLAT CODE <<<<<<<<<<<<\n')
# check you are online
    if checkOnline():
        sys.stderr.write('\n...you are online and can see SPLAT website\n')
    else:
        sys.stderr.write('\n...you are NOT online or cannot see SPLAT website\n')

# check your access
    if checkAccess():
        sys.stderr.write('\n...you currently HAVE access to unpublished spectra\n')
    else:
        sys.stderr.write('\n...you currently DO NOT HAVE access to unpublished spectra\n')
        
# check you can search for and load a spectrum
#    sp = getSpectrum(shortname=test_src)[0]
    sp = getSpectrum(spt=['L5','T5'],lucky=True)[0]
    sp.info()
    sys.stderr.write('\n...getSpectrum and loadSpectrum successful\n')

# check searchLibrary
    list = searchLibrary(young=True,output='DATA_FILE')
    sys.stderr.write('\n{} young spectra in the SPL  ...searchLibrary successful\n'.format(len(list)))

# check index measurement
    ind = measureIndexSet(sp,set='burgasser')
    sys.stderr.write('\nSpectral indices for '+test_src+':\n')
    for k in ind.keys():
        print '\t{:s}: {:4.3f}+/-{:4.3f}'.format(k, ind[k][0], ind[k][1])
    sys.stderr.write('...index measurement successful\n')

# check classification
    spt, spt_e = classifyByIndex(sp,set='burgasser')
    sys.stderr.write('\n...index classification of '+test_src+' = {:s}+/-{:2.1f}; successful\n'.format(spt,spt_e))

    spt, spt_e = classifyByStandard(sp,method='kirkpatrick')
    sys.stderr.write('\n...standard classification of '+test_src+' = {:s}+/-{:2.1f}; successful\n'.format(spt,spt_e))

    grav = classifyGravity(sp)
    sys.stderr.write('\n...gravity class of '+test_src+' = {}; successful\n'.format(grav))

# check SpT -> Teff
    teff, teff_e = typeToTeff(spt,unc=spt_e)
    sys.stderr.write('\n...Teff of '+test_src+' = {:.1f}+/-{:.1f} K; successful\n'.format(teff,teff_e))

# check flux calibration
    sp.normalize()
    sp.fluxCalibrate('2MASS J',15.0,apparent=True)
    mag,mag_e = filterMag(sp,'MKO J')
    sys.stderr.write('\n...apparent magnitude MKO J = {:3.2f}+/-{:3.2f} from 2MASS J = 15.0; filter calibration successful\n'.format(mag,mag_e))

# check models
#   mdl = loadModel(teff=1000,logg=5.0,set='BTSettl2008')
    logg = 5.2
    if grav == 'VL-G':
        logg = 4.2
    elif grav == 'INT-G':
        logg = 4.6
    mdl = loadModel(teff=teff,logg=logg,set='BTSettl2008')
    sys.stderr.write('\n...interpolated model generation successful\n')

# check normalization
    sys.stderr.write('\n...normalization successful\n')

# check compareSpectrum
    chi, scale = compareSpectra(sp,mdl,mask_standard=True,stat='chisqr')
    sys.stderr.write('\nScaling model: chi^2 = {}, scale = {}'.format(chi,scale))
    sys.stderr.write('\n...compareSpectra successful\n'.format(chi,scale))

# check plotSpectrum
    mdl.scale(scale)
    plotSpectrum(sp,mdl,colors=['k','r'],title='If this appears everything is OK: close window')
    sys.stderr.write('\n...plotSpectrum successful\n')
    sys.stderr.write('\n>>>>>>>>>>>> SPLAT TEST SUCCESSFUL; HAVE FUN! <<<<<<<<<<<<\n\n')


def typeToMag(spt, filt, **kwargs):
    """
    Takes a spectral type, its uncertainty, and a filter, returns absolute magnitude
    Filter options = ['MKO K', 'MKO H', 'MKO J', 'MKO Y', 'MKO LP', '2MASS J', '2MASS K', '2MASS H']
    References = ['faherty', 'dupuy', 'burgasser']
    """

#Keywords
    nsamples = kwargs.get('nsamples', 100)
    ref = kwargs.get('ref', 'dupuy')
    unc = kwargs.get('unc', 0.)

#Convert spectral type string to number
    if (type(spt) == str):
        spt = typeToNum(spt, uncertainty=unc)
    else:
        spt = copy.deepcopy(spt)

#Faherty
    if (ref.lower() == 'faherty'):
        sptoffset = 10.
        reference = 'Abs Mag/SpT relation from Faherty et al. (2012)'
        coeffs = { \
            'MKO J': {'fitunc' : 0.30, 'range' : [20., 38.],  \
                'coeff': [.000203252, -.0129143, .275734, -1.99967, 14.8948]}, \
            'MKO H': {'fitunc' : 0.27, 'range' : [20., 38.], \
                'coeff' : [.000175368, -.0108205, .227363, -1.60036, 13.2372]}, \
            'MKO K': {'fitunc' : 0.28, 'range' : [20., 38.], \
                'coeff' : [.0000816516, -.00469032, .0940816, -.485519, 9.76100]}}

# Burgasser
    elif (ref.lower() == 'burgasser'):
        sptoffset = 20.
        reference = 'Abs Mag/SpT relation from Burgasser (2007)'
        coeffs = { \
            'MKO K': {'fitunc' : 0.26, 'range' : [20., 38.], \
                'coeff': [.0000001051, -.000006985, .0001807, -.002271, .01414, -.04024, .05129, .2322, 10.45]}}
 
# Dupuy & Liu, default reference  
    elif (ref.lower() == 'dupuy'):
        reference = 'Abs Mag/SpT relation from Dupuy & Liu (2012)'
        sptoffset = 10.
        coeffs = { \
            'MKO J': {'fitunc' : 0.39, 'range' : [16., 39.], \
                'coeff' : [-.00000194920, .000227641, -.0103332, .232771, -2.74405, 16.3986, -28.3129]}, \
            'MKO Y': {'fitunc': 0.40, 'range' : [16., 39.], \
                'coeff': [-.00000252638, .000285027, -.0126151, .279438, -3.26895, 19.5444, -35.1560]}, \
            'MKO H': {'fitunc': 0.38, 'range' : [16., 39.], \
                'coeff': [-.00000224083, .000251601, -.0110960, .245209, -2.85705, 16.9138, -29.7306]}, \
            'MKO K': {'fitunc': 0.40, 'range' : [16., 39.], \
                'coeff': [-.00000104935, .000125731, -.00584342, .135177, -1.63930, 10.1248, -15.2200]}, \
            'MKO LP': {'fitunc': 0.28, 'range': [16., 39.], \
                'coeff': [0.00000, 0.00000, .0000546366, -.00293191, .0530581,  -.196584, 8.89928]}, \
            '2MASS J': {'fitunc': 0.40, 'range': [16., 39.], \
                'coeff': [-.000000784614, .000100820, -.00482973, .111715, -1.33053, 8.16362, -9.67994]}, \
            '2MASS H': {'fitunc': 0.40, 'range': [16., 38.5], \
                'coeff': [-.00000111499, .000129363, -.00580847, .129202, -1.50370, 9.00279, -11.7526]}, \
            '2MASS K': {'fitunc': 0.43, 'range':[16., 38.5], \
                'coeff': [0.00000, 0.00000, .000106693, -.00642118, .134163, -.867471, 11.0114]}}

    else:
        sys.stderr.write('\nInvalid Abs Mag/SpT relation given: %s\n' % ref)
        return numpy.nan, numpy.nan

    if (filt.upper() in coeffs.keys()) == 1:
        for filter in coeffs.keys():
            if filt.upper() == filter:
                coeff = coeffs[filter]['coeff']
                fitunc = coeffs[filter]['fitunc']
                range = coeffs[filter]['range']
    else:
        sys.stderr.write('\n Invalid filter given for %s\n' % reference)
        return numpy.nan, numpy.nan

# compute magnitude if its in the right spectral type range
    if (range[0] <= spt <= range[1]):
        if (unc > 0.):
            vals = numpy.polyval(coeff, numpy.random.normal(spt - sptoffset, unc, nsamples))
            abs_mag = numpy.nanmean(vals)
            abs_mag_error = (numpy.nanstd(vals)**2+fitunc**2)**0.5
            return abs_mag, abs_mag_error
        else:
            abs_mag = numpy.polyval(coeff, spt-sptoffset)
            return abs_mag, fitunc
    else:
        sys.stderr.write('\nSpectral Type is out of range for %s Abs Mag/SpT relation\n' % reference)
        return numpy.nan, numpy.nan


def typeToNum(input, **kwargs):
    '''convert between string and numeric spectral types'''
# keywords     
    error = kwargs.get('error','')
    unc = kwargs.get('uncertainty',0.)
    subclass = kwargs.get('subclass','')
    lumclass = kwargs.get('lumclass','')
    ageclass = kwargs.get('ageclass','')
    colorclass = kwargs.get('colorclass','')
    peculiar = kwargs.get('peculiar',False)
    spletter = 'KMLTY'

# number -> spectral type
    if (isNumber(input)):
        spind = int(abs(input/10))
        spdec = numpy.around(input,1)-spind*10.
        pstr = ''
        if (unc > 1.):
            error = ':'
        if (unc > 2.):
            error = '::'
        if (peculiar):
            pstr = 'p'
        if (0 <= spind < len(spletter)):
            output = colorclass+subclass+spletter[spind]+'{:3.1f}'.format(spdec)+ageclass+lumclass+pstr+error
        else:
            print 'Spectral type number must be between 0 ({}0) and {} ({}9)'.format(spletter[0],len(spletter)*10.-1.,spletter[-1])
            output = numpy.nan

# spectral type -> number
    elif isinstance(input,str):
        input = string.split(input,sep='+')[0]    # remove +/- sides
        input = string.split(input,sep='-')[0]    # remove +/- sides
        sptype = re.findall('[{}]'.format(spletter),input)
        if (len(sptype) == 1):
            output = spletter.find(sptype[0])*10.
            spind = input.find(sptype[0])+1
            if (spind < len(input)):
                if (input.find('.') < 0):
                    if (isNumber(input[spind])):
                        output = output+float(input[spind])
                else:
                    output = output+float(input[spind:spind+3])
                    spind = spind+3
            ytype = re.findall('[abcd]',input.split('p')[-1])
            if (len(ytype) == 1):
                ageclass = ytype[0]
            if (input.find('p') != -1):
                 peculiar = True
            if (input.find('sd') != -1):
                 subclass = 'sd'
            if (input.find('esd') != -1):
                 subclass = 'esd'
            if (input.find('usd') != -1):
                 subclass = 'usd'
            if (input.count('I') > 0):
                 lumclass = ''.join(re.findall('I',input))
            if (input.count(':') > 0):
                 error = ''.join(re.findall(':',input))
            if (input[0] == 'b' or input[0] == 'r'):
                 colorclass = input[0]
        if (len(sptype) != 1):
#            print 'Only spectral classes {} are handled with this routine'.format(spletter)
            output = numpy.nan
# none of the above - return the input
    else:
        output = input
    return output


def typeToTeff(input, **kwargs):
    '''return Teff for a given SpT'''
# keywords     
    nsamples = kwargs.get('nsamples',100)
    unc = kwargs.get('uncertainty',0.001)
    unc = kwargs.get('unc',unc)
    unc = kwargs.get('spt_e',unc)
    ref = kwargs.get('ref','stephens2009')
    ref = kwargs.get('set',ref)
    ref = kwargs.get('method',ref)

# convert spectral type string to number
    if (type(input) == str):
        spt = typeToNum(input,uncertainty=unc)
    else:
        spt = copy.deepcopy(input)
    
    if spt < 20. and 'marocco' not in ref.lower():
        ref='stephens2009'

# choose among possible options

# Golimowski et al. (2004, AJ, 127, 3516)
    if ('golimowski' in ref.lower()):
        reference = 'Teff/SpT relation from Golimowski et al. (2004)'
        sptoffset = 10.
        coeff = [9.5373e-4,-9.8598e-2,4.0323,-8.3099e1,9.0951e2,-5.1287e3,1.4322e4]
        range = [16.,38.]
        fitunc = 124.

# Looper et al. (2008, ApJ, 685, 1183)
    elif ('looper' in ref.lower()):
        reference = 'Teff/SpT relation from Looper et al. (2008)'
        sptoffset = 20.
        coeff = [9.084e-4,-4.255e-2,6.414e-1,-3.101,1.950,-108.094,2319.92]
        range = [20.,38.]
        fitunc = 87.

# Stephens et al. (2009, ApJ, 702, 1545); using OPT/IR relation for M6-T8
# plus alternate coefficients for L3-T8
    elif ('stephens' in ref.lower()):
        reference = 'Teff/SpT relation from Stephens et al. (2009)'
        sptoffset = 10.
        coeff = [-0.0025492,0.17667,-4.4727,54.67,-467.26,4400.]
        range = [16.,38.]
        fitunc = 100.
        coeff_alt = [-0.011997,1.2315,-50.472,1031.9,-10560.,44898.]
        range_alt = [23.,38.]

# Marocco et al. (2013, AJ, 146, 161)
    elif ('marocco' in ref.lower()):
        reference = 'Teff/SpT relation from Marocco et al. (2013)'
        sptoffset = 10.
        coeff = [7.4211e-5,-8.43736e-3,3.90319e-1,-9.46896,129.141,-975.953,3561.47,-1613.82]
        range = [17.,38.]
        fitunc = 140.

    else:
        sys.stderr.write('\nInvalid Teff/SpT relation given ({})\n'.format(ref))
        return numpy.nan, numpy.nan

    if (range[0] <= spt <= range[1]):
        vals = numpy.polyval(coeff,numpy.random.normal(spt-sptoffset,unc,nsamples))
        if ('stephens' in ref.lower()):
            if (range_alt[0] <= spt <= range_alt[1]):
                vals = numpy.polyval(coeff_alt,numpy.random.normal(spt-sptoffset,unc,nsamples))
        teff = numpy.nanmean(vals)
        teff_e = (numpy.nanstd(vals)**2+fitunc**2)**0.5
        return teff, teff_e
    else:
        sys.stderr.write('\nSpectral Type is out of range for {:s} Teff/SpT relation\n'.format(reference))
        return numpy.nan, numpy.nan


def weightedMeanVar(vals, winp, *args, **kwargs):
    '''Compute weighted mean of an array of values through various methods'''
    
    method = kwargs.get('method','')
    minwt = kwargs.get('weight_minimum',0.)
    dof = kwargs.get('dof',len(vals)-1)
    if (numpy.nansum(winp) <= 0.):
        weights = numpy.ones(len(vals))
    if isinstance(winp,astropy.units.quantity.Quantity):
        winput = winp.value
    else:
        winput = copy.deepcopy(winp)

# uncertainty weighting: input is unceratinties   
    if (method == 'uncertainty'):
        weights = [w**(-2) for w in winput]
# ftest weighting: input is chisq values, extra dof value is required   
    elif (method == 'ftest'):
# fix issue of chi^2 = 0
        minchi = numpy.nanmin(winput)
        weights = numpy.array([stats.f.pdf(w/minchi,dof,dof) for w in winput])
# just use the input as the weights
    else:
        weights = [w for w in winput]
    
    weights = weights/numpy.nanmax(weights)
    weights[numpy.where(weights < minwt)] = 0.
    mn = numpy.nansum(vals*weights)/numpy.nansum(weights)
    var = numpy.nansum(weights*(vals-mn)**2)/numpy.nansum(weights)
    
    return mn,var        



# run test program if calling from command line
if __name__ == "__main__":
    test()