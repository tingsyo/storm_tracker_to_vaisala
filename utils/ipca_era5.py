#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Purpose:
    This script provide functions that read and perform PCA with ERA5 
    dataset. 
Data:
    The dataset is pre-rpocessed as a single variable at a single time
    stored in netCDF4 format. The domain of the processed data ranged 
    from 10' to 50'N, 100' to 140'E, with 0.25' intervals. The data 
    dimension is (161,161).
Method:
    The PCA is performed with IncrementalPCA from sklearn.
'''
import numpy as np
import pandas as pd
import os, argparse, logging
from netCDF4 import Dataset
from sklearn.decomposition import PCA, IncrementalPCA
import joblib, csv

__author__ = "Ting-Shuo Yo"
__copyright__ = "Copyright 2019~2021, DataQualia Lab Co. Ltd."
__credits__ = ["Ting-Shuo Yo"]
__license__ = "Apache License 2.0"
__version__ = "0.1.0"
__maintainer__ = "Ting-Shuo Yo"
__email__ = "tingyo@dataqualia.com"
__status__ = "development"
__date__ = '2021-03-30'


# Utility functions
def list_era5_files(dir, suffix='.nc'):
    ''' To scan through the sapecified dir and get the corresponding file with suffix. '''
    import os
    import pandas as pd
    xfiles = []
    for root, dirs, files in os.walk(dir, followlinks=True):    # Loop through the directory
        for fn in files:
            if fn.endswith(suffix):                             # Filter files with suffix
                timestamp = fn.replace(suffix,'')[:10]          # Removing the suffix to get time-stamp
                xfiles.append({'timestamp':timestamp, 'xuri':os.path.join(root, fn)})
    return(pd.DataFrame(xfiles).sort_values('timestamp').reset_index(drop=True))

# Binary reader
def read_era5_singlevar(furi):
    ''' The method reads in a ERA5 single variable in netCDF4 format (.nc file). 
        Rhe data domain focuss on East Asia (10-50'N, 100-140'E), and the output 
        is a 2-d numpy array of float32 with shape (161, 161).
    '''
    import numpy as np
    import netCDF4 as nc
    # Read in data
    data = nc.Dataset(furi)
    varname = list(data.variables.keys())[-1]
    var = np.array(data.variables[varname])
    # Done
    return(var[0,:,:])

def read_multiple_era5(flist, flatten=False):
    ''' This method reads in a list of NOAA-GridSat-B1 images and returns a numpy array. '''
    import numpy as np
    data = []
    for f in flist:
        tmp = read_era5_singlevar(f)
        if flatten:
            tmp = tmp.flatten()
        data.append(tmp)
    return(np.array(data))


# Incremental PCA
def fit_ipca_partial(finfo, n_component=20, batch_size=128, rseed=0):
    ''' Initial and fit a PCA model with incremental PCA. '''
    # Shuffle file list if specified
    if rseed!=0:
        flist = flist.sample(frac=1, random_state=rseed).reset_index(drop=True)
        logging.info('Shuffling the input data for batch processing with random seed: '+str(rseed))
    # Initialize the PCA object
    ipca = IncrementalPCA(n_components=n_component, whiten=True, batch_size=batch_size)
    # Loop through finfo
    nSample = len(finfo)
    batch_start = 0
    batch_end = batch_size
    batch_count = 0
    while batch_start < nSample:
        logging.debug('Starting batch: '+str(batch_count))
        # Check bound
        limit = min(batch_end, nSample)             # Check for the final batch
        if n_component>(nSample-batch_end):         # Merge the final batch if it's too small
            logging.info('The final batch is too small, merge it to the previous batch.')
            limit = nSample
        # Read batch data
        data = read_multiple_era5(finfo['xuri'].iloc[batch_start:limit], flatten=True)
        logging.debug(data.shape)
        # increment
        batch_start = limit   
        batch_end = limit + batch_size
        batch_count += 1
        # Partial fit with batch data
        ipca.partial_fit(data)
    #
    return(ipca)

# Incremental PCA
def transform_ipca_partial(finfo, model, batch_size=128):
    ''' Transform the data by batch with trained incremental PCA. '''
    # Loop through finfo
    n_component = model.n_components_
    nSample = len(finfo)
    batch_start = 0
    batch_end = batch_size
    batch_count = 0
    # Output
    proj_full = None
    while batch_start < nSample:
        logging.debug('Starting batch: '+str(batch_count))
        # Check bound
        limit = min(batch_end, nSample)             # Check for the final batch
        if n_component>(nSample-batch_end):         # Merge the final batch if it's too small
            logging.info('The final batch is too small, merge it to the previous batch.')
            limit = nSample
        # Read batch data
        data = read_multiple_era5(finfo['xuri'].iloc[batch_start:limit], flatten=True)
        logging.debug(data.shape)
        # increment
        batch_start = limit   
        batch_end = limit + batch_size
        batch_count += 1
        # Partial transform with batch data
        proj_batch = model.transform(data)
        if proj_full is None:
            proj_full = proj_batch
        else:
            proj_full = np.vstack([proj_full, proj_batch])
    #
    return(proj_full)

def writeToCsv(output, fname, header=None):
    # Overwrite the output file:
    with open(fname, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_ALL)
        if header is not None:
            writer.writerow(header)
        for r in output:
            writer.writerow(r)
    return(0)
#-----------------------------------------------------------------------
def main():
    # Configure Argument Parser
    parser = argparse.ArgumentParser(description='Performing Incremental PCA on ERA5 data.')
    parser.add_argument('--datapath', '-i', help='the directory containing ERA5 data in netCDF4 format.')
    parser.add_argument('--output', '-o', help='the prefix of output files.')
    parser.add_argument('--logfile', '-l', default=None, help='the log file.')
    parser.add_argument('--n_component', '-n', default=50, type=int, help='the number of PCs to derive.')
    parser.add_argument('--batch_size', '-b', default=1024, type=int, help='the batch size.')
    parser.add_argument('--random_seed', '-r', default=0, type=int, help='the random seed for shuffling.')
    args = parser.parse_args()
    # Set up logging
    if not args.logfile is None:
        logging.basicConfig(level=logging.DEBUG, filename=args.logfile, filemode='w')
    else:
        logging.basicConfig(level=logging.DEBUG)
    logging.debug(args)
    # Get data files
    logging.info('Scanning data files.')
    datainfo = list_era5_files(args.datapath, suffix='.nc')
    #datainfo.to_csv(args.output+'.file_info.csv', index=False)
    # IncrementalPCA
    logging.info("Performing IncrementalPCA with "+ str(args.n_component)+" components and batch size of " + str(args.batch_size))
    ipca = fit_ipca_partial(datainfo, n_component=args.n_component, batch_size=args.batch_size, rseed=args.random_seed)
    # Project the data by batch
    projections = transform_ipca_partial(datainfo, model=ipca, batch_size=args.batch_size)
    projdf = pd.DataFrame(projections)
    projdf.insert(0, 'timestamp', datainfo['timestamp'])
    projdf.to_csv(args.output+".proj.csv", index=False)
    # Preparing output
    ev = ipca.explained_variance_
    evr = ipca.explained_variance_ratio_
    com = np.transpose(ipca.components_)
    logging.info("Explained variance ratio: "+ str(evr))
    # Output components
    com_header = ['pc'+str(x+1) for x in range(args.n_component)]
    #writeToCsv(com, args.output+'.components.csv', header=com_header)
    #pd.DataFrame({'ev':ev, 'evr':evr}).to_csv(args.output+'.exp_var.csv')
    # Output fitted IPCA model
    joblib.dump(ipca, args.output+".pca.mod")
    # done
    return(0)
    
#==========
# Script
#==========
if __name__=="__main__":
    main()