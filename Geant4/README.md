# BkgStudy_CMSBeamDump

## Geant4 compilation

Keep the Geant4 source and build directories separate:

```text
BkgStudy_CMSBeamDump/
  Geant4/
  Geant4_build/
```

The source directory should contain `CMakeLists.txt`, `exampleB1.cc`,
`include/`, `src/`, and the macro files. Configure and compile from the build
directory:

```bash
cd /cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Geant4_build
cmake -DGeant4_DIR=/cvmfs/cms.cern.ch/el9_amd64_gcc12/external/geant4/11.2.2-96274063466de81dd6bd0c2db0e072f2/lib64/cmake/Geant4 ../Geant4
make -j4
```

If CMake cannot find Geant4, load the CMS/Geant4 environment first, then rerun
the same commands:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /cms/ldap_home/taehee/CMSSW_14_0_18/src
cmsenv
cd /cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Geant4_build
cmake -DGeant4_DIR=/cvmfs/cms.cern.ch/el9_amd64_gcc12/external/geant4/11.2.2-96274063466de81dd6bd0c2db0e072f2/lib64/cmake/Geant4 ../Geant4
make -j4
```

Run an existing macro with:

```bash
./exampleB1 /cms/scratch/hyunyong/Geant4/CMSBeamDump_build/batch/ECalHCal/CMS_ECal_HCal_p_2212_0_1E5.mac
```

## Geant4 test job

A 10-event proton smoke-test macro is provided at:

```text
Geant4/CMS_ECal_HCal_p_2212_12_10evt_test.mac
```

The macro uses 10 Geant4 worker threads, a 176.88966891446282 GeV proton beam
from `z = -130 cm`, `envSizeZ = 23.0`, and writes:

```text
CMS_ECal_HCal_p_2212_12_10evt_test.root
```

Run it from the build directory:

```bash
cd /cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Geant4_build
./exampleB1 ../Geant4/CMS_ECal_HCal_p_2212_12_10evt_test.mac
```

The working macro order is important: set detector properties before
`/run/initialize`, then set gun and analysis commands after initialization.
The original 100k-event macro order with repeated initialize/reinitialize
caused the job to sit idle.

Note: `/detector/envMaterial` is intentionally omitted from the test macro.
In the current detector code it only changes the printed `env_matm` value and
does not change the ECal, HCal, or world materials.

## ROOT histograms

The ROOT histograms are created in:

```text
Geant4/src/B1RunAction.cc
```

and filled in:

```text
Geant4/src/B1TrackingAction.cc
```

For the 3D histograms, the axes are:

```text
x: particle total energy [GeV]
y: theta angle [rad]
z: z position [cm]
```

This build was verified in `/cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Geant4_build`
with Geant4 11.2.2 from CVMFS. The successful final build command was:

```bash
make -j4
```

## Pythia8/Rivet all-particle analysis

The Pythia8/Rivet files copied from
`/cms/ldap_home/taehee/CMSSW_14_0_18/src` are stored in:

```text
Pythia8/
```

The key files are:

```text
Pythia8/allParticles.cc          custom Rivet analysis source
Pythia8/RivetallParticles.so     compiled Rivet plugin
Pythia8/pythia_test.py           small CMSSW/Rivet test config
Pythia8/pythia_softQCD_rivet.py  SoftQCD production config
Pythia8/pythia_hardQCD_rivet.py  HardQCD pTHat-bin production config
Pythia8/run_rivet_condor_job.sh  per-job Condor runner
Pythia8/submit_rivet_all.sh      Condor submission helper
```

The `allParticles` analysis loops over all particles in each event and fills
ROOT `TH2D` histograms of particle energy versus polar angle. Its ROOT output
file is `allParticles.root`.

Load the CMSSW environment, then run from the copied Pythia8 directory:

```bash
cd /cms/ldap_home/taehee/CMSSW_14_0_18/src
cmsenv
cd /cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Pythia8
export RIVET_ANALYSIS_PATH=$PWD
```

Check that Rivet and ROOT are available:

```bash
which rivet
which rivet-buildplugin
which root-config
```

Check that Rivet can see the custom analysis:

```bash
rivet --show-analysis allParticles
```

If it is working, Rivet prints an entry headed:

```text
allParticles
============
```

Rebuild the plugin after editing `allParticles.cc`:

```bash
rivet-buildplugin RivetallParticles.so allParticles.cc $(root-config --cflags --libs)
```

`rivet-buildplugin` may print a deprecation warning suggesting `rivet-build`;
the command above still works in the CMSSW environment.

Run Rivet directly on a HepMC file with:

```bash
rivet -a allParticles input.hepmc
```

This loads `RivetallParticles.so` from `RIVET_ANALYSIS_PATH` and writes
`allParticles.root`.

Run a small CMSSW/Rivet test:

```bash
cmsRun pythia_test.py
```

`pythia_test.py` runs the CMSSW Rivet analyzer with:

```python
process.load('GeneratorInterface.RivetInterface.rivetAnalyzer_cfi')
process.rivetAnalyzer.AnalysisNames = cms.vstring('allParticles')
process.rivetAnalyzer.OutputFile = cms.string('allParticles.yoda')
process.generation_step += process.rivetAnalyzer
```

This writes the standard Rivet output `allParticles.yoda` and the ROOT output
from the custom plugin, `allParticles.root`.

Submit the SoftQCD and HardQCD Condor production jobs with:

```bash
cd /cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Pythia8
./submit_rivet_all.sh
```

The helper writes generated Condor files under `Pythia8/condor/` and output
ROOT/YODA files under `Pythia8/root/`.

## Condor production jobs

The Condor helper script is:

```text
Geant4/condor/submit_cms_ecal_hcal_jobs.sh
```

It generates jobs for these particles:

```text
photon, pip, pim, kp, km, p, pb, n, nb, e, ep, mup, mum
```

The energy grid is built from log-spaced bin edges:

```text
low edge:  1e-3 GeV to 5e3 GeV
log step:  0.1 in log10(E)
```

Bins whose low edge is below `10 GeV` are skipped, but the global bin index is
kept. The generated bins are therefore indexed `41..67`. The energy-bin center
is the geometric center of each kept total-energy log bin:

```text
Etotal_center = sqrt(E_low * E_high)
```

The first kept bin is index `41` with center `11.220184543019641 GeV`. The last
kept bin is index `67` with center `4466.8359215096352 GeV`.

The Geant4 `/gun/energy` command expects kinetic energy, not total energy. The
macro generator therefore subtracts the beam-particle rest mass:

```text
Egun_kinetic = Etotal_center - m_particle
```

For photons this is unchanged because the mass is zero. For protons, bin `41`
uses `11.220184543019641 - 0.93827208943 = 10.281912453589641 GeV`.

By default the script generates 100 independent seed replicas per
particle/energy sample and 1000 events per job. With 13 active particles, 27
energy bins, and 100 replicas, the default production is 35100 Condor jobs.
Filenames are:

```text
CMS_ECal_HCal_<particle>_<pdgid>_<Ebin>_1E3_<replica>.mac
```

The matching ROOT output basename uses the same pattern, so one
particle/energy sample can be globbed across replicas, for example:

```text
CMS_ECal_HCal_photon_22_41_1E3_*.root
```

The script writes one Condor submit file per particle and energy bin. Each
submit file queues all seed replicas for that particle/energy sample and sets
`JobBatchName` to the same sample-level prefix as the ROOT files, for example
`CMS_ECal_HCal_photon_22_41_1E3`. With the default 100 replicas, each
`condor_submit` sends 100 jobs instead of sending all 2700 photon jobs at once.

During real submission, the script throttles between submit files so the queue
limit is not exceeded. These production constants are fixed in the script:

```text
ENV_SIZE_Z=23.0
BEAM_Z_CM=-130
MAX_MYJOBS=4900
MAX_ALLJOBS=19000
QUEUE_SLEEP_SECONDS=360
```

Generated files are separated under `Geant4_condor/`:

```text
Geant4_condor/mac/     generated macro files
Geant4_condor/sh/      generated per-job shell scripts
Geant4_condor/root/    ROOT output target directory
Geant4_condor/log/     per-job stdout/stderr files and shared Condor event log
Geant4_condor/submit/  Condor submit file and job list
```

`Geant4_condor/` is ignored by git because it is generated output.

Submit the jobs:

```bash
cd /cms/ldap_home/taehee/BkgStudy_CMSBeamDump
cd Geant4/condor
./submit_cms_ecal_hcal_jobs.sh
```

Submit only one particle species:

```bash
./submit_cms_ecal_hcal_jobs.sh --particle photon
./submit_cms_ecal_hcal_jobs.sh --particle 2212
```

Generate the Condor files without submitting:

```bash
cd /cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Geant4/condor
./submit_cms_ecal_hcal_jobs.sh --dryrun
```

Each generated job shell sources:

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-dbg/setup.sh
```

and runs the local executable:

```bash
/cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Geant4_build/exampleB1 <macro>
```

Useful overrides:

```bash
THREADS=4 EVENTS=100000 REPLICAS=20 REQUEST_MEMORY_MB=8192 WORK_DIR=/path/to/workdir ./submit_cms_ecal_hcal_jobs.sh
./submit_cms_ecal_hcal_jobs.sh --replicas 5 --particle photon --dryrun
EXE=/path/to/exampleB1 ./submit_cms_ecal_hcal_jobs.sh --dryrun
```

If Condor holds jobs with a message like `Job has gone over cgroup memory
limit`, either reduce `THREADS` or increase `REQUEST_MEMORY_MB` and resubmit.
The default is `THREADS=2` and `REQUEST_MEMORY_MB=12288`, a compromise between
the stable one-thread memory footprint and the higher memory use seen with
eight-thread Geant4 jobs.
