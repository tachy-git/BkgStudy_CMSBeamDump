#!/bin/bash

rm *root
hadd analyze_root.root condor/analyze_root/root/hist_CMS_ECal_HCal_* &
hadd analyze_root_no_tilt.root condor/analyze_root_no_tilt/root/hist_CMS_ECal_HCal_* &
