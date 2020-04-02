#!/usr/bin/env python3
'''
This is meant to calculate the time delays for each event and then save them to file.
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
    default_align_method = 0
    if len(sys.argv) > 1:
        run = int(sys.argv[1])
        if len(sys.argv) > 2:
            align_method = int(sys.argv[2])
        else:
            align_method = default_align_method#4#0#4#8
        print('Using align_method = %i'%align_method)
    else:
        run = 1702
        align_method = default_align_method#4#0#4#8

    datapath = os.environ['BEACON_DATA']

    crit_freq_low_pass_MHz = None #This new pulser seems to peak in the region of 85 MHz or so
    low_pass_filter_order = None

    crit_freq_high_pass_MHz = None
    high_pass_filter_order = None

    apply_phase_response = False

    shorten_signals = True
    shorten_thresh = 0.7
    shorten_delay = 10.0
    shorten_length = 90.0

    hilbert=False
    final_corr_length = 2**18

    filter_string = ''

    if crit_freq_low_pass_MHz is None:
        filter_string += 'LPf_%s-'%('None')
    else:
        filter_string += 'LPf_%0.1f-'%(crit_freq_low_pass_MHz)

    if low_pass_filter_order is None:
        filter_string += 'LPo_%s-'%('None')
    else:
        filter_string += 'LPo_%i-'%(low_pass_filter_order)

    if crit_freq_high_pass_MHz is None:
        filter_string += 'HPf_%s-'%('None')
    else:
        filter_string += 'HPf_%0.1f-'%(crit_freq_high_pass_MHz)

    if high_pass_filter_order is None:
        filter_string += 'HPo_%s-'%('None')
    else:
        filter_string += 'HPo_%i-'%(high_pass_filter_order)

    if apply_phase_response is None:
        filter_string += 'Phase_%s-'%('None')
    else:
        filter_string += 'Phase_%i-'%(apply_phase_response)

    if hilbert is None:
        filter_string += 'Hilb_%s-'%('None')
    else:
        filter_string += 'Hilb_%i-'%(hilbert)

    if final_corr_length is None:
        filter_string += 'corlen_%s-'%('None')
    else:
        filter_string += 'corlen_%i-'%(final_corr_length)

    if align_method is None:
        filter_string += 'align_%s'%('None')
    else:
        filter_string += 'align_%i'%(align_method)


    if shorten_signals is None:
        filter_string += 'shorten_signals-%s'%('None')
    else:
        filter_string += 'shorten_signals-%i'%(shorten_signals)
    if shorten_thresh is None:
        filter_string += 'shorten_thresh-%s'%('None')
    else:
        filter_string += 'shorten_thresh-%0.2f'%(shorten_thresh)
    if shorten_delay is None:
        filter_string += 'shorten_delay-%s'%('None')
    else:
        filter_string += 'shorten_delay-%0.2f'%(shorten_delay)
    if shorten_length is None:
        filter_string += 'shorten_length-%s'%('None')
    else:
        filter_string += 'shorten_length-%0.2f'%(shorten_length)


    print(filter_string)



    plot_filter = False
    plot_multiple = False


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
                rf_cut = file['trigger_type'][...] == 2

                dsets = list(file.keys()) #Existing datasets

                if not numpy.isin('time_delays',dsets):
                    file.create_group('time_delays')
                else:
                    print('time_delays group already exists in file %s'%filename)

                time_delay_groups = list(file['time_delays'].keys()) #Existing datasets

                if not numpy.isin(filter_string,time_delay_groups):
                    file['time_delays'].create_group(filter_string)
                else:
                    print('%s group already exists in file %s'%(filter_string,filename))

                time_delay_dsets = list(file['time_delays'][filter_string].keys()) #Existing datasets

                #eventids with rf trigger
                if numpy.size(eventids) != 0:
                    print('run = ',run)

                #Time Delays
                #01
                if not numpy.isin('hpol_t_0subtract1',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_t_0subtract1', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_t_0subtract1 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_t_0subtract1',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_t_0subtract1', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_t_0subtract1 of %s will be overwritten by this analysis script.'%filename)



                #02
                if not numpy.isin('hpol_t_0subtract2',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_t_0subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_t_0subtract2 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_t_0subtract2',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_t_0subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_t_0subtract2 of %s will be overwritten by this analysis script.'%filename)



                #03
                if not numpy.isin('hpol_t_0subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_t_0subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_t_0subtract3 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_t_0subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_t_0subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_t_0subtract3 of %s will be overwritten by this analysis script.'%filename)



                #12
                if not numpy.isin('hpol_t_1subtract2',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_t_1subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_t_1subtract2 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_t_1subtract2',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_t_1subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_t_1subtract2 of %s will be overwritten by this analysis script.'%filename)



                #13
                if not numpy.isin('hpol_t_1subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_t_1subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_t_1subtract3 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_t_1subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_t_1subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_t_1subtract3 of %s will be overwritten by this analysis script.'%filename)



                #23
                if not numpy.isin('hpol_t_2subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_t_2subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_t_2subtract3 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_t_2subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_t_2subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_t_2subtract3 of %s will be overwritten by this analysis script.'%filename)



                #Correlation values.
                #01
                if not numpy.isin('hpol_max_corr_0subtract1',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_max_corr_0subtract1', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_max_corr_0subtract1 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_max_corr_0subtract1',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_max_corr_0subtract1', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_max_corr_0subtract1 of %s will be overwritten by this analysis script.'%filename)
                


                #02
                if not numpy.isin('hpol_max_corr_0subtract2',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_max_corr_0subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_max_corr_0subtract2 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_max_corr_0subtract2',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_max_corr_0subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_max_corr_0subtract2 of %s will be overwritten by this analysis script.'%filename)



                #03
                if not numpy.isin('hpol_max_corr_0subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_max_corr_0subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_max_corr_0subtract3 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_max_corr_0subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_max_corr_0subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_max_corr_0subtract3 of %s will be overwritten by this analysis script.'%filename)



                #12
                if not numpy.isin('hpol_max_corr_1subtract2',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_max_corr_1subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_max_corr_1subtract2 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_max_corr_1subtract2',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_max_corr_1subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_max_corr_1subtract2 of %s will be overwritten by this analysis script.'%filename)



                #13
                if not numpy.isin('hpol_max_corr_1subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_max_corr_1subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_max_corr_1subtract3 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_max_corr_1subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_max_corr_1subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_max_corr_1subtract3 of %s will be overwritten by this analysis script.'%filename)



                #23
                if not numpy.isin('hpol_max_corr_2subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('hpol_max_corr_2subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in hpol_max_corr_2subtract3 of %s will be overwritten by this analysis script.'%filename)

                if not numpy.isin('vpol_max_corr_2subtract3',time_delay_dsets):
                    file['time_delays'][filter_string].create_dataset('vpol_max_corr_2subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                else:
                    print('Values in vpol_max_corr_2subtract3 of %s will be overwritten by this analysis script.'%filename)


                if sum(rf_cut) > 0:
                    tdc = TimeDelayCalculator(reader, final_corr_length=final_corr_length, crit_freq_low_pass_MHz=crit_freq_low_pass_MHz, crit_freq_high_pass_MHz=crit_freq_high_pass_MHz, low_pass_filter_order=low_pass_filter_order, high_pass_filter_order=high_pass_filter_order,waveform_index_range=(None,None),plot_filters=plot_filter,apply_phase_response=apply_phase_response)
                    time_shifts, corrs, pairs = tdc.calculateMultipleTimeDelays(eventids[rf_cut],align_method=align_method,hilbert=hilbert,plot=plot_multiple,hpol_cut=None,vpol_cut=None)

                    for pair_index, pair in enumerate(pairs):
                        if numpy.all(pair == numpy.array([0,2])):
                            file['time_delays'][filter_string]['hpol_t_0subtract1'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['hpol_max_corr_0subtract1'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([0,4])):
                            file['time_delays'][filter_string]['hpol_t_0subtract2'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['hpol_max_corr_0subtract2'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([0,6])):
                            file['time_delays'][filter_string]['hpol_t_0subtract3'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['hpol_max_corr_0subtract3'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([2,4])):
                            file['time_delays'][filter_string]['hpol_t_1subtract2'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['hpol_max_corr_1subtract2'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([2,6])):
                            file['time_delays'][filter_string]['hpol_t_1subtract3'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['hpol_max_corr_1subtract3'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([4,6])):
                            file['time_delays'][filter_string]['hpol_t_2subtract3'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['hpol_max_corr_2subtract3'][rf_cut] = corrs[pair_index]

                        elif numpy.all(pair == numpy.array([1,3])):
                            file['time_delays'][filter_string]['vpol_t_0subtract1'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['vpol_max_corr_0subtract1'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([1,5])):
                            file['time_delays'][filter_string]['vpol_t_0subtract2'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['vpol_max_corr_0subtract2'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([1,7])):
                            file['time_delays'][filter_string]['vpol_t_0subtract3'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['vpol_max_corr_0subtract3'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([3,5])):
                            file['time_delays'][filter_string]['vpol_t_1subtract2'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['vpol_max_corr_1subtract2'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([3,7])):
                            file['time_delays'][filter_string]['vpol_t_1subtract3'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['vpol_max_corr_1subtract3'][rf_cut] = corrs[pair_index]
                        elif numpy.all(pair == numpy.array([5,7])):
                            file['time_delays'][filter_string]['vpol_t_2subtract3'][rf_cut] = time_shifts[pair_index]
                            file['time_delays'][filter_string]['vpol_max_corr_2subtract3'][rf_cut] = corrs[pair_index]
                else:
                    print('No RF signals, skipping calculation.')
                file.close()
        else:
            print('filename is None, indicating empty tree.  Skipping run %i'%run)
    except Exception as e:
        print('\nError in %s'%inspect.stack()[0][3])
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        sys.exit(1)

    sys.exit(0)