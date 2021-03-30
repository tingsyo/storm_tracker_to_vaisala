#!/usr/bin/bash
#=======================================================================
# Purpose:
#   This script converts ERA5 data in grib format into separate netCDF4 
#   files using wgrib and grib_to_netcdf.
#=======================================================================
# Details:
#   The original grib file contains 600 entries, which are 4 150-entry 
# sets at 00Z, 06Z, 12Z, and 18Z in a given day. The entries we need
# are:
# 39:U200:00Z / 189 / ...
# 40:V200:00Z / 190 / ...
# 71:H500:00Z / 221 / ...
# 92:Q700:00Z / 242 / ...
# 93:T700:00Z
# 94:U700:00Z
# 95:V700:00Z
#117:Q850:00Z
#118:T850:00Z
#119:U850:00Z
#120:V850:00Z
#132:Q925:00Z
#133:T925:00Z
#134:U925:00Z
#135:V925:00Z

SRCPATH=$1 #"$HOME/data/ERA5_grib"
OUTPATH=$2 #"$HOME/data/ERA5_nc"

gribidx=(39 40 71 92 93 94 95 117 118 119 120 132 133 134 135) 
surfix=("00_u200.nc" "00_v200.nc" "00_h500.nc" "00_q700.nc" "00_t700.nc" "00_u700.nc" "00_v700.nc" "00_q850.nc" "00_t850.nc" "00_u850.nc" "00_v850.nc" "00_q925.nc" "00_t925.nc" "00_u925.nc" "00_v925.nc")

for f in $SRCPATH/atm-*.grib; do
    fname=$(basename "$f")
    fname="${fname%.*}"
    fname=${fname:4:12}
    for i in "${!gribidx[@]}"; do
        outfile=$OUTPATH/$fname"${surfix[$i]}"
        wgrib $f -d "${gribidx[$i]}" -grib -o tmp.grb 
        grib_to_netcdf -o $outfile tmp.grb
    done
done
    
