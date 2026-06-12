#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${WORK_DIR:-${REPO_DIR}/Geant4_condor}"
EXE="${EXE:-${REPO_DIR}/Geant4_build/exampleB1}"
SETUP="${SETUP:-/cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-dbg/setup.sh}"
THREADS="${THREADS:-1}"
EVENTS="${EVENTS:-100000}"
ENV_SIZE_Z="${ENV_SIZE_Z:-23.0}"
BEAM_Z_CM="${BEAM_Z_CM:--130}"
REQUEST_MEMORY_MB="${REQUEST_MEMORY_MB:-6144}"
DRYRUN=0

usage() {
  cat <<EOF
Usage: $0 [--dryrun]

Generate CMS ECal/HCal Geant4 Condor jobs.

Environment overrides:
  WORK_DIR     Output area for generated mac/sh/root/log files
  EXE          Path to exampleB1 executable
  SETUP        Environment setup script sourced by each job
  THREADS      Geant4 threads per job, default: ${THREADS}
  EVENTS       Events per job, default: ${EVENTS}
  ENV_SIZE_Z   Detector envSizeZ command value, default: ${ENV_SIZE_Z}
  BEAM_Z_CM    Gun z position in cm, default: ${BEAM_Z_CM}
  REQUEST_MEMORY_MB  Condor memory request in MB, default: ${REQUEST_MEMORY_MB}

By default this generates files and runs condor_submit. Use --dryrun to only
generate files.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dryrun|--dry-run)
      DRYRUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

MAC_DIR="${WORK_DIR}/mac"
SH_DIR="${WORK_DIR}/sh"
ROOT_DIR="${WORK_DIR}/root"
LOG_DIR="${WORK_DIR}/log"
SUBMIT_DIR="${WORK_DIR}/submit"

mkdir -p "${MAC_DIR}" "${SH_DIR}" "${ROOT_DIR}" "${LOG_DIR}" "${SUBMIT_DIR}"

JOBS_LIST="${SUBMIT_DIR}/jobs.list"
SUBMIT_FILE="${SUBMIT_DIR}/cms_ecal_hcal.submit"

python3 - "$MAC_DIR" "$SH_DIR" "$ROOT_DIR" "$JOBS_LIST" "$EXE" "$SETUP" "$THREADS" "$EVENTS" "$ENV_SIZE_Z" "$BEAM_Z_CM" <<'PY'
import math
import os
import stat
import sys

mac_dir, sh_dir, root_dir, jobs_list, exe, setup, threads, events, env_size_z, beam_z_cm = sys.argv[1:]

particles = [
    (22, "photon", "gamma"),
    (12, "nue", "nu_e"),
    (-12, "nueb", "anti_nu_e"),
    (14, "numu", "nu_mu"),
    (-14, "numub", "anti_nu_mu"),
    (16, "nutau", "nu_tau"),
    (-16, "nutaub", "anti_nu_tau"),
    (111, "pi0", "pi0"),
    (211, "pip", "pi+"),
    (-211, "pim", "pi-"),
    (221, "eta", "eta"),
    (321, "kp", "kaon+"),
    (-321, "km", "kaon-"),
    (2212, "p", "proton"),
    (-2212, "pb", "anti_proton"),
    (2112, "n", "neutron"),
    (-2112, "nb", "anti_neutron"),
    (11, "e", "e-"),
    (-11, "ep", "e+"),
    (-13, "mup", "mu+"),
    (13, "mum", "mu-"),
]

energies = []
e = 1.0e-3
while e < 5.0e3:
    if e >= 10.0:
        energies.append(e)
    e *= math.pow(10.0, 0.1)

with open(jobs_list, "w", encoding="utf-8") as jobs:
    job_index = 0
    for pdgid, label, g4name in particles:
        for ebin, energy in enumerate(energies, start=1):
            job_index += 1
            name = f"CMS_ECal_HCal_{label}_{pdgid}_{ebin}_1E5"
            macro_path = os.path.join(mac_dir, f"{name}.mac")
            shell_path = os.path.join(sh_dir, f"{name}.sh")
            root_base = os.path.join(root_dir, name)
            seed1 = 1000003 + 2 * job_index
            seed2 = 2000003 + 2 * job_index

            with open(macro_path, "w", encoding="utf-8") as macro:
                macro.write(f"""/random/setSeeds {seed1} {seed2}
/run/numberOfThreads {threads}
/detector/envSizeZ {env_size_z}
/run/initialize
/analysis/setFileName {root_base}
/gun/position 0 0 {beam_z_cm} cm
/gun/momentum 0 0 1
/gun/particle {g4name}
/gun/energy {energy:.17g} GeV
/run/beamOn {events}
""")

            with open(shell_path, "w", encoding="utf-8") as shell:
                shell.write(f"""#!/usr/bin/env bash
set -euo pipefail
set +u
source "{setup}"
set -u
"{exe}" "{macro_path}"
""")
            os.chmod(shell_path, os.stat(shell_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            jobs.write(f"{shell_path} {name}\n")

print(f"Generated {len(particles) * len(energies)} jobs")
print(f"Energy bins: {len(energies)} from {energies[0]:.17g} to {energies[-1]:.17g} GeV")
PY

cat > "${SUBMIT_FILE}" <<EOF
universe = vanilla
executable = \$(script)
output = ${LOG_DIR}/\$(name).out
error = ${LOG_DIR}/\$(name).err
log = ${LOG_DIR}/condor.log
request_cpus = ${THREADS}
request_memory = ${REQUEST_MEMORY_MB} MB
getenv = True
accounting_group = group_cms
queue script,name from ${JOBS_LIST}
EOF

echo "Macro directory: ${MAC_DIR}"
echo "Shell directory: ${SH_DIR}"
echo "ROOT directory:  ${ROOT_DIR}"
echo "Log directory:   ${LOG_DIR}"
echo "Submit file:     ${SUBMIT_FILE}"

if [[ "${DRYRUN}" -eq 1 ]]; then
  echo "Dry run only. Submit with:"
  echo "  $0"
else
  condor_submit "${SUBMIT_FILE}"
fi
