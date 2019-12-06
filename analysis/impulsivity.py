#!/usr/bin/env python3
'''
This is meant to calculate the impulsivity for each event and then save them to file.
'''
import os
import sys
import h5py
sys.path.append(os.environ['BEACON_INSTALL_DIR'])
from examples.beacon_data_reader import Reader #Must be imported before matplotlib or else plots don't load.

sys.path.append(os.environ['BEACON_ANALYSIS_DIR'])
import tools.interpret as interpret #Must be imported before matplotlib or else plots don't load.
import tools.info as info
from objects.fftmath import TimeDelayCalculator
from tools.data_handler import createFile

import matplotlib.pyplot as plt
import scipy.signal
import scipy.stats
import numpy
import sys
import math
import matplotlib
from scipy.fftpack import fft
import datetime as dt
import inspect
from ast import literal_eval
import astropy.units as apu
from astropy.coordinates import SkyCoord
import itertools
plt.ion()
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)



font = {'weight' : 'bold',
        'size'   : 16}

matplotlib.rc('font', **font)
matplotlib.rcParams['figure.figsize'] = [10, 11]
matplotlib.rcParams.update({'font.size': 16})

if __name__=="__main__":
    if len(sys.argv) == 2:
        run = int(sys.argv[1])
    else:
        run = 1701

    datapath = os.environ['BEACON_DATA']
    crit_freq_low_pass_MHz = None#60 #This new pulser seems to peak in the region of 85 MHz or so
    low_pass_filter_order = None#4

    crit_freq_high_pass_MHz = None
    high_pass_filter_order = None
    apply_phase_response = True
    plot_filter=False
    hilbert=False
    plot_multiple = False
    final_corr_length = 2**15
    align_method = 0
    max_method = 0
    impulsivity_window = 750

    hpol_pairs  = numpy.array(list(itertools.combinations((0,2,4,6), 2)))
    vpol_pairs  = numpy.array(list(itertools.combinations((1,3,5,7), 2)))
    pairs       = numpy.vstack((hpol_pairs,vpol_pairs)) 

    try:
        run = int(run)

        reader = Reader(datapath,run)
        filename = createFile(reader) #Creates an analysis file if one does not exist.  Returns filename to load file.
        if filename is not None:
            with h5py.File(filename, 'a') as file:
                eventids = file['eventids'][...]
                all_time_delays = numpy.vstack((file['%s_t_%isubtract%i'%('hpol',0,1)][...],file['%s_t_%isubtract%i'%('hpol',0,2)][...],file['%s_t_%isubtract%i'%('hpol',0,3)][...],file['%s_t_%isubtract%i'%('hpol',1,2)][...],file['%s_t_%isubtract%i'%('hpol',1,3)][...],file['%s_t_%isubtract%i'%('hpol',2,3)][...],file['%s_t_%isubtract%i'%('vpol',0,1)][...],file['%s_t_%isubtract%i'%('vpol',0,2)][...],file['%s_t_%isubtract%i'%('vpol',0,3)][...],file['%s_t_%isubtract%i'%('vpol',1,2)][...],file['%s_t_%isubtract%i'%('vpol',1,3)][...],file['%s_t_%isubtract%i'%('vpol',2,3)][...])).T

                #eventids with rf trigger
                if numpy.size(eventids) != 0:
                    print('run = ',run)
                dsets = list(file.keys()) #Existing datasets

                
                file.attrs['impulsivity_window_ns'] = impulsivity_window

                if not numpy.isin('impulsivity_hpol',dsets):
                    file.create_dataset('impulsivity_hpol', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in impulsivity_hpol of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('impulsivity_vpol',dsets):
                    file.create_dataset('impulsivity_vpol', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in impulsivity_vpol of %s will be overwritten by this analysis script.'%filename)

                #Add two functions to TimeDelayCalculator: calculateImpulsivityFromDelay and calculateImpulsivityFromEventid, these can then be use below to get the impulsivity.

                tdc = TimeDelayCalculator(reader, final_corr_length=final_corr_length, crit_freq_low_pass_MHz=crit_freq_low_pass_MHz, crit_freq_high_pass_MHz=crit_freq_high_pass_MHz, low_pass_filter_order=low_pass_filter_order, high_pass_filter_order=high_pass_filter_order,waveform_index_range=(None,None),plot_filters=plot_filter,apply_phase_response=apply_phase_response)

                for eventid in eventids: 
                    if eventid%500 == 0:
                        sys.stdout.write('(%i/%i)\r'%(eventid,len(eventids)))
                        sys.stdout.flush()
                    delays = -all_time_delays[eventid] #Unsure why I need to invert this.
                    file['impulsivity_hpol'][eventid], file['impulsivity_vpol'][eventid] = tdc.calculateImpulsivityFromTimeDelays(eventid, delays, upsampled_waveforms=None,return_full_corrs=False, align_method=0, hilbert=False,plot=False,impulsivity_window=750)

                file.close()
        else:
            print('filename is None, indicating empty tree.  Skipping run %i'%run)
    except Exception as e:
        print('\nError in %s'%inspect.stack()[0][3])
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

