#!/usr/bin/bash
#=======================================================================
# Purpose:
#   This script run ipca_era5.py on 15 variables.
#=======================================================================
SRCPATH="../data/era5/"
OUTPATH="./"

VARS=("u200" "v200" "h500" "q700" "t700" "u700" "v700" "q850" "t850" "u850" "v850" "q925" "t925" "u925" "v925","mslp")
#VARS=("mslp")

for i in "${!VARS[@]}"; do
    INPUT=$SRCPATH/"${VARS[$i]}"
    OUTPUT=$OUTPATH/"${VARS[$i]}"
    python ../utils/ipca_era5.py -i $INPUT -o $OUTPUT -b 4096 -l $OUTPUT.log
done
    
