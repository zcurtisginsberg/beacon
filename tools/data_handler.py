'''
This script is meant to contain the overhead code for organizing and working with
analysis files for BEACON analysis.  Given a reader and some kwargs it will
load the correct analysis file (or create one if necessary).

I anticipate having wrapper functions for certain things such as adding a datasets
or overwriting existing datasets.
'''

import sys
import os
import inspect
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from pprint import pprint
sys.path.append(os.environ['BEACON_INSTALL_DIR'])
from examples.beacon_data_reader import Reader #Must be imported before matplotlib or else plots don't load.
import numpy
import h5py

sys.path.append(os.environ['BEACON_ANALYSIS_DIR'])
import tools.interpret as interpret #Must be imported before matplotlib or else plots don't load.
import tools.info as info


analysis_data_dir = '/home/dsouthall/scratch-midway2/beacon/'
#os.environ['BEACON_ANALYSIS_DIR'] + 'data/'


def loadTriggerTypes(reader):
    '''
    Will get a list of trigger types corresponding to all eventids for the given reader
    trigger_type:
    1 Software
    2 RF
    3 GPS
    '''
    #trigger_types = numpy.zeros(reader.N())
    try:
        N = reader.head_tree.Draw("trigger_type","","goff") 
        trigger_types = numpy.frombuffer(reader.head_tree.GetV1(), numpy.dtype('float64'), N).astype(int)
    except Exception as e:
        print('\nError in %s'%inspect.stack()[0][3])
        print('Error while trying to copy header elements to attrs.')
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
    return trigger_types

def createFile(reader):
    '''
    This will make an hdf5 file for the run specified by the reader.
    If the file already exists then this will check if the file has
    all of the baseline datasets that are currently expected, and if
    not it will do this prepwork.  It will not overwrite.

    This will returnt the filename of the file.

    Parameters
    ----------
    reader : examples.beacon_data_reader.Reader
        This is the reader for the selected run.
    '''
    try:
        run = int(reader.run)
        N = reader.N()
        filename = analysis_data_dir + 'run%i_analysis_data.h5'%run

        header_keys_to_copy = []
        h = interpret.getHeaderDict(reader)

        initial_expected_datasets = numpy.array(['trigger_types']) #expand as more things are added.  This should only include datasets that this function will add.
        initial_expected_attrs    = numpy.array(['N','run'])
        if os.path.exists(filename):
            print('%s already exists, checking if setup is up to date.'%filename )

            with h5py.File(filename, 'a') as file:
                try:
                    for key in initial_expected_datasets[~numpy.isin(initial_expected_datasets,list(file.keys()))]:
                        print('Attempting to add content for key: %s'%key)
                        if key == 'trigger_types':
                            file.create_dataset('trigger_types', (N,), dtype=numpy.uint8, compression='gzip', compression_opts=9, shuffle=True)
                            file['trigger_types'][...] = loadTriggerTypes(reader)
                        else:
                            print('key: %s currently has no hardcoded support in this loop.'%key)

                    for key in initial_expected_attrs[~numpy.isin(initial_expected_attrs,list(file.attrs.keys()))]:
                        print('Attempting to add content for key: %s'%key)
                        if key == 'N':
                            file.attrs['N'] = N
                        elif key == 'run':
                            file.attrs['run'] = run
                        else:
                            print('key: %s currently has no hardcoded support in this loop.'%key)
                    file.close()
                except Exception as e:
                    file.close()
                    print('\nError in %s'%inspect.stack()[0][3])
                    print('Error while trying to copy header elements to attrs.')
                    print(e)
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)

        else:
            print('Creating %s.'%filename )
            with h5py.File(filename, 'w') as file:
                #Prepare attributes for the file.
                file.attrs['N'] = N
                file.attrs['run'] = run
                for key in header_keys_to_copy:
                    try:
                        file.attrs[key] = h[key]
                    except Exception as e:
                        file.close()
                        print('\nError in %s'%inspect.stack()[0][3])
                        print('Error while trying to copy header elements to attrs.')
                        print(e)
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        print(exc_type, fname, exc_tb.tb_lineno)

                #Create datasets that don't require analysis, but might be useful in analysis.
                #When adding things to here, ensure they are also added and handled above as well
                #for when the file already exists. 

                file.create_dataset('trigger_types', (N,), dtype=numpy.uint8, compression='gzip', compression_opts=9, shuffle=True)
                file['trigger_types'][...] = loadTriggerTypes(reader)
        return filename

    except Exception as e:
        print('\nError in %s'%inspect.stack()[0][3])
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

if __name__=="__main__":
    datapath = os.environ['BEACON_DATA']
    runs = numpy.array([1645])#numpy.arange(1645,1700)

    for run in runs:
        run = int(run)

        reader = Reader(datapath,run)
        trigger_types = loadTriggerTypes(reader)
        print('\nReader:')
        d = interpret.getReaderDict(reader)
        pprint(d)
        print('\nHeader:')
        h = interpret.getHeaderDict(reader)
        pprint(h)
        print('\nStatus:')
        s = interpret.getStatusDict(reader)
        pprint(s)

        createFile(reader)