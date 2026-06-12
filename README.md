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

This build was verified in `/cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Geant4_build`
with Geant4 11.2.2 from CVMFS. The successful final build command was:

```bash
make -j4
```
