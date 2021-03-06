#!/usr/bin/env python3
'''
This script is meant to determine where each map points for each event and then save these values to file. 
'''
import os
import sys
import h5py
sys.path.append(os.environ['BEACON_INSTALL_DIR'])
from examples.beacon_data_reader import Reader #Must be imported before matplotlib or else plots don't load.

sys.path.append(os.environ['BEACON_ANALYSIS_DIR'])
import tools.interpret as interpret #Must be imported before matplotlib or else plots don't load.
import tools.info as info
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
plt.ion()
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from tools.correlator import Correlator


font = {'weight' : 'bold',
        'size'   : 16}

matplotlib.rc('font', **font)
matplotlib.rcParams['figure.figsize'] = [10, 11]
matplotlib.rcParams.update({'font.size': 16})

def getEventIds(reader, trigger_type=None):
    '''
    Will get a list of eventids for the given reader, but only those matching the trigger
    types supplied.  If trigger_type  == None then all eventids will be returned. 
    trigger_type:
    1 Software
    2 RF
    3 GPS
    '''
    try:
        if trigger_type == None:
            trigger_type = numpy.array([1,2,3])
        elif type(trigger_type) == int:
            trigger_type = numpy.array([trigger_type])

        eventids = numpy.array([])
        for trig_index, trig in enumerate(trigger_type):
            N = reader.head_tree.Draw("Entry$","trigger_type==%i"%trig,"goff") 
            eventids = numpy.append(eventids,numpy.frombuffer(reader.head_tree.GetV1(), numpy.dtype('float64'), N).astype(int))
        eventids.sort()
        return eventids
    except Exception as e:
        print('\nError in %s'%inspect.stack()[0][3])
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return e


if __name__=="__main__":
    if len(sys.argv) == 2:
        run = int(sys.argv[1])
    else:
        run = 1701

    datapath = os.environ['BEACON_DATA']
    plot_filter=False

    crit_freq_low_pass_MHz = 70 #This new pulser seems to peak in the region of 85 MHz or so
    low_pass_filter_order = 4

    crit_freq_high_pass_MHz = None
    high_pass_filter_order = None

    apply_phase_response = True
    hilbert=True
    upsample = 2**15 #Just upsample in this case
    max_method = 0

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

    if upsample is None:
        filter_string += 'upsample_%s-'%('None')
    else:
        filter_string += 'upsample_%i-'%(upsample)

    if max_method is None:
        filter_string += 'maxmethod_%s'%('None')
    else:
        filter_string += 'maxmethod_%i'%(max_method)


    print(filter_string)

    

    try:
        run = int(run)

        reader = Reader(datapath,run)
        try:
            print(reader.status())
        except Exception as e:
            print('Status Tree not present.  Returning Error.')
            print('\nError in %s'%inspect.stack()[0][3])
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            sys.exit(1)
        filename = createFile(reader) #Creates an analysis file if one does not exist.  Returns filename to load file.
        eventids = getEventIds(reader,trigger_type=[1,2,3]) #eventids with rf trigger
        if numpy.size(eventids) != 0:
            print('run = ',run)

        if filename is not None:
            with h5py.File(filename, 'a') as file:
                try:
                    dsets = list(file.keys()) #Existing datasets

                    if not numpy.isin('map_direction',dsets):
                        file.create_group('map_direction')
                    else:
                        print('map_direction group already exists in file %s'%filename)

                    map_direction_dsets = list(file['map_direction'].keys())

                    if not numpy.isin(filter_string,map_direction_dsets):
                        file['map_direction'].create_group(filter_string)
                    else:
                        print('%s group already exists in file %s'%(filter_string,filename))

                    map_direction_subsets = list(file['map_direction'][filter_string].keys())



                    if not numpy.isin('map_times',dsets):
                        file.create_group('map_times')
                    else:
                        print('map_times group already exists in file %s'%filename)

                    map_times_dsets = list(file['map_times'].keys())

                    if not numpy.isin(filter_string,map_times_dsets):
                        file['map_times'].create_group(filter_string)
                    else:
                        print('%s group already exists in file %s'%(filter_string,filename))

                    map_times_subsets = list(file['map_times'][filter_string].keys())


                    #Directions
                    if not numpy.isin('hpol_ENU_azimuth',map_direction_subsets):
                        file['map_direction'][filter_string].create_dataset('hpol_ENU_azimuth', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in hpol_ENU_azimuth of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('hpol_ENU_zenith',map_direction_subsets):
                        file['map_direction'][filter_string].create_dataset('hpol_ENU_zenith', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in hpol_ENU_zenith of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('vpol_ENU_azimuth',map_direction_subsets):
                        file['map_direction'][filter_string].create_dataset('vpol_ENU_azimuth', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in vpol_ENU_azimuth of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('vpol_ENU_zenith',map_direction_subsets):
                        file['map_direction'][filter_string].create_dataset('vpol_ENU_zenith', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in vpol_ENU_zenith of %s will be overwritten by this analysis script.'%filename)

                    #Time Delays for directions
                    #01
                    if not numpy.isin('hpol_0subtract1',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('hpol_0subtract1', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in hpol_0subtract1 of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('vpol_0subtract1',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('vpol_0subtract1', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in vpol_0subtract1 of %s will be overwritten by this analysis script.'%filename)

                    #02
                    if not numpy.isin('hpol_0subtract2',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('hpol_0subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in hpol_0subtract2 of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('vpol_0subtract2',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('vpol_0subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in vpol_0subtract2 of %s will be overwritten by this analysis script.'%filename)

                    #03
                    if not numpy.isin('hpol_0subtract3',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('hpol_0subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in hpol_0subtract3 of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('vpol_0subtract3',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('vpol_0subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in vpol_0subtract3 of %s will be overwritten by this analysis script.'%filename)

                    #12
                    if not numpy.isin('hpol_1subtract2',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('hpol_1subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in hpol_1subtract2 of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('vpol_1subtract2',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('vpol_1subtract2', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in vpol_1subtract2 of %s will be overwritten by this analysis script.'%filename)

                    #13
                    if not numpy.isin('hpol_1subtract3',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('hpol_1subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in hpol_1subtract3 of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('vpol_1subtract3',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('vpol_1subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in vpol_1subtract3 of %s will be overwritten by this analysis script.'%filename)

                    #23
                    if not numpy.isin('hpol_2subtract3',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('hpol_2subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in hpol_2subtract3 of %s will be overwritten by this analysis script.'%filename)

                    if not numpy.isin('vpol_2subtract3',map_times_subsets):
                        file['map_times'][filter_string].create_dataset('vpol_2subtract3', (file.attrs['N'],), dtype='f', compression='gzip', compression_opts=4, shuffle=True)
                    else:
                        print('Values in vpol_2subtract3 of %s will be overwritten by this analysis script.'%filename)


                    cor = Correlator(reader,  upsample=upsample, n_phi=360, n_theta=360, waveform_index_range=(None,None),crit_freq_low_pass_MHz=crit_freq_low_pass_MHz, crit_freq_high_pass_MHz=crit_freq_high_pass_MHz, low_pass_filter_order=low_pass_filter_order, high_pass_filter_order=high_pass_filter_order, plot_filter=plot_filter)

                    for mode in ['hpol','vpol']:
                        print('Performing calculations for %s'%mode)
                        for event_index, eventid in enumerate(eventids):
                            if (event_index + 1) % 1000 == 0:
                                sys.stdout.write('(%i/%i)\t\t\t\n'%(event_index+1,len(eventids)))
                                sys.stdout.flush()
                            m = cor.map(eventid, mode, plot_map=False, plot_corr=False, hilbert=hilbert,verbose=False)
                            if max_method is not None:
                                row_index, column_index, theta_best, phi_best, t_0subtract1, t_0subtract2, t_0subtract3, t_1subtract2, t_1subtract3, t_2subtract3 = cor.mapMax(m,max_method=max_method,verbose=False)
                            else:
                                row_index, column_index, theta_best, phi_best, t_0subtract1, t_0subtract2, t_0subtract3, t_1subtract2, t_1subtract3, t_2subtract3 = cor.mapMax(m,verbose=False)        

                            file['map_direction'][filter_string]['%s_ENU_zenith'%mode][eventid] = theta_best 
                            file['map_direction'][filter_string]['%s_ENU_azimuth'%mode][eventid] = phi_best 
                            file['map_times'][filter_string]['%s_0subtract1'%mode][eventid] = t_0subtract1 
                            file['map_times'][filter_string]['%s_0subtract2'%mode][eventid] = t_0subtract2 
                            file['map_times'][filter_string]['%s_0subtract3'%mode][eventid] = t_0subtract3 
                            file['map_times'][filter_string]['%s_1subtract2'%mode][eventid] = t_1subtract2 
                            file['map_times'][filter_string]['%s_1subtract3'%mode][eventid] = t_1subtract3 
                            file['map_times'][filter_string]['%s_2subtract3'%mode][eventid] = t_2subtract3 

                    file.close()
                except Exception as e:
                    file.close()
                    print('\nError in %s'%inspect.stack()[0][3])
                    print(e)
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)
                    sys.exit(1)
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

