from __future__ import print_function, division

"""
.. note::
         Using a suite of evolutionary models, this code translates 
         between the following brown dwarf parameters: mass, age, 
         temperature, radius, surface gravity, and luminosity. We allow 
         the user to choose a set of evolutionary model 
         (Baraffe, Burrows, or Saumon) and two parameters, then output
         the rest of the interpolated parameters. 
"""

# imports: internal
import copy
import glob
import requests

# imports: external
from astropy import units as u
import astropy.constants as constants
from astropy.cosmology import Planck15, z_at_value
from astropy.io import ascii
import pandas
import matplotlib.pyplot as plt
import numpy
from scipy.interpolate import griddata, interp1d
import scipy.integrate as integrate
import scipy.stats as stats

# imports: splat
from splat.initialize import *
from splat.utilities import *


###############################################################################
###############################################################################
def loadEvolModel(*model,**kwargs):
    '''
    :Purpose: Reads in the evolutionary model parameters for the models listed below, which are used to interpolate parameters in `modelParameters()`_. 

    .. _`modelParameters()` : api.html#splat_evolve.modelParameters

    Available models are:

        - **baraffe** : Models from `Baraffe et al. (2003) <http://adsabs.harvard.edu/abs/2003A&A...402..701B>`_ for 1 Myr < age < 10 Gyr, 0.005 Msol < mass < 0.1 Msol, and solar metallicity (COND dust prescription)
        - **baraffe15** : Models from `Baraffe et al. (2015) <http://adsabs.harvard.edu/abs/2015A&A...577A..42B>`_ for 1 Myr < age < 10 Gyr, 0.01 Msol < mass < 1.4 Msol, and solar metallicity
        - **burrows** : Models from `Burrows et al. (2001) <http://adsabs.harvard.edu/abs/2001RvMP...73..719B>`_ for 1 Myr < age < 10 Gyr, 0.005 Msol < mass < 0.2 Msol, and solar metallicity
        - **saumon** : Models from `Saumon et al. (2003) <http://adsabs.harvard.edu/abs/2008ApJ...689.1327S>`_ for 3 Myr < age < 10 Gyr, 0.002 Msol < mass < 0.085 Msol, although mass and age ranges vary as the maximum temperature for the models is 2500 K. For these models there are additional options:
        
            - **metallicity** = `solar`, `+0.3`, or `-0.3`
            - **cloud** =  `cloud-free`, `hybrid`, `f2` (sub- and super-solar metallicities are only cloud-free)

    Parameter units (in astropy convention) are: 

        - `masses`: Solar masses
        - `ages`: Gyr
        - `temperature`: K
        - `gravity`: log10 of cm/s/s
        - `luminosity`: log10 of Solar luminosities
        - `radius`: Solar radii

    Models are contained in SPLAT's reference/EvolutionaryModels folder.

    Required Inputs:

    :param: model: string of the name of the evolutionary model set to be used; can be `baraffe` (default), `burrows`, or `saumon`

    Optional Inputs:

    :param: metallicity: for Saumon models, this is the metallicity assumed, and can be a string or integer.  Allowed values are 0 (or `solar` = default), -0.3 (or `subsolar`) or 0.3 (or `supersolar`)
    :param: cloud: for Saumon models, this is the desired cloud prescription, and is a string:

        - no clouds: `cloud` = `nocloud`, `cloud-free` or `nc` (default)
        - hybrid cloud prescription: `cloud` = `hybrid`
        - f2 cloud prescription: `cloud` = `f2`

    Output: 

    Dictionary containing keywords mass, age, temperature, luminosity, gravity, and radius, each linked to the evolutionary parameters retrieved. 

    :Example:
    >>> import splat
    >>> p = splat.loadEvolModel('saumon',metallicity=-0.3,cloud='nc')
    You are using saumon's models.
    >>> for k in list(p.keys()): print('{}: {}'.format(k, p[k][12]))
    age: 0.15
    mass: [ 0.002  0.003  0.004  0.005  0.006  0.007  0.008  0.009  0.01   0.011
      0.012  0.013  0.014  0.015  0.016  0.017  0.018  0.019  0.02   0.022
      0.024  0.026  0.028  0.03   0.033  0.035  0.038  0.04   0.043  0.045
      0.048  0.05   0.053]
    temperature: [  353.   418.   471.   523.   585.   642.   695.   748.   806.   893.
      1146.  1228.  1114.  1113.  1148.  1183.  1227.  1270.  1316.  1402.
      1489.  1572.  1654.  1739.  1853.  1930.  2030.  2096.  2187.  2240.
      2316.  2362.  2426.] 
    gravity: [ 3.576  3.746  3.871  3.972  4.056  4.128  4.191  4.246  4.296  4.335
      4.337  4.368  4.437  4.479  4.512  4.543  4.571  4.597  4.621  4.665
      4.704  4.74   4.772  4.8    4.839  4.861  4.892  4.909  4.931  4.947
      4.966  4.978  4.996]
    luminosity: [-6.691 -6.393 -6.185 -6.006 -5.815 -5.658 -5.527 -5.404 -5.277 -5.098
     -4.628 -4.505 -4.709 -4.724 -4.675 -4.627 -4.568 -4.51  -4.45  -4.342
     -4.24  -4.146 -4.058 -3.969 -3.856 -3.781 -3.69  -3.628 -3.546 -3.5   -3.432
     -3.393 -3.34 ]
    radius: [ 0.1206  0.1214  0.1214  0.1209  0.1202  0.1195  0.1189  0.1182  0.1178
      0.1181  0.123   0.1235  0.1184  0.1167  0.1161  0.1154  0.1151  0.1148
      0.1146  0.1142  0.1139  0.1139  0.1138  0.1141  0.1144  0.115   0.1155
      0.1163  0.1174  0.118   0.1193  0.12    0.121 ]
    '''

# check model
    try: model = model[0].lower()
    except TypeError: raise TypeError('\nInput parameter must be a string')
    except IndexError: model = 'baraffe15'

    m = checkEvolutionaryModelName(model)
    if m == False: raise ValueError('\nDid not recognize model name {}'.format(model))
    model = m
    if kwargs.get('verbose',False): print('You are using evolutionary models from {}'.format(EVOLUTIONARY_MODELS[model]['name']))

# read in models
    files = glob.glob(os.path.normpath(SPLAT_PATH+EVOLUTIONARY_MODEL_FOLDER+model+'/{}*.txt'.format(model)))
    if model == 'saumon08':

# set metallicity
        metallicity = kwargs.get('z',False)
        metallicity = kwargs.get('metallicity',metallicity)
        if metallicity == False:
            metallicity = 'solar'
        if isinstance(metallicity,int) or isinstance(metallicity,float):
            metallicity = '{:.1f}'.format(metallicity)
        if metallicity.lower() == 'solar' or metallicity == '0.0':
            Z = 'z0'
        elif metallicity == '0.3' or metallicity == '+0.3' or metallicity == 'supersolar':
            Z = 'z+0.3'
        elif metallicity == '-0.3' or metallicity == 'subsolar':
            Z = 'z-0.3'
        else:
            raise ValueError('\nMetallicity for Saumon model must be 0.0 (solar), +0.3 or -0.3, not {}\n'.format(metallicity))
# set cloud treatment
        cloud = kwargs.get('cloud',False)
        cloud = kwargs.get('clouds',cloud)
        cloud = kwargs.get('cld',cloud)
        if cloud == False:
            cloud = 'nc'
        if metallicity=='-0.3' or metallicity=='0.3':
            C = 'nc'
        if isinstance(cloud,int) or isinstance(cloud,float):
            cloud = 'f{:1d}'.format(int(cloud))
        if cloud.lower() == 'hybrid':
            C = 'hybrid'
        elif cloud.lower() == 'f2':
            C = 'f2'
        elif cloud.lower() == 'nc' or cloud.lower() == 'nocloud' or cloud.lower() == 'noclouds' or cloud.lower() == 'cloud-free':
            C = 'nc'
        else:
            raise ValueError('\nCould not recognize cloud choice for Saumon model: must be cloud-free, hybrid or f2, not {}\n'.format(cloud))

        files = glob.glob(os.path.normpath(SPLAT_PATH+EVOLUTIONARY_MODEL_FOLDER+model+'/{}_{}_{}*.txt'.format(model,Z,C)))


#######################################################################

# read in parameters
    ages = [(f.split('_')[-1]).replace('.txt','') for f in files]

    mparam = {}
    mparam['name'] = model
    for ep in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
        mparam[ep] = []

#    for i,age in enumerate(ages):
#        mfile = prefix+'{:05d}.txt'.format(int(float(age)*1000.))
#        try:
#            dp=pandas.read_csv(SPLAT_PATH+EVOLUTIONARY_MODEL_FOLDER+mfile,comment='#',sep=',',header=0)
#            for ep in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
#                mparam[ep].append(dp[ep].values)

    for f in files:
        try:
            dp=pandas.read_csv(os.path.normpath(f),comment='#',sep=',',header=0)
            for ep in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
                mparam[ep].append(dp[ep].values)


# this is done in case models are not local - NOTE: currently just throwing an error
        except:
            raise ValueError('Could not find model file {} locally; aborting'.format(f))
#            try:
#                print('Could not read in model file {} locally; trying online'.format(mfile))
#                data =ascii.read(requests.get(SPLAT_URL+EVOLUTIONARY_MODEL_FOLDER+mfile).content,comment='#',delimiter='\t')
#            except: 
#                raise ValueError('Could not find model file {} locally or online; aborting'.format(mfile))

    mparam['age'] = [float(i)/1000. for i in ages]

    return mparam



def _modelParametersSingle(*args, **kwargs):
    '''
    :Purpose: Driver function for modelParameters_, performs actual interpolation of evolutionary models. See SPLAT API for `modelParameters()`_ for details.

    .. _`modelParameters()` : api.html#splat_evolve.modelParameters

    '''

    keywords = list(kwargs.keys())

# check that model is passed correctly
    try: model = args[0]
    except IndexError: 
        model = loadEvolModel('baraffe03')
        print('\nWarning: model error; using Baraffe et al. (2003) models by default\n')

# retool models to allow for logarithmic interpolation
    lmodel = copy.deepcopy(model)
# convert to logarithmic values
    lmodel['age'] = [numpy.log10(m) for m in lmodel['age']]
    for i in range(len(lmodel['age'])):
        lmodel['mass'][i] = [numpy.log10(m) for m in lmodel['mass'][i]]
        lmodel['temperature'][i] = [numpy.log10(m) for m in lmodel['temperature'][i]]
        lmodel['radius'][i] = [numpy.log10(m) for m in lmodel['radius'][i]]

# prep output parameters
    params = {}
#    for e in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):

    for e in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
        params[e] = 0.
        if e in keywords:
            try: f = float(kwargs[e])
            except: raise ValueError('\nInput parameter {} must be a single number, not {}\n'.format(e,kwargs[e]))
            finally: params[e] = f

    input_type = 'mass_age'
    Ag, Ma, Te, Le, Ge, Re, P = [],[],[],[],[],[],[]


    if kwargs.get('debug',False) == True: print(lmodel)

############### UNKNOWN MASS AND AGE - INTERPOLATE AGE FROM OTHER PARAMETERS #################
# for each age, interpolate mass as a function of first parameter and then second parameter as a function of mass
# and obtain second parameter as a function of age; then interpolate the model ages as a function of 
# the second parameter and evaluate for known parameter to get age
###############################################################################

# REVISED METHOD USING GRIDDATA    
    if (params['mass'] == 0.) and (params['age'] == 0.) and kwargs.get('alt',False) == False:

        Ma1, Ma2 = [], []
        input_type = 'two_params'
        if params['temperature'] != 0.:
            P.append(['temperature', numpy.log10(params['temperature'])])
        if params['gravity'] != 0.:
            P.append(['gravity', params['gravity']])
        if params['radius'] != 0.:
            P.append(['radius', numpy.log10(params['radius'])])
        if params['luminosity'] != 0.:
            P.append(['luminosity', params['luminosity']])

# create a grid to produce extract the mass and age
        points = []
        Ag, Ma = [], []

        for i,age in enumerate(lmodel['age']):
            if numpy.nanmin(lmodel[P[0][0]][i]) <= P[0][1] <= numpy.nanmax(lmodel[P[0][0]][i]) \
                and numpy.nanmin(lmodel[P[1][0]][i]) <= P[1][1] <= numpy.nanmax(lmodel[P[1][0]][i]):
                for j,m in enumerate(lmodel[P[0][0]][i]): 
                    points.append((lmodel[P[0][0]][i][j],lmodel[P[1][0]][i][j]))
                    Ag.append(age)
                Ma.extend(lmodel['mass'][i])

        if kwargs.get('debug',False) == True:
            pts = numpy.array(points)
            print('\n')
            print(pts,pts.shape)
            print('\n')
            print(Ag,len(Ag))
            print('\n')
            print(Ma,len(Ma))
            print('\n')
            print(P[0][1],P[1][1])

        try: 
            params['age'] = 10.**(griddata(numpy.array(points),Ag,numpy.array((P[0][1],P[1][1])),method='linear')[0])
        except: 
            params['age'] = float('nan')
        try: 
            params['mass'] = 10.**(griddata(numpy.array(points),Ma,numpy.array((P[0][1],P[1][1])),method='linear')[0])
        except: 
            params['mass'] = float('nan')

        if kwargs.get('debug',False) == True: print('\nMass and Age unknown; determined age to be {} and mass to be {}'.format(params['age'],params['mass']))
        Ge, Ag, Ma = [], [], []


# OLD WAY OF DOING THIS

    if (params['mass'] == 0.) and (params['age'] == 0.) and kwargs.get('alt',False) == True:

        input_type = 'two_params'
        if params['temperature'] != 0.:
            P.append(['temperature', numpy.log10(params['temperature'])])
        if params['gravity'] != 0.:
            P.append(['gravity', params['gravity']])
        if params['radius'] != 0.:
            P.append(['radius', numpy.log10(params['radius'])])
        if params['luminosity'] != 0.:
            P.append(['luminosity', params['luminosity']])

# compute for each age the appropriate mass for each parameter
        for i,age in enumerate(lmodel['age']):
            if numpy.nanmin(lmodel[P[0][0]][i]) <= P[0][1] <= numpy.nanmax(lmodel[P[0][0]][i]) \
                and numpy.nanmin(lmodel[P[1][0]][i]) <= P[1][1] <= numpy.nanmax(lmodel[P[1][0]][i]):
                Ag.append(age)
                f = interp1d(lmodel[P[0][0]][i], lmodel['mass'][i])
                Ma = f(P[0][1])
                f = interp1d(lmodel['mass'][i], lmodel[P[1][0]][i])
                Ge.append(f(Ma))

        try: 
            f = interp1d(Ge, Ag)
            params['age'] = 10.**f(P[1][1])
        except: 
            params['age'] = float('nan')
            if kwargs.get('debug',False) == True: 
                print('\nFailed:\nP = {}\nGe = {}\nAg = {}'.format(P,Ge,Ag))
                for a in Ag:
                    i = numpy.argmin(numpy.abs(numpy.array(lmodel['age'])-a))
                    print(a,i,numpy.nanmin(lmodel[P[0][0]][i]),P[0][1],numpy.nanmax(lmodel[P[0][0]][i]),numpy.nanmin(lmodel[P[1][0]][i]),P[1][1],numpy.nanmax(lmodel[P[1][0]][i]))
                    f = interp1d(lmodel[P[0][0]][i], lmodel['mass'][i])
                    Ma = f(P[0][1])
                    print(lmodel[P[0][0]][i],lmodel['mass'][i],Ma)
                    f = interp1d(lmodel['mass'][i], lmodel[P[1][0]][i])
                    print(lmodel[P[1][0]][i],lmodel['mass'][i],f(Ma))


        if kwargs.get('debug',False) == True: print('\nMass and Age unknown; determined age to be {}'.format(params['age']))
        Ge, Ag, Ma = [], [], []

################ UNKNOWN AGE BUT KNOWN MASS AND ONE OTHER PARAMETER ###########
# interpolate second parameter as a function of mass for each of the age models and evaluate for known mass
# interpolate the model ages as a fucntion of these parameters and evaluate for known parameter
###############################################################################
    if params['age'] == 0. and params['mass'] != 0. and \
        not numpy.isnan(params['mass']):

        if input_type != 'two_params': 
            input_type = 'one_param'
            if params['temperature'] != 0.:
                P.append(['temperature', numpy.log10(params['temperature'])])
            elif params['gravity'] != 0.:
                P.append(['gravity', params['gravity']])
            elif params['radius'] != 0.:
                P.append(['radius', numpy.log10(params['radius'])])
            elif params['luminosity'] != 0.:
                P.append(['luminosity', params['luminosity']])
            else:
                for k in list(params.keys()):
                    print('{}: {}'.format(k,params[k]))
                print(P)
                raise ValueError('\nProblem with one_param interpolation\n')

        for i,age in enumerate(lmodel['age']):
            if numpy.nanmin(lmodel['mass'][i]) <= numpy.log10(params['mass']) <= numpy.nanmax(lmodel['mass'][i]):
                Ag.append(age)
                f = interp1d(lmodel['mass'][i], lmodel[P[0][0]][i])
                Ge.append(f(numpy.log10(params['mass'])))

        try: 
            f = interp1d(Ge, Ag)
            params['age'] = 10.**f(P[0][1])
        except: 
            print('\nFailed in age + parameter determination\n')
            params['age'] = float('nan')

        if kwargs.get('debug',False) == True: print('\nMass known and Age unknown; determined age to be {}'.format(params['age']))

        Ge, Ag = [], []


################ KNOWN AGE BUT KNOWN MASS AND ONE OTHER PARAMETER ###########
# generate mass as function of second parameter interpolated between two closest age models
# evaluate mass(parameter) (resulting in both mass and age as knowns)
###############################################################################

    if params['age'] != 0. and params['mass'] == 0. and \
        not numpy.isnan(params['age']):

        if kwargs.get('debug',False) == True: print(params)

        if input_type != 'two_params' and input_type != 'one_param': 
            input_type = 'one_param'
            if params['temperature'] != 0.:
                P.append(['temperature', numpy.log10(params['temperature'])])
            elif params['gravity'] != 0.:
                P.append(['gravity', params['gravity']])
            elif params['radius'] != 0.:
                P.append(['radius', numpy.log10(params['radius'])])
            elif params['luminosity'] != 0.:
                P.append(['luminosity', params['luminosity']])
            else:
                for k in list(params.keys()):
                    print('{}: {}'.format(k,params[k]))
                print(P)
                raise ValueError('\nProblem with one_param interpolation\n')

        if numpy.log10(params['age']) < numpy.min(lmodel['age']) or \
            numpy.log10(params['age']) > numpy.max(lmodel['age']):
                print('\nAge of {} is outside range of models, {} to {}\n'.format(params['age'],10.**numpy.min(lmodel['age']),10**numpy.max(lmodel['age'])))
                params['mass'] = numpy.nan

        else:
            adiff = [numpy.log10(params['age'])-a for a in lmodel['age']]
            ai = numpy.argmin(numpy.abs(adiff))
            if adiff[ai] < 0:
                ai=ai-1
            for i,m in enumerate(lmodel['mass'][ai]):
                if m in lmodel['mass'][ai+1]:
                    Ma.append(m)
                    aj = numpy.argmin(numpy.abs([a-m for a in lmodel['mass'][ai+1]]))
                    vals = [lmodel[P[0][0]][ai][i],lmodel[P[0][0]][ai+1][aj]]
                    f = interp1d(lmodel['age'][ai:ai+2],vals)
                    Ge.append(f(numpy.log10(params['age'])))
            try:
                f = interp1d(Ge, Ma)
                params['mass'] = 10.**f(P[0][1])
            except:
                print('\nFailed in mass + parameter determination\n')
                params['mass'] = numpy.nan

        if kwargs.get('debug',False) == True: print('\nMass unknown and Age known; determined mass to be {}'.format(params['mass']))

        Ma, Ge = [],[]


###################### KNOWN MASS AND AGE #####################################
# generate parameters as a function of mass interpolated between two closest age models
# evaluate parameters(mass)
###############################################################################
    if params['mass'] != 0. and params['age'] != 0. and \
        not numpy.isnan(params['age']) and not numpy.isnan(params['mass']):

        if kwargs.get('debug',False) == True: print(params)

        for i,age in enumerate(lmodel['age']):
            if numpy.nanmin(lmodel['mass'][i]) <= numpy.log10(params['mass']) \
                                              <= numpy.nanmax(lmodel['mass'][i]):
                Ag.append(age)
                f =interp1d(lmodel['mass'][i],lmodel['temperature'][i])
                Te.append(float(f(numpy.log10(params['mass']))))
                f = interp1d(lmodel['mass'][i],lmodel['luminosity'][i])
                Le.append(float(f(numpy.log10(params['mass']))))
                f = interp1d(lmodel['mass'][i],lmodel['gravity'][i])
                Ge.append(float(f(numpy.log10(params['mass']))))
                f = interp1d(lmodel['mass'][i],lmodel['radius'][i])
                Re.append(float(f(numpy.log10(params['mass']))))
  
        if params['temperature'] == 0.:
            try:
                f = interp1d(Ag, Te)
                params['temperature'] = 10.**float(f(numpy.log10(params['age'])))
            except: 
                params['temperature'] = numpy.nan
        if params['luminosity'] == 0.:
            try: 
                f = interp1d(Ag, Le)
                params['luminosity'] = float(f(numpy.log10(params['age'])).item(0))
            except: 
                params['luminosity'] = numpy.nan
        if params['gravity'] == 0.:
            try: 
                f = interp1d(Ag, Ge) 
                params['gravity'] = float(f(numpy.log10(params['age'])).item(0))      
            except: 
                params['gravity'] = numpy.nan
        if params['radius'] == 0.:
            try: 
                f = interp1d(Ag, Re)
                params['radius'] = 10.**float(f(numpy.log10(params['age'])))
            except: 
                params['radius'] = numpy.nan
  
        if kwargs.get('debug',False) == True: print('\nDetermined parameters: {}'.format(params))

        return params


# something failed	  
    else:
#        print(params)
        for e in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
            params[e] = numpy.nan
        print('\nParameter set is not covered by model {}\n'.format(model['name']))
        return params
      


###############################################################################

def modelParameters(*model,**kwargs):
    '''
    :Purpose: Retrieves the evolutionary model parameters given two of the following parameters: mass, age, temperature, luminosity, gravity, or radius. The inputs can be individual values or arrays.  Using the input parameters, the associated evolutionary model parameters are computed through log-linear interpolation of the original model grid. Parameters that fall outside the grid return nan.

    Required Inputs:

    :param: model: Either a string of the name of the evolutionary model set, which can be one of `baraffe` (default), `burrows`, or `saumon`; or a dictionary output from `loadEvolModel()`_ containing model parameters. 
    
    and two (2) of the following:

    :param: mass: input value or list of values for mass (can also be `masses` or `m`)
    :param: age: input value or list of values for age (can also be `ages`, `time` or `a`)
    :param: temperature: input value or list of values for temperature (can also be `temperatures`, `teff`, `temp` or `t`)
    :param: gravity: input value or list of values for gravity (can also be `gravities`, `grav`, `logg` or `g`)
    :param: luminosity: input value or list of values for luminosity (can also be `luminosities`, `lum`, `lbol` or `l`)
    :param: radius: input value or list of values for radius (can also be `radii`, `rad` and `r`)

    .. _`loadEvolModel()` : api.html#splat_evolve.loadEvolModel

    Optional Inputs:

    :param: Parameters for `loadEvolModel()`_ may also be used.

    Output: 

    Dictionary containing keywords mass, age, temperature, luminosity, gravity, and radius, each linked to the evolutionary parameters retrieved. 


    :Example:
    >>> import splat, numpy
    >>> masses = numpy.random.uniform(0.01,0.1,20)
    >>> ages = numpy.random.uniform(0.01,10,20)
    >>> p = splat.modelParameters('baraffe',mass=masses,age=ages)
    You are using baraffe's models.
    >>> print(p.temperature)
    [ 2502.90132332  2818.85920306  1002.64227134  1330.37273021  1192.86976417
      500.45609068  2604.99966013  1017.03307609  1774.18267474  1675.12181635
      2682.9697321   2512.45223777   346.41152614  2066.19972036   843.28528456
      2264.93051445  2767.85660557   348.84214986   922.87030167  2669.27152307] K    
    '''

# read in model
    try: model = model[0]
    except IndexError: 
        if kwargs.get('model',False)==False:
            model = loadEvolModel('baraffe03')
        else: model=kwargs.get('model')
    if type(model) is not dict: model = loadEvolModel(model,**kwargs)
    if type(model) is not dict: raise ValueError('Something went wrong in loading in models')

    keywords = list(kwargs.keys())

# do some key word replacement
    mkwargs = {}
    for e in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
        if e in keywords:
            mkwargs[e] = kwargs[e]
    if 'temperature' not in keywords:
        if 't' in keywords:
            mkwargs['temperature'] = kwargs['t']
        if 'teff' in keywords:
            mkwargs['temperature'] = kwargs['teff']
        if 'temp' in keywords:
            mkwargs['temperature'] = kwargs['temp']
        if 'temperatures' in keywords:
            mkwargs['temperature'] = kwargs['temperatures']
    if 'gravity' not in keywords:
        if 'g' in keywords:
            mkwargs['gravity'] = kwargs['g']
        if 'logg' in keywords:
            mkwargs['gravity'] = kwargs['logg']
        if 'grav' in keywords:
            mkwargs['gravity'] = kwargs['grav']
        if 'gravities' in keywords:
            mkwargs['gravity'] = kwargs['gravities']
    if 'mass' not in keywords:
        if 'm' in keywords:
            mkwargs['mass'] = kwargs['m']
        if 'masses' in keywords:
            mkwargs['mass'] = kwargs['masses']
    if 'age' not in keywords:
        if 'time' in keywords:
            mkwargs['age'] = kwargs['time']
        if 'a' in keywords:
            mkwargs['age'] = kwargs['a']
        if 'ages' in keywords:
            mkwargs['age'] = kwargs['ages']
    if 'radius' not in keywords:
        if 'r' in keywords:
            mkwargs['radius'] = kwargs['r']
        if 'rad' in keywords:
            mkwargs['radius'] = kwargs['rad']
        if 'radii' in keywords:
            mkwargs['radius'] = kwargs['radii']
        if 'radiuses' in keywords:
            mkwargs['radius'] = kwargs['radiuses']
    if 'luminosity' not in keywords:
        if 'l' in keywords:
            mkwargs['luminosity'] = kwargs['l']
        if 'lum' in keywords:
            mkwargs['luminosity'] = kwargs['lum']
        if 'lbol' in keywords:
            mkwargs['luminosity'] = kwargs['lbol']
        if 'luminosities' in keywords:
            mkwargs['luminosity'] = kwargs['luminosities']


# determine length of input arrays and assert they must be pure numbers 
    inparams = {}
    inparams['debug'] = kwargs.get('debug',False)
    inparams['alt'] = kwargs.get('alt',False)
    inparams['verbose'] = kwargs.get('verbose',False)
    outparams = {}
    pkeys = list(mkwargs.keys())
    if len(pkeys) < 2:
        raise ValueError('\nNeed at least two parameters provided; only {} given: {}'.format(len(pkeys),pkeys))
    for p in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
        outparams[p] = []
        if p in pkeys:
            if isinstance(mkwargs[p],float) or isinstance(mkwargs[p],int):
                mkwargs[p] = [mkwargs[p]]
            if isUnit(mkwargs[p]):
                unit = mkwargs[p].unit
                mkwargs[p] = mkwargs[p].value
            if isUnit(mkwargs[p][0]):
                mkwargs[p] = [x*value for x in mkwargs[p]]
            numberValues = len(mkwargs[p])

# now loop through each parameter set to determine remaining parameters
    for i in range(numberValues):
        for p in pkeys:
            inparams[p] = mkwargs[p][i]
        par = _modelParametersSingle(model,**inparams)
        for p in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
            outparams[p].append(par[p])


# remove lists if only one parameter set is being calculated
    if len(outparams['temperature']) == 1:
        for e in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
            outparams[e] = outparams[e][0]

# add units
    for e in list(EVOLUTIONARY_MODEL_PARAMETERS.keys()):
        outparams[e] *= EVOLUTIONARY_MODEL_PARAMETERS[e]['unit']

    return outparams




def plotModelParameters(parameters,xparam,yparam,**kwargs):
    '''
    :Purpose: Plots pairs of physical star parameters and optionally compares to evolutionary model tracks. 

    Required Inputs:

    :param: parameters: dictionary or nested set of two arrays containing parameters to be plotted. For dictionary, keywords should include the `xparameter` and `yparameter` strings to be plotted. Values associated with keywords can be single numbers or arrays
    :param: xparam: string corresponding to the key in the `parameters` dictionary to be plot as the x (independent) variable. 
    :param: yparam: string corresponding to the key in the `parameters` dictionary to be plot as the y (dependent) variable. 


    Optional Inputs:

    .. _`loadEvolModel()` : api.html#splat_evolve.loadEvolModel

    :param: showmodel: set to True to overplot evolutionary model tracks from `model` (default = True)
    :param: model: either a string of the name of the evolutionary model set, one of  `baraffe` (default), `burrows`, or `saumon`; or a dictionary output from `loadEvolModel()`_ containing model parameters. 
    :param: tracks: string indicating what model tracks to show; can either be `mass` (default) or `age`


    :param: file: name of file to output plot (`output` can also be used)
    :param: show: set to True to show the plot onscreen (default = True)
    :param: figsize: a two-element array defining the figure size (default = [8,6])

    :param: color: color of data symbols (default = 'blue')
    :param: marker: matplotlib marker type for data symbols (default = 'o')
    :param: xlabel: string overriding the x-axis label (default = parameter name and unit)
    :param: ylabel: string overriding the y-axis label (default = parameter name and unit)
    :param: title: string specifying plot title (no title by default)
    :param: tight: set to True to tighten plot to focus on the data points (default = True)

    Output: 

    A matplotlib plot object. Optionally, can also show plot on screen or output plot to a file.

    :Example:
    >>> import splat, numpy
    >>> age_samp = 10.**numpy.random.normal(numpy.log10(1.),0.3,50)
    >>> mass_samp = numpy.random.uniform(0.001,0.1,50)
    >>> p = splat.modelParameters('baraffe',age=age_samp,mass=mass_samp)
    >>> splat.plotModelParameters(p,'age','temperature',showmodels=True,model='baraffe',show=True)
    [plot of temperature vs age for 50 data points with baraffe models overplotted]    
    '''
# check inputs
    if type(parameters) is not dict:
        if len(parameters) != 2:
            raise ValueError('\nInput parameters should be a dictionary or two-element list\n')
        else:
            param = {xparam: parameters[0], yparam: parameters[1]}
    else:
        param = copy.deepcopy(parameters)

    keys = list(param.keys())
    if xparam not in keys:
        raise ValueError('\nCould not find parameter {} in input dictionary\n'.format(xparam))
    if yparam not in keys:
        raise ValueError('\nCould not find parameter {} in input dictionary\n'.format(yparam))

    if isinstance(param[xparam],list) == False:
        param[xparam] = [param[xparam]]
    if isinstance(param[yparam],list) == False:
        param[yparam] = [param[yparam]]


# sort flags
    if xparam=='age' or xparam=='time' or xparam=='a':
        xmparam = 'age'
        xlogflag = True
    elif xparam=='mass' or xparam=='m':
        xmparam = 'mass'
        xlogflag = True
    elif xparam=='temperature' or xparam=='teff' or xparam=='t':
        xmparam = 'temperature'
        xlogflag = True
    elif xparam=='radius' or xparam=='r':
        xmparam = 'radius'
        xlogflag = True
    elif xparam=='gravity' or xparam=='logg' or xparam=='g':
        xmparam = 'gravity'
        xlogflag = False
    elif xparam=='luminosity' or xparam=='lbol' or xparam=='l':
        xmparam = 'luminosity'
        xlogflag = False
    else:
        raise ValueError('\nx-axis parameter {} is not one that can be plotted'.format(xparam))

    if yparam=='age' or yparam=='time' or yparam=='a':
        ymparam = 'age'
        ylogflag = True
    elif yparam=='mass' or yparam=='m':
        ymparam = 'mass'
        ylogflag = True
    elif yparam=='temperature' or yparam=='teff' or yparam=='t':
        ymparam = 'temperature'
        ylogflag = True
    elif yparam=='radius' or yparam=='r':
        ymparam = 'radius'
        ylogflag = True
    elif yparam=='gravity' or yparam=='logg' or yparam=='g':
        ymparam = 'gravity'
        ylogflag = False
    elif yparam=='luminosity' or yparam=='lbol' or yparam=='l':
        ymparam = 'luminosity'
        ylogflag = False
    else:
        raise ValueError('\ny-axis parameter {} is not one that can be plotted'.format(yparam))

# plot parameters
    plt.close('all')
    plt.figure(figsize=kwargs.get('figsize',[8,6]))
    if xlogflag == True and ylogflag == True:
        plt.loglog(param[xparam],param[yparam],color=kwargs.get('color','blue'),marker=kwargs.get('marker','o'))
    elif xlogflag == False and ylogflag == True:
        plt.semilogy(param[xparam],param[yparam],color=kwargs.get('color','blue'),marker=kwargs.get('marker','o'))
    elif xlogflag == True and ylogflag == False:
        plt.semilogx(param[xparam],param[yparam],color=kwargs.get('color','blue'),marker=kwargs.get('marker','o'))
    else:
        plt.plot(param[xparam],param[yparam],color=kwargs.get('color','blue'),marker=kwargs.get('marker','o'))

# read in models to display   
    if kwargs.get('showmodel',True) != False or kwargs.get('showmodels',True) != False:
        if kwargs.get('model',False) == False:
            model = 'baraffe03'
        else:
            model = kwargs.get('model')
        try:
            if type(model) is not dict: model = loadEvolModel(model,**kwargs)
        except:
            print('\nProblem in reading in original models\n')
            kwargs['showmodel'] = False

# models tracks (mass by default)
        tracks = kwargs.get('tracks',['mass'])
        if isinstance(tracks,bool):
            if tracks == True: 
                tracks = ['mass','age']
            else:
                tracks = ['']
        if tracks == 'all': tracks = ['mass','age']
        if not isinstance(tracks,list): tracks = [tracks]
        tracks = [t.lower() for t in tracks]

        if 'mass' in tracks:
            xvals, yvals, masses = [], [], []
            for i in model['mass']:
                masses.extend(i)
            masses.sort()
            tvals = numpy.unique(masses)
            for j,m in enumerate(tvals):
                xx,yy = [],[]
                for i,x in enumerate(model['age']):
                    if m in model['mass'][i]:
                        if xmparam != 'age':
                            xx.append(numpy.array(model[xmparam][i])[numpy.where(model['mass'][i]==m)].item(0))
                        else:
                            xx.append(x)
                        if ymparam != 'age':
                            yy.append(numpy.array(model[ymparam][i])[numpy.where(model['mass'][i]==m)].item(0))
                        else:
                            yy.append(x)
                    else:
                        xx.append(numpy.nan)
                        yy.append(numpy.nan)                        
                xvals.append(xx)
                yvals.append(yy)

            for i,x in enumerate(xvals):
                if xlogflag == True and ylogflag == True:
                    plt.loglog(xvals[i],yvals[i],color='grey',linestyle='-')
                elif xlogflag == False and ylogflag == True:
                    plt.semilogy(xvals[i],yvals[i],color='grey',linestyle='-')
                elif xlogflag == True and ylogflag == False:
                    plt.semilogx(xvals[i],yvals[i],color='grey',linestyle='-')
                else:
                    plt.plot(xvals[i],yvals[i],color='grey',linestyle='-')

# models tracks trace isochrones
        if 'age' in tracks:
            xvals, yvals = [], []
            tvals = model['age']
# fix to account for unequal lengths of model values
            maxlen = numpy.max([len(a) for a in model['mass']])
            for i,x in enumerate(tvals):
                t = numpy.zeros(maxlen)
                t.fill(numpy.nan)
                if xparam != 'age':
                    t[0:len(model[xparam][i])] = model[xmparam][i]
                else:
                    t.fill(x)
                xvals.append(t.tolist())
                s = numpy.zeros(maxlen)
                s.fill(numpy.nan)
                if yparam != 'age':
                    s[0:len(model[yparam][i])] = model[ymparam][i]
                else:
                    s.fill(x)
                yvals.append(s.tolist())

# plot them
            for i,x in enumerate(xvals):
                if xlogflag == True and ylogflag == True:
                    plt.loglog(xvals[i],yvals[i],color='grey',linestyle='--')
                elif xlogflag == False and ylogflag == True:
                    plt.semilogy(xvals[i],yvals[i],color='grey',linestyle='--')
                elif xlogflag == True and ylogflag == False:
                    plt.semilogx(xvals[i],yvals[i],color='grey',linestyle='--')
                else:
                    plt.plot(xvals[i],yvals[i],color='grey',linestyle='--')

# add labels
    plt.xlabel(kwargs.get('xlabel','{} ({})'.format(xmparam,EVOLUTIONARY_MODEL_PARAMETERS[xmparam]['unit'])))
    plt.ylabel(kwargs.get('ylabel','{} ({})'.format(ymparam,EVOLUTIONARY_MODEL_PARAMETERS[yparam]['unit'])))
    if kwargs.get('title',False) != False:
        plt.title(kwargs.get('title'))
# tighten plot
    if kwargs.get('tight',True) == True:
        xrng = [numpy.nanmin(param[xparam]),numpy.nanmax(param[xparam])]
        if xlogflag ==True:
            xsep = xrng[1]/xrng[0]
            if xsep != 1.:
                plt.xlim([xrng[0]/(xsep**0.1),xrng[1]*(xsep**0.1)])
        else:
            xsep = xrng[1]-xrng[0]
            if xsep != 0.:
                plt.xlim([xrng[0]-0.05*xsep,xrng[1]+0.05*xsep])
        yrng = [numpy.nanmin(param[yparam]),numpy.nanmax(param[yparam])]
        if ylogflag ==True:
            ysep = yrng[1]/yrng[0]
            if ysep != 1.:
                plt.ylim([yrng[0]/(ysep**0.1),yrng[1]*(ysep**0.1)])
        else:
            ysep = yrng[1]-yrng[0]
            if ysep != 0.:
                plt.ylim([yrng[0]-0.05*ysep,yrng[1]+0.05*ysep])

# save the plot or display
    file = kwargs.get('file',False)
    file = kwargs.get('output',file)
    if file != False:
        plt.savefig(file)
    elif kwargs.get('show',True) == True:
        plt.show()
    else:
        pass

    return plt



def simulateAges(num,**kwargs):
    '''
    :Purpose: Generates a distribution of ages based on the defined input distribution. 

    Required Inputs:

    :param: num: number of ages to generate

    Optional Inputs:

    :param: age_range: range of ages to draw from (default = [0.1,10.]); can also specify `range`, `minage` or `min`, and `maxage` or `max`
    :param: distribution: either a string set to one of the following to define the type of age distribution (or reverse star formation rate) desired:
        * `uniform`: uniform distribution (default) 
        * `exponential`: exponential age distribution, P(t) ~ e\^(beta x t). You can specify the parameters `beta` or `tau` = 1/beta, or set ``distribution`` to `aumer` or `miller`
        * `double_exponential`: double exponential age distribution, P(t) ~ Ae\^(lambda x t) + e\^(beta x t). You can specify the parameters `beta`, `lambda` and `a` or set ``distribution`` to `aumer_double` (default parameters)
        * `cosmic` or `rujopakarn`: cosmic age distribution with P(t) ~ (1+z(t))\^alpha, where z is the redshift, which is converted to time using the Planck 2015 cosmology. You can specify the parameter `alpha` or set ``distribution`` to `rujopakarn` (default parameters)
        * `peaked`: age distribution that peaks at some early time, written in the form P(t) ~ (t-t0)/(t\^2+t1\^2)\^2. You can specify the parameters `t0` and `t1` or set ``distribution`` to `aumer_peaked` or `just_peaked`
        * `aumer` or `aumer_exponential`: exponential age distribution with parameters from Aumer & Binney (2009): beta = 0.117
        * `aumer_double`: double exponential age distribution with parameters from Aumer & Binney (2009): beta = 0.348, lambda = 2.0, a = 1.e-8
        * `aumer_peaked`: peaked age distribution with parameters from Aumer & Binney (2009): t0 = XXX, t1 = XXX
        * `just` or `just_exponential: exponential age distribution with parameters from Just & Jahriess (2010): beta = 0.125
        * `just_peaked_a`: peaked age distribution with parameters from Just & Jahriess (2010) Model A: t0 = 5.6, t1 = 8.2
        * `just_peaked` or `just_peaked_b`: peaked age distribution with parameters from Just & Jahriess (2010) Model B: t0 = 1.13, t1 = 7.8
        * `miller`: exponential age distribution with parameters from Miller & Scalo (1979): beta = max age / 2
        * `rujopakarn`: cosmic age distribution with parameters from Rujopakarn et al. (2010): beta = max age / 2
        * `input`: user specified age distribution or star formation history; ``input`` must be set to a 2 x N array specifying age and distribution
    :param: distribution can also be set to a 2 x N array specifying an age distribution or star formation history; the first vector should be the ages for the function and the second vector the distribution function
    :param: parameters: dictionary containing the parameters for the age distribution/star formation model being used; options include:
        * `alpha`: power law factor for cosmic age distribution
        * `beta`: power factor in exponential age distribution; positive beta implies a star formation rate that decreases with time
        * `lambda`: second power factor in double exponential age distribution; positive lambda implies a star formation rate that decreases with time
        * `a`: relative scale factor for second exponential in double exponential age distribution
        * `tau`: 1/beta scale factor in exponential age distribution
        * `t0` and `t1`: parameters for peaked age distribution
    :param: sfh: set to True if distribution is a star formation history rather than an age distribution (default = False)
    :param: verbose: Give feedback (default = False)

    Output: 

    An array of ages drawn from the desired distribution in units of Gyr

    :Example:
    >>> import splat
    >>> import matplotlib.pyplot as plt
    >>> ages = splat.simulateAges(10000,distribution='aumer',age_range=[0.3,8.0])
    >>> plt.hist(ages)
    [histogram of ages in range 0.3-8.0 Gyr]    
    '''

# initial parameters
    distribution = kwargs.get('distribution','uniform')
    allowed_distributions = ['uniform','flat','exponential','double-exponential','peaked','cosmic','aumer','aumer-double','aumer-peaked','just','just_exponential','just-peaked','just-peaked-a','just-peaked-b','miller','rujopakarn']
    mn = kwargs.get('minage',0.1)
    mn = kwargs.get('min',mn)
    mx = kwargs.get('maxage',10.)
    mx = kwargs.get('max',mx)
    sfh = kwargs.get('sfh',False)
    age_range = kwargs.get('age_range',[mn,mx])
    age_range = kwargs.get('range',age_range)
    verbose = kwargs.get('verbose',False)
    if distribution.lower() not in allowed_distributions:
        raise ValueError('No distribution named {} in code; try one of the following: {}'.format(distribution,allowed_distributions))

# protective offset
    if age_range[0] == age_range[1]:
        age_range[1]+=0.0001
# set default parameters
    if kwargs.get('parameters',False) == False:
        parameters = {}
    else:
        parameters = kwargs['parameters']
    if 'beta' not in list(parameters.keys()):
        parameters['beta'] = 1.0
    if 'tau' not in list(parameters.keys()):
        parameters['tau'] = 1./parameters['beta']
    if 'alpha' not in list(parameters.keys()):
        parameters['alpha'] = 3.5
    if 'lambda' not in list(parameters.keys()):
        parameters['lambda'] = 2.0
    if 'a' not in list(parameters.keys()):
        parameters['a'] = 1.e-8
    if 't0' not in list(parameters.keys()):
        parameters['t0'] = 1.13
    if 't1' not in list(parameters.keys()):
        parameters['t1'] = 7.8

# 
# exponential
    if distribution.lower() == 'exponential' or distribution.lower() == 'aumer' or distribution.lower() == 'miller' or distribution.lower() == 'just' or distribution.lower() == 'just_exponential':
        if verbose: print('using exponential distribution')
        if distribution.lower() == 'aumer':
            parameters['beta'] = 0.117
        if distribution.lower() == 'miller':
            parameters['beta'] = 0.5*numpy.max(age_range)
        if distribution.lower() == 'just' or distribution.lower() == 'just_exponential':
            parameters['beta'] = 0.125

# use CDF sampling
        if parameters['beta'] != 0.:
            x = numpy.linspace(numpy.min(age_range),numpy.max(age_range),num=10000)
            y = numpy.exp(parameters['beta']*x)
            y -= numpy.min(y)
            y /= numpy.max(y)
            f = interp1d(y,x)
            ages = f(numpy.random.uniform(size=num))
        else:
            ages = numpy.random.uniform(numpy.min(age_range), numpy.max(age_range), size=num)

# double exponential
    elif distribution.lower() == 'double_exponential' or distribution.lower() == 'aumer_double':
        if verbose: print('using double exponential distribution')
        if distribution.lower() == 'aumer_double':
            parameters['beta'] = 0.348
            parameters['lambda'] = 2.0
            parameters['a'] = 1.e-8

# use CDF sampling
        x = numpy.linspace(numpy.min(age_range),numpy.max(age_range),num=10000)
        y = parameters['a']*numpy.exp(parameters['lambda']*x) + numpy.exp(parameters['beta']*x)
        y -= numpy.min(y)
        y /= numpy.max(y)
        f = interp1d(y,x)
        ages = f(numpy.random.uniform(size=num))

# peaked distribution
    elif distribution.lower() == 'peaked' or distribution.lower() == 'just_peaked' or distribution.lower() == 'just_peaked_a' or distribution.lower() == 'just_peaked_b' or distribution.lower() == 'aumer_peaked':
        if verbose: print('using peaked distribution')
# Aumer & Binney 2009
        if distribution.lower() == 'aumer_peaked':
            parameters['t0'] = 0.
            parameters['t1'] = 7.23
# Just & Jahriess 2010 Model A
        if distribution.lower() == 'just_peaked_a':
            parameters['t0'] = 5.6
            parameters['t1'] = 8.2
            sfh = True
# Just & Jahriess 2010 Model B (default)
        if distribution.lower() == 'just_peaked' or distribution.lower() == 'just_peaked_b':
            parameters['t0'] = 1.13
            parameters['t1'] = 7.8
            sfh = True

# generate CDF by integration and then do CDF sampling
# note that function is slightly different for the two forms
        x = numpy.linspace(numpy.min(age_range),numpy.max(age_range),num=10000)
        if 'just' in distribution:
            y = (x+parameters['t0'])/((x**2+parameters['t1']**2)**2)
#            print(2./3.*(t0**2+0.75*t1**2)**0.5 - 2./3.*t0)
        else:
            y = (14.-x+parameters['t0'])/(((14.-x)**2+parameters['t1']**2)**2)
#            print(14.-2./3.*(t0**2+0.75*t1**2)**0.5 - 2./3.*t0)
        yc = numpy.cumsum(y)
        yc -= numpy.min(yc)
        yc /= numpy.max(yc)
        f = interp1d(yc,x)
        ages = f(numpy.random.uniform(size=num))

# cosmic star formation rate
    elif distribution.lower() == 'cosmic' or distribution.lower() == 'rujopakarn': 
        if verbose: print('using cosmic SFH distribution')
        if distribution.lower() == 'rujopakarn': 
            parameters['alpha'] = 3.5

        cosmo = Planck15    # in case we want to change later
        zrng = [z_at_value(cosmo.lookback_time,numpy.min(age_range)*u.Gyr),z_at_value(cosmo.lookback_time,numpy.max(age_range)*u.Gyr)]
# use CDF sampling
        x = numpy.linspace(numpy.min(zrng),numpy.max(zrng),num=10000)
        y = (x+1.)**parameters['alpha']
        y -= numpy.min(y)
        y /= numpy.max(y)
        f = interp1d(y,x)
        z = f(numpy.random.uniform(size=num))
        ages = cosmo.lookback_time(z)

# uniform distribution (default)
    elif distribution.lower() == 'uniform' or distribution.lower() == 'flat': 
        if verbose: print('using uniform distribution')
        ages = numpy.random.uniform(numpy.min(age_range), numpy.max(age_range), size=num)

    else:
        return ValueError('Did not recognize distribution {}'.format(distribution))

    if sfh:
        if verbose: print('reversing ages (SFH)')
        ages = numpy.max(ages)-ages

    return ages



def simulateMasses(num,**kwargs):
    '''
    :Purpose: Generates a distribution of masses based on the defined input distribution. 

    Required Inputs:

    :param: num: number of masses to generate

    Optional Inputs:

    :param: mass_range: range of masses to draw from (default = [0.01,0.1]); can also specify ``range``, ``minmass`` or ``min``, and ``maxmass`` or ``max``
    :param: distribution: can be a string set to one of the following to define the type of mass distribution to sample:
        * `uniform`: uniform distribution (default) 
        * `powerlaw` or `power-law`: single power-law distribution, P(M) ~ M\^-alpha. You must specify the parameter `alpha` or set ``distribution`` to TBD
        * `broken-powerlaw' or `broken-power-law: a broken power-law distribution; segments are specified by the parameters `alpha` (N array of numbers) for the slopes and `ranges` (N array of 2-element arrays) for the ranges over which these slopes occur; if the `scales` parameter is also included, the power-law segments are scaled by these factors; otherwise, the segments are forced to be continuous. You can also set ``distribution`` to `kroupa`
        * 'lognormal` or `log-normal`: log normal distribution, P(M) ~ exp(-0.5*(M-M0)\^2/sigmaM^2). You must specify the parameters `M0` and `sigmaM` or set ``distribution`` to `chabrier` (default parameters)
        * `kroupa`: broken power-law distribution with parameters from Kroupa (2001): `http://adsabs.harvard.edu/abs/2001MNRAS.322..231K`_
        * `chabrier`: lognormal distribution with parameters from Chabrier (2003): `http://adsabs.harvard.edu/abs/2003PASP..115..763C`_
    :param: distribution can also be set to a 2 x N array specifying the mass distribution; the first vector should be the masses for the distribution function and the second vector the distribution function itself
    :param: parameters: dictionary containing the parameters for the age distribution/star formation model being used; options include:
        * `alpha`: exponent for power-law distribution, or array of numbers giving power-law factors for broken power-law distribution
        * `range`: array of 2-element arrays specifying the masses (in units of solar masses) over which the broken-law slopes are defined
        * `scales`: array of numbers specifying relative scaling between the segments in the broken-law distribution
        * `M0` and `sigmaM: parameters for lognormal distribution in units of solar masses
    :param: verbose: Give feedback (default = False)

    Output: 

    An array of masses drawn from the desired distribution in units of solar masses

    :Example:
    >>> import splat
    >>> import matplotlib.pyplot as plt
    >>> masses = splat.simulateMasses(10000,distribution='power-law',parameters={'alpha': 0.5},mass_range=[0.01,0.08])
    }
    >>> plt.hist(masses)
    [histogram of masses in range 0.01-0.08 solar masses]    
    '''

# initial parameters
    distribution = kwargs.get('distribution','powerlaw')
    allowed_distributions = ['uniform','flat','powerlaw','power-law','broken-powerlaw','broken-power-law','lognormal','log-normal','kroupa','chabrier','salpeter']
    mn = kwargs.get('minmass',0.01)
    mn = kwargs.get('min',mn)
    mx = kwargs.get('maxmass',0.1)
    mx = kwargs.get('max',mx)
    mass_range = kwargs.get('mass_range',[mn,mx])
    mass_range = kwargs.get('range',mass_range)
    verbose = kwargs.get('verbose',False)

# protective offset
    if mass_range[0] == mass_range[1]:
        mass_range[1]+=0.0001

# set default parameters
    if kwargs.get('parameters',False) == False:
        parameters = {}
    else:
        parameters = kwargs['parameters']
    if 'alpha' not in list(parameters.keys()):
        parameters['alpha'] = kwargs.get('alpha',0.5)
    if 'alpha-broken' not in list(parameters.keys()):
        parameters['alpha-broken'] = kwargs.get('alpha-broken',[0.3,1.3,2.3])
    if 'mass-broken' not in list(parameters.keys()):
        parameters['mass-broken'] = kwargs.get('mass-broken',[0.08,0.5])
    if 'log-mu' not in list(parameters.keys()):
        parameters['log-mu'] = kwargs.get('log-mu',numpy.log(0.079))
    if 'log-sigma' not in list(parameters.keys()):
        parameters['log-sigma'] = kwargs.get('log-sigma',0.69)

# power-law - sample from CDF
    if distribution.lower() == 'power-law' or distribution.lower() == 'powerlaw' or distribution.lower() == 'salpeter':
        if distribution.lower() == 'salpeter': parameters['alpha'] = 2.35
        x = numpy.linspace(numpy.min(mass_range),numpy.max(mass_range),num=10000)
        if parameters['alpha'] == 1.:
            y = numpy.log(x)
        else:
            y = x**(1.-parameters['alpha'])
#        print(x,y)
        y -= numpy.min(y)
        y /= numpy.max(y)
        f = interp1d(y,x)
#        plt.plot(x,y)
        masses = f(numpy.random.uniform(size=num))

# lognormal - this doesn't quite work?
    elif distribution.lower() == 'lognormal' or distribution.lower() == 'log-normal':
        masses = numpy.random.lognormal(parameters['log-mu'], parameters['log-sigma'], num)


# broken power law
    elif distribution.lower() == 'kroupa' or distribution.lower() == 'broken-power-law' or distribution.lower() == 'broken-powerlaw':
        if distribution.lower() == 'kroupa':
            alphas = numpy.array([0.3,1.3,2.3])
            mbs = numpy.array([0.08,0.5])
        else:
            alphas = numpy.array(parameters['alpha-broken'])
            mbs = numpy.array(parameters['mass-broken'])
        if len(alphas)-1 != len(mbs):
            raise ValueError('\nBroken Power Law should have one more alpha parameter than mass break parameter; your values are alpha = {} and masses = {}'.format(parameters['alpha-broken'],parameters['mass-broken']))
        yfull = []
        xfull = []
        mlow = numpy.min(mass_range)
        for i,mb in enumerate(mbs):
            if mlow < mb and mlow < numpy.max(mass_range):
#                print(mb,mlow,numpy.min([mb,numpy.max(mass_range)]))
                x = numpy.linspace(mlow,numpy.min([mb,numpy.max(mass_range)]),num=10000)
                y = x**(-1.*alphas[i])
                if len(yfull) > 0: y *= yfull[-1]/y[0]
                yfull.extend(y)
                xfull.extend(x)
                mlow = mb
# last mass range                
        if mlow < numpy.max(mass_range):
#            print(mlow,numpy.max(mass_range))
            x = numpy.linspace(mlow,numpy.max(mass_range),num=10000)
            y = x**(-1.*alphas[-1])
            if len(yfull) > 0: y *= yfull[-1]/y[0]
            yfull.extend(y)
            xfull.extend(x)
#        plt.loglog(xfull,[a+10 for a in yfull])
#        plt.ylim([7,10])
#        plt.show()
        xf = numpy.linspace(mass_range[0],mass_range[1],num=10000)
        f = interp1d(xfull,yfull)
        yf = f(xf)
        yf -= numpy.min(yf)
        yc = numpy.cumsum(yf)
        yc -= numpy.min(yc)
        yc /= numpy.max(yc)
#        plt.plot(xfull,yc)
#        plt.ylim([7,10])
#        plt.show()
        f = interp1d(yc,xf)
        masses = f(numpy.random.uniform(size=num))

# Chabrier (2005) distribution
    elif 'chabrier' in distribution.lower():
# lognormal below 1 solar mass
        yfull = []
        xfull = []
        if numpy.min(mass_range) < 1.0:
            xfull = numpy.linspace(numpy.min(mass_range),numpy.min([numpy.max(mass_range),1.0]),num=10000)
#            yfull = stats.lognorm.pdf(xfull/0.079,0.69)
            if 'system' in distribution.lower():
                yfull = numpy.exp(-0.5*((numpy.log10(xfull)-numpy.log10(0.22))/0.57)**2)/xfull
                mcut = 1.0
            elif 'globular' in distribution.lower():
                yfull = numpy.exp(-0.5*((numpy.log10(xfull)-numpy.log10(0.33))/0.34)**2)/xfull
                mcut = 0.9
            elif 'halo' in distribution.lower():
                yfull = numpy.exp(-0.5*((numpy.log10(xfull)-numpy.log10(0.22))/0.33)**2)/xfull
                mcut = 0.7
            else:
                yfull = numpy.exp(-0.5*((numpy.log10(xfull)-numpy.log10(0.079))/0.69)**2)/xfull
                mcut = 1.0
# salpeter or broken power law above this
        if numpy.max(mass_range) > mcut:
            mbs = [numpy.max([numpy.min(mass_range),mcut]),numpy.max(mass_range)]
            alphas = [2.3]
            if 'broken' in distribution.lower():
                mbs = numpy.array([numpy.max([numpy.min(mass_range),mcut]),10.**0.54,10.**1.26,10.**1.80])
                alphas = numpy.array([5.37,4.53,3.11])
                mbs = mbs[numpy.where(mbs < numpy.max(mass_range))]
                if len(mbs) <= len(alphas): 
                    mbs = numpy.append(mbs,numpy.max(mass_range))
                else:
                    mbs[-1] = numpy.max(mass_range)
            for iii in range(len(mbs)-1):
                x = numpy.linspace(mbs[iii],mbs[iii+1],num=10000)
                y = numpy.array(x**(-1.*alphas[iii]))
                if len(yfull) > 0:
                    y *= yfull[-1]/y[0]
                    yfull = numpy.append(yfull,y)
                    xfull = numpy.append(xfull,x)
                else:
                    yfull = y
                    xfull = x
        f = interp1d(xfull,yfull)
        xf = numpy.linspace(mass_range[0],mass_range[1],num=10000)
        yf = f(xf)
        yf -= numpy.min(yf)
        yc = numpy.cumsum(yf)
        yc -= numpy.min(yc)
        yc /= numpy.max(yc)
        f = interp1d(yc,xf)
        masses = f(numpy.random.uniform(size=num))

# uniform distribution (default)
    elif distribution.lower() == 'uniform' or distribution.lower() == 'flat':
        masses = numpy.random.uniform(numpy.min(mass_range), numpy.max(mass_range), size=num)

# wrong distribution
    else:
        raise NameError('\n{} distribution is not recognized; please choose from {}'.format(distribution,allowed_distributions))

    return masses


def simulateMassRatios(num,**kwargs):
    '''
    :Purpose: Generates a distribution of mass ratios (q = M2/M1) based on the defined input distribution. It is assumed that q <= 1

    Required Inputs:

    :param: num: number of masses to generate

    Optional Inputs:

.. _Allen (2007), ApJ 668, 492: http://adsabs.harvard.edu/abs/2007ApJ...668..492A
.. _Burgasser et al (2006), ApJS 166, 585: http://adsabs.harvard.edu/abs/2006ApJS..166..585B

    :param: q_range: range of masses to draw from (default = [0.1,1.0]); can also specify ``range``, ``minq`` or ``min``, and ``maxq`` or ``max``
    :param: distribution: can be a string set to one of the following to define the type of mass distribution to sample:
        * `uniform`: uniform distribution (default) 
        * `powerlaw` or `power-law`: single power-law distribution, P(M) ~ M\^-alpha. You must specify the parameter `alpha` or set ``distribution`` to TBD
        * `allen`: power-law distribution with gamma = -1.8 based on `Allen (2007), ApJ 668, 492`_
        * `burgasser`: power-law distribution with gamma = -4.2 based on `Burgasser et al (2006), ApJS 166, 585`_
    :param: parameters: dictionary containing the parameters for the age distribution/star formation model being used; options include:
        * `gamma`: exponent for power-law distribution
    :param: verbose: Give feedback (default = False)

    Output: 

    An array of mass ratios drawn from the desired distribution 

    :Example:
    >>> import splat
    >>> import matplotlib.pyplot as plt
    >>> q = splat.simulateMassRatios(100,distribution='allen'),q_range=[0.2,1.0])
    }
    >>> plt.hist(q)
    [histogram of mass ratios in the range 0.2-1.0 solar masses]    
    '''

# initial parameters
    allowed_distributions = ['uniform','flat','powerlaw','power-law','allen']
    distribution = kwargs.get('distribution','uniform')
    mn = kwargs.get('minq',0.1)
    mn = kwargs.get('min',mn)
    mx = kwargs.get('maxq',1.)
    mx = kwargs.get('max',mx)
    q_range = kwargs.get('q_range',[mn,mx])
    q_range = kwargs.get('range',q_range)
    verbose = kwargs.get('verbose',False)

# protective offset
    if q_range[0] == q_range[1]:
        q_range[0]-=0.0001

# set default parameters
    if kwargs.get('parameters',False) == False:
        parameters = {}
    else:
        parameters = kwargs['parameters']
    if 'gamma' not in list(parameters.keys()):
        parameters['gamma'] = kwargs.get('gamma',1.8)

# power-law - sample from CDF
    if distribution.lower() == 'power-law' or distribution.lower() == 'powerlaw' or distribution.lower() == 'allen' or distribution.lower() == 'burgasser':
        if distribution.lower() == 'allen' or kwargs.get('allen',False) == True: parameters['gamma'] = 1.8
        if distribution.lower() == 'burgasser' or kwargs.get('burgasser',False) == True: parameters['gamma'] = 4.2
        x = numpy.linspace(numpy.min(q_range),numpy.max(q_range),num=10000)
        if parameters['gamma'] == 1.:
            y = numpy.log(x)
        else:
            y = x**(1.+parameters['gamma'])
#        print(x,y)
        y -= numpy.min(y)
        y /= numpy.max(y)
        f = interp1d(y,x)
#        plt.plot(x,y)
        q = f(numpy.random.uniform(size=num))

# uniform distribution (default)
    elif distribution.lower() == 'uniform' or distribution.lower() == 'flat':
        q = numpy.random.uniform(numpy.min(q_range), numpy.max(q_range), size=num)

# wrong distribution
    else:
        raise NameError('\n{} distribution is not recognized; please choose from {}'.format(distribution,allowed_distributions))

    return q


def simulateSpatialDistribution(**kwargs):
    pass    

def simulateBinaryOrbits(**kwargs):
    pass    

def simulateGalacticOrbits(**kwargs):
    pass    

def simulateUVW(ages,**kwargs):
    '''
    :Purpose: Generates a distribution of U, V and W velocities for a population of stars with given ages
    Currently this only includes the velocity dispersions of Aumer et al. 2009

    Required Inputs:

    :param: ages: array of ages in units of Gyr

    Optional Inputs:

    :param: verbose: Give feedback (default = False)

    Output: 

    Three arrays of U, V and W in units of km/s, defined on a right-hand coordinate system centered on the Sun
    Note that these are defined in the model's local standard of rest

    :Example:
    >>> import splat.evolve as spev
    >>> import numpy
    >>> ages = spev.simulateAges(1000,distribution='cosmic')
    >>> u,v,w = spev.simulateKinematics(ages)
    >>> print('sU = {:.2f}, sV = {:.2f}, sW = {:.2f}, mV = {:.2f}'.format(numpy.std(u),numpy.std(v),numpy.std(w),numpy.mean(v)))
        sU = 39.15 km / s, sV = 27.47 km / s, sW = 21.01 km / s, mV = -20.46 km / s
    '''

# u velocity
    v10 = 41.899
    tau1 = 0.001
    beta = 0.307
    sig = v10*((numpy.array(ages)+tau1)/(10.+tau1))**beta
    uvel = numpy.random.normal(numpy.zeros(len(ages)),sig)

# v velocity - firs offset
    k = 74.
    voff = -1.*(sig**2)/k
# now compute scatter    
    v10 = 28.823
    tau1 = 0.715
    beta = 0.430
    sig = v10*((numpy.array(ages)+tau1)/(10.+tau1))**beta
    vvel = numpy.random.normal(voff,sig)

# w velocity
    v10 = 23.381
    tau1 = 0.001
    beta = 0.445
    sig = v10*((numpy.array(ages)+tau1)/(10.+tau1))**beta
    wvel = numpy.random.normal(numpy.zeros(len(ages)),sig)

    return uvel*u.km/u.s, vvel*u.km/u.s, wvel*u.km/u.s

def simulatePhotometry(**kwargs):
    pass    


def simulatePopulation(**kwargs):

    parameters = {}

# draw ages - DONE
    age_kwargs = kwargs.get('age_parameters',{})
    parameters['age'] = simulateAges(num,**age_kwargs)

# draw masses - DONE
    mass_kwargs = kwargs.get('mass_parameters',{})
    parameters['mass'] = simulateMasses(num,**mass_kwargs)

# extract evolutionary model parameters
    model_kwargs = kwargs.get('model_parameters',{})
    mp = modelParameters(mass=parameters['mass'],age=parameters['age'],**model_kwargs)
    parameters['gravity'] = mp['gravity']
    parameters['luminosity'] = mp['luminosity']
    parameters['radius'] = mp['radius']
    parameters['temperature'] = mp['temperature']

# determine spectral types from teff - DONE
# COULD ALSO DO THIS WITH LUMINOSITIES
    spt_kwargs = kwargs.get('spt_parameters',{})
    sp0 = numpy.linspace(10,40,300)
    tf0 = numpy.array([splat.typeToTeff(spi,**spt_kwargs)[0] for spi in sp0])
    sp = sp0[~numpy.isnan(tf0)]
    tf = tf0[~numpy.isnan(tf0)]
    f_teff_spt = interp1d(tf,sp,bounds_error=False,fill_value=numpy.nan)
    spt = [f_teff_sp(t.value) for t in mp['temperature']]
    spt = numpy.array(spt)
    parameters['spt'] = numpy.array(spt)

# add binary companions if desired
    if kwargs.get('binaries',False) == True:
        binary_kwargs = kwargs.get('binary_parameters',{})
        parameters['q'] = simulateMassRatios(num,**binary_kwargs)
        parameters['mass2'] = numpy.array(parameters['q'])*numpy.array(parameters['mass'])
        mp = modelParameters(mass=parameters['mass2'],age=parameters['age'],**model_kwargs)
        parameters['gravity2'] = mp['gravity']
        parameters['luminosity2'] = mp['luminosity']
        parameters['radius2'] = mp['radius']
        parameters['temperature2'] = mp['temperature']
        spt2 = [f_teff_spt(t.value) for t in mp['temperature2']]
        spt2 = numpy.array(spt2)
        parameters['spt2'] = numpy.array(spt2)


# assign binary orbital properties if desired

# assign sky positions if desired

# assign distances based on density profile if desired

# assign absolute, systemic and apparent magnitudes if desired

# assign age-dependent kinematics if desired

# assign proper and radial motions if desired

# assign apparent binary properties - current projected separation, astrometric offset, primary & secondary RV offsets - if desired

# assign metallicities (?) if desired

# visualize output?

    return parameters


def UVWpopulation(uvw,e_uvw=[0.,0.,0.],nsamp=1000,verbose=False):
    '''
    :Purpose: Computes the probabilities of a source being within the thin disk, thick disk or halo populations
    using the analysis of Bensby et al. 2003

    Required Inputs:

    :param: uvw: array containing the UVW velocities in km/s in right-hand coordinate system

    Optional Inputs:

    :param: e_uvw: uarray containing the uncertainties of UVW in km/s (default = [0.,0.,0.])
    :param: nsamp: number of Monte Carlo samples for error propogation (default = 1000)
    :param: verbose: Give feedback (default = False)

    Output: 

    Three value specifying the probability of being in the thin disk, thick disk, or halo (sums to 1)

    :Example:
    >>> import splat.evolve as spev
    >>> pt,pth,ph = spev.UVWpopulation([20.,-80.,10.],verbose=True)
        P(thin) = 0.418
        P(thick) = 0.581
        P(halo) = 0.000
        Borderline thin/thick disk star
    '''

# parameters 
    thin_sig = numpy.array([35.,20.,16.])
    thin_asym = -15.
    thin_f = 0.94

    thick_sig = numpy.array([67.,38.,35.])
    thick_asym = -46.
    thick_f = 0.06

    halo_sig = numpy.array([160.,90.,90.])
    halo_asym = -220.
    halo_f = 0.0015

    k_thin = 1./(((2.*numpy.pi)**1.5)*numpy.product(numpy.array(thin_sig)))
    k_thick = 1./(((2.*numpy.pi)**1.5)*numpy.product(numpy.array(thick_sig)))
    k_halo = 1./(((2.*numpy.pi)**1.5)*numpy.product(numpy.array(halo_sig)))

    if e_uvw[0] != 0.:
        us = numpy.random.normal(uvw[0],e_uvw[0],nsamp)
        vs = numpy.random.normal(uvw[1],e_uvw[1],nsamp)
        ws = numpy.random.normal(uvw[2],e_uvw[2],nsamp)
    else:
        us = numpy.array(uvw[0])
        vs = numpy.array(uvw[1])
        ws = numpy.array(uvw[2])
        
    us_thin_exp = (us**2)/(2.*thin_sig[0]**2)
    us_thick_exp = (us**2)/(2.*thick_sig[0]**2)
    us_halo_exp = (us**2)/(2.*halo_sig[0]**2)
    vs_thin_exp = ((vs-thin_asym)**2)/(2.*thin_sig[1]**2)
    vs_thick_exp = ((vs-thick_asym)**2)/(2.*thick_sig[1]**2)
    vs_halo_exp = ((vs-halo_asym)**2)/(2.*halo_sig[1]**2)
    ws_thin_exp = (ws**2)/(2.*thin_sig[2]**2)
    ws_thick_exp = (ws**2)/(2.*thick_sig[2]**2)
    ws_halo_exp = (ws**2)/(2.*halo_sig[2]**2)

    td_d = (thick_f/thin_f)*(k_thick/k_thin)*numpy.exp(us_thin_exp+vs_thin_exp+ws_thin_exp-us_thick_exp-vs_thick_exp-ws_thick_exp)
    h_td = (halo_f/thick_f)*(k_halo/k_thick)*numpy.exp(-1.*(us_halo_exp+vs_halo_exp+ws_halo_exp-us_thick_exp-vs_thick_exp-ws_thick_exp))

    pd = 1./(1.+td_d*(1.+h_td))
    ptd = pd*td_d
    ph = ptd*h_td

    if e_uvw[0] != 0.:
        if verbose==True:
            print('P(thin) = {:.3f}+/-{:.3f}'.format(numpy.mean(pd),numpy.std(pd)))
            print('P(thick) = {:.3f}+/-{:.3f}'.format(numpy.mean(ptd),numpy.std(ptd)))
            print('P(halo) = {:.3f}+/-{:.3f}'.format(numpy.mean(ph),numpy.std(ph)))
            if numpy.mean(td_d) > 10.: print('Likely thick disk star')
            elif numpy.mean(td_d) < 0.1: print('Likely thin disk star')
            else: print('Borderline thin/thick disk star')
        return numpy.mean(pd),numpy.mean(ptd),numpy.mean(ph)
    else:
        if verbose==True:
            print('P(thin) = {:.3f}'.format(pd))
            print('P(thick) = {:.3f}'.format(ptd))
            print('P(halo) = {:.3f}'.format(ph))
            if td_d > 10.: print('Likely thick disk star')
            elif td_d < 0.1: print('Likely thin disk star')
            else: print('Borderline thin/thick disk star')
        return pd,ptd,ph


def galacticPotential(r,z,verbose=False,report='all'):
    '''
    :Purpose: Computes the specific gravitational potential (energy per mass) at a particular radius r and 
    scaleheight z in the Milky Way Galaxy based on the cylindrically symmetric models of Barros et al. (2016, AandA, 593A, 108)

    Required Inputs:

    :param: r: radial coordinate from center of Galaxy in units of kpc
    :param: r: vertical coordinate in plane of Galaxy in units of kpc

    Optional Inputs:

    :param: report: set to the following to return specific values:
        * `all`: return total potential (default) 
        * `disk`: return only potential from the disk
        * `halo`: return only potential from the halo
        * `bulge`: return only potential from the bulge
    :param: verbose: Give feedback (default = False)

    Output: 

    Specific potential in units of km2/s2

    :Example:
    >>> import splat.evolve as spev
    >>> pot = spev.galacticPotential(8.5,2.0,verbose=True)
        Thin disk potential = -16164.669941534123 km2 / s2
        Thick disk potential = -2805.8541251994084 km2 / s2
        H I disk potential = -4961.194452965543 km2 / s2
        H II disk potential = -1320.2381374715114 km2 / s2
        Total disk potential = -25251.956657170587 km2 / s2
        Bulge potential = -12195.097166319883 km2 / s2
        Halo potential = 64175.96074890407 km2 / s2    
    '''

# convert inputs into proper units
    rval = r*u.kpc
    zval = z*u.kpc
    fmass = 1.0
# bulge
    mb = 2.6e10*u.solMass
    ab = 0.44*u.kpc
    phib = -1.*constants.G*mb/((rval**2+zval**2)**0.5+ab)
    phib = phib.to((u.km**2)/(u.s**2))
# halo
    vh = 166*u.km/u.s
    rh = 5.4*u.kpc
    qphi = 1.
    phih = 0.5*(vh**2)*numpy.log((rval/u.kpc)**2+(zval/qphi/u.kpc)**2+(rh/u.kpc)**2)
    phih = phih.to((u.km**2)/(u.s**2))
# thin disk
    b = 0.243*u.kpc
    xi = (zval**2+b**2)**0.5
    md = 2.106e10*u.solMass
    ad = 3.859*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    x2 = rval**2-2.*(ad+xi)**2
    phid1 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2)-(1./3.)*(ad**2)*x2/(x**4))
    md = 2.162e10*u.solMass
    ad = 9.052*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    x2 = rval**2-2.*(ad+xi)**2
    phid2 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2)-(1./3.)*(ad**2)*x2/(x**4))
    md = -1.074e10*u.solMass
    ad = 3.107*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    x2 = rval**2-2.*(ad+xi)**2
    phid3 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2)-(1./3.)*(ad**2)*x2/(x**4))
    phid = phid1.to(u.km**2/u.s**2)+phid2.to(u.km**2/u.s**2)+phid3.to(u.km**2/u.s**2)
# thick disk
    b = 0.776*u.kpc
    xi = (zval**2+b**2)**0.5
    md = 0.056e10*u.solMass
    ad = 0.993*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    phitd1 = -1.*constants.G*(fmass*md/x)
    md = 3.766e10*u.solMass
    ad = 6.555*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    phitd2 = -1.*constants.G*(fmass*md/x)
    md = -3.250e10*u.solMass
    ad = 7.651*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    phitd3 = -1.*constants.G*(fmass*md/x)
    phitd = phitd1.to(u.km**2/u.s**2)+phitd2.to(u.km**2/u.s**2)+phitd3.to(u.km**2/u.s**2)
# h1 disk
    b = 0.168*u.kpc
    xi = (zval**2+b**2)**0.5
    md = 2.046e10*u.solMass
    ad = 9.021*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    phih11 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2))
    md = 2.169e10*u.solMass
    ad = 9.143*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    phih12 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2))
    md = -3.049e10*u.solMass
    ad = 7.758*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    phih13 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2))
    phih1 = phih11.to(u.km**2/u.s**2)+phih12.to(u.km**2/u.s**2)+phih13.to(u.km**2/u.s**2)
# h2 disk
    b = 0.128*u.kpc
    xi = (zval**2+b**2)**0.5
    md = 0.928e10*u.solMass
    ad = 6.062*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    x2 = rval**2-2.*(ad+xi)**2
    phih21 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2)-(1./3.)*(ad**2)*x2/(x**4))
    md = 0.163e10*u.solMass
    ad = 3.141*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    x2 = rval**2-2.*(ad+xi)**2
    phih22 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2)-(1./3.)*(ad**2)*x2/(x**4))
    md = -0.837e10*u.solMass
    ad = 4.485*u.kpc
    x = (rval**2+(ad+xi)**2)**0.5
    x2 = rval**2-2.*(ad+xi)**2
    phih23 = -1.*constants.G*(fmass*md/x)*(1.+(ad*(ad+xi)/x**2)-(1./3.)*(ad**2)*x2/(x**4))
    phih2 = phih21.to(u.km**2/u.s**2)+phih22.to(u.km**2/u.s**2)+phih23.to(u.km**2/u.s**2)

    phidisk = phid+phitd+phih1+phih2    

    if verbose==True: 
        print('Thin disk potential = {}'.format(phid))
        print('Thick disk potential = {}'.format(phitd))
        print('H I disk potential = {}'.format(phih1))
        print('H II disk potential = {}'.format(phih2))
        print('Total disk potential = {}'.format(phidisk))
        print('Bulge potential = {}'.format(phib))
        print('Halo potential = {}'.format(phih))

    if report=='halo': return phih
    elif report=='bulge': return phib
    elif report=='disk': return phidisk
    else: return phib+phih+phidisk

