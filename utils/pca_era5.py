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
    The PCA is performed with PCA from sklearn.decomposition.
'''
import numpy as np
import pandas as pd
import os, argparse, logging
from netCDF4 import Dataset
from sklearn.decomposition import PCA
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
def fit_pca(finfo, n_component=20):
    ''' Initial and fit a PCA model with sklearn.decomposition.PCA. '''
    # Initialize the PCA object
    pca = PCA(n_components=n_component, whiten=True)
    # Load Data
    data = read_multiple_era5(finfo['xuri'], flatten=True)
    # Fit and transform
    proj = pca.fit_transform(data)
    #
    return(pca, proj)

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
    logging.info("Performing PCA with "+ str(args.n_component)+" components.")
    pca, projections = fit_pca(datainfo, n_component=args.n_component)
    # Project the data by batch
    projdf = pd.DataFrame(projections)
    projdf.insert(0, 'timestamp', datainfo['timestamp'])
    projdf.to_csv(args.output+".proj.csv", index=False)
    # Preparing output
    ev = pca.explained_variance_
    evr = pca.explained_variance_ratio_
    com = np.transpose(pca.components_)
    logging.info("Explained variance ratio: "+ str(evr))
    # Output components
    com_header = ['pc'+str(x+1) for x in range(args.n_component)]
    #writeToCsv(com, args.output+'.components.csv', header=com_header)
    #pd.DataFrame({'ev':ev, 'evr':evr}).to_csv(args.output+'.exp_var.csv')
    # Output fitted IPCA model
    joblib.dump(pca, args.output+".pca.mod")
    # done
    return(0)
    
#==========
# Script
#==========
if __name__=="__main__":
    main()