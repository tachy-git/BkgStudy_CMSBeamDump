# Pythia8 HardQCD CalW Production

**Current production:** the plugin writes three jet constituent selections
(pT > 30, 50, 100 GeV). Use the commands in "Jet constituent CalW production"
below with a new `condor_jetcuts` directory. The earlier workflow describes
the legacy inclusive output and must not be used to mix old and new jobs.

This directory produces `CalW.pkl` from binned Pythia8 proton-proton
collision samples at 13.6 TeV. The samples are generated in `pTHat` bins, the
particle energy and polar angle distributions are stored as ROOT histograms,
and the weighted histogram contents are converted into a Python pickle file.

## Overview

The generation uses `pythia_hardQCD_rivet.py`, which enables `HardQCD:all` and
sets the proton-proton center-of-mass energy to 13.6 TeV:

```python
comEnergy = cms.double(13600.0)
```

The output is built from 17 `pTHat` bins:

```text
5-15, 15-20, 20-30, 30-50, 50-80, 80-120, 120-170,
170-300, 300-470, 470-600, 600-800, 800-1000,
1000-1500, 1500-2000, 2000-2500, 2500-3000, 3000+
```

Each bin is submitted with seeds 42 through 241 and 10,000 events per seed.

## Workflow

Run the production in this order:

```bash
./submit_rivet_all.sh
./make_rivet_xsec_table.py
./merge_rivet_weighted.py
./make_CalW_pkl.py
```

### `./submit_rivet_all.sh`

Creates and submits a Condor file at `condor/submit_rivet_all.generated.sub`.
Each Condor job runs `run_rivet_condor_job.sh`, which sets up CMSSW, runs
`cmsRun pythia_hardQCD_rivet.py`, and writes per-job outputs under
`condor/root/`.

The main per-job ROOT output is:

```text
condor/root/<sample>_<seed>.root
```

The job also keeps the Rivet YODA output when it is produced:

```text
condor/root/<sample>_<seed>.yoda
```

### `allParticles.cc`

`allParticles.cc` defines the Rivet analysis plugin used by the generation.
It writes `allParticles.root` in each Condor job.

In `init()`, the plugin opens:

```cpp
rootOut = new TFile("allParticles.root", "RECREATE");
```

It then books one `TH2D` histogram for each configured particle species. The
histogram axes are:

- X axis: particle energy `E` in GeV, with logarithmic bin edges from `1e-3`
  to `5e3`.
- Y axis: polar angle `theta` in degrees, with 1-degree bins from 0 to 180.

In `analyze()`, the plugin loops over `event.allParticles()`. If the particle
PDG ID is one of the configured species, it fills the corresponding histogram
with:

```cpp
hist->second->Fill(particle.E(), momentum.theta() * 180.0 / M_PI);
```

In `finalize()`, all particle histograms are written to `allParticles.root`,
then the ROOT file is closed.

### `./make_rivet_xsec_table.py`

Parses the Condor error logs in `condor/logs/` and extracts the final cross
section and generated event count for each `HardQCD_Bin-PT-*` process.

The output file is:

```text
rivet_xsec_table.txt
```

This table contains:

```text
process  category  n_logs  events_per_log  total_events  xsec_mean_pb
```

### `./merge_rivet_weighted.py`

Reads `rivet_xsec_table.txt` and the per-job ROOT files from `condor/root/`.
For each `pTHat` process, it sums the ROOT histograms and scales them by:

```text
xsec_mean_pb / total_events
```

The merged HardQCD output is:

```text
allParticles_hardQCD_weighted.root
```

This weighted ROOT file is the input to `make_CalW_pkl.py`.

### `./make_CalW_pkl.py`

Reads the weighted `TH2` histograms from:

```text
allParticles_hardQCD_weighted.root
```

It stores selected energy and angle bins into:

```text
CalW.pkl
```

The default scale factor applied to each stored histogram bin content is:

```text
2.0e6
```

This factor is used because only the angular region up to 90 degrees is stored.
The particle distribution is treated as symmetric in eta, so the selected
half-range is multiplied by 2 to account for the opposite side. The remaining
factor of `1e6` converts the normalization from `pb^-1` to `ab^-1`.

## `CalW.pkl` Structure

`CalW.pkl` is a Python pickle containing a dictionary:

```python
dict[tuple[str, int, int], float]
```

Each key has the form:

```python
(particle_label, energy_bin, angle_index)
```

Example:

```python
("photon_22", 41, 1)
```

The fields mean:

- `particle_label`: particle name plus PDG ID, such as `photon_22`, `p_2212`,
  `pi0_111`, or `mum_13`.
- `energy_bin`: ROOT X-axis energy bin index. The stored range is 41 to 66,
  corresponding approximately to 10 GeV through 3981 GeV in the original
  logarithmic energy axis.
- `angle_index`: compact output angle index. The stored range is 1 to 84,
  corresponding to ROOT Y-axis bins covering `6 <= theta < 90` degrees.
- value: the weighted histogram bin content multiplied by the `2.0e6` scale
  factor, where `2.0e6 = 2 * 1e6` accounts for eta symmetry and converts the
  normalization from `pb^-1` to `ab^-1`.

The configured particle labels are:

```text
e_11, ep_-11, eta_221, km_-321, kp_321, lambda_2114,
mum_13, mup_-13, n_2112, nb_-2112,
nue_12, nueb_-12, numu_14, numub_-14,
nutau_16, nutaub_-16, p_2212, pb_-2212,
photon_22, pi0_111, pim_-211, pip_211
```

You can inspect the pickle with:

```python
import pickle

with open("CalW.pkl", "rb") as handle:
    calw = pickle.load(handle)

print(type(calw))
print(len(calw))
print(next(iter(calw.items())))
```

## Plotting `CalW.pkl`

`plot_CalW_pkl.py` provides a quick visual check of the pickle contents:

```bash
./plot_CalW_pkl.py
```

The script loads `CalW.pkl`, rebuilds the same logarithmic energy binning used
in `allParticles.cc`, and creates one energy histogram per particle. For each
particle, it sums the stored `CalW.pkl` weights over all angle bins at each
energy bin.

The script writes PNG files only:

```text
plots/hist_<particle>.png
```

No ROOT file is produced by this plotting script.


## Jet constituent CalW production (30, 50, 100 GeV)

The plugin now builds anti-kT R=0.4 jets from `FinalState()`, using the same
FastJets defaults as the previous jetConstituents analysis. It keeps jets with
|rapidity| <= 3 and fills constituents separately for strict jet pT > 30,
> 50, and > 100 GeV. These are cumulative selections on the same events,
not additional constituent pT or eta cuts. Each job ROOT contains directories
`jetpt30`, `jetpt50`, and `jetpt100`, with the original particle histogram names
and original new energy and polar-angle axes. Decayed intermediates are no
longer counted. A jet threshold is not a pTHat threshold.

Build in CMSSW_14_0_18, then submit to a separate production directory:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /cms/ldap_home/taehee/CMSSW_14_0_18/src
cmsenv
cd /cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Pythia8
rivet-build RivetallParticles.so allParticles.cc $(root-config --cflags --libs)
bash submit_rivet_all.sh --output-dir condor_jetcuts
```

After all jobs finish successfully:

```bash
python3 make_rivet_xsec_table.py --log-dir condor_jetcuts/logs --output condor_jetcuts/rivet_xsec_table.txt
python3 merge_rivet_weighted.py --table condor_jetcuts/rivet_xsec_table.txt --root-dir condor_jetcuts/root --hard-output condor_jetcuts/allParticles_hardQCD_weighted.root
python3 make_CalW_pkl.py --input condor_jetcuts/allParticles_hardQCD_weighted.root --jet-cuts --output condor_jetcuts
```

The three final files are `condor_jetcuts/CalW_jetpt30.pkl`,
`condor_jetcuts/CalW_jetpt50.pkl`, and `condor_jetcuts/CalW_jetpt100.pkl`.
The converter verifies equal key sets and W30 >= W50 >= W100 >= 0 for every
stored bin before writing. Select one with the dimuon analysis `--weights`:

```bash
python3 260907_TH.py --weights /cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Pythia8/condor_jetcuts/CalW_jetpt30.pkl
```

All three use sigma / **all generated events** per pTHat process. Never divide
by jet-selected events or multiply by selection efficiency again. The
2 * 10^6 CalW scale (1 ab^-1 and eta symmetry), 13.6 TeV configuration,
17 pTHat bins, and compact angle index mapping remain the same.
Existing flat-histogram ROOT files can still be converted without `--jet-cuts`.
They cannot be used to reconstruct jet-selected flux; new generation is required.
The older Overview describes the original inclusive format; use this section
for the updated jet production. The existing CalW.pkl is not overwritten.
