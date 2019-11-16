#!/usr/bin/env python3
'''
This script is meant to submit multiple similar jobs as sbatch to slurm. 
'''
import os
import sys
sys.path.append(os.environ['BEACON_ANALYSIS_DIR'])
import subprocess
import time
import numpy
import yaml




if __name__ == "__main__":

    ###------------###
    ### Parameters ###
    ###------------###

    username = 'dsouthall'
    mem = '16G'
    partition = 'kicp'

    runs = numpy.array([1507,1509,1511])#numpy.arange(1645,1700)

    ###--------###
    ### Script ###
    ###--------###

    for run in runs:
        jobname = 'beacon_%i'%run

        batch = 'sbatch --partition=%s --job-name=%s '%(partition,jobname)

        command = os.environ['BEACON_ANALYSIS_DIR'] + 'analysis/rf_bg_search.py %i'%(run)

        command_queue = batch + command
    
        os.system(command_queue) # Submit to queue

        # Avoid overwhelming the queue with jobs
        while False:

            # Clean up log files
            n_output = subprocess.Popen('ls slurm*.out | wc', shell=True, 
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0].split()[0]
            if n_output.isdigit():
                os.system('rm slurm*.out')

            n_submitted = int(subprocess.Popen('squeue -u %s | wc\n'%username, shell=True, 
                                               stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0].split()[0]) - 1
            
            # Check to see whether to enter holding pattern
            if n_submitted < 200:
                break
            else:
                print('%i jobs already in queue, waiting ...'%(n_submitted), time.asctime(time.localtime()))
                time.sleep(60)
                