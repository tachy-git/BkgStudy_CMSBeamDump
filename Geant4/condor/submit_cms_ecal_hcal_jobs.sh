#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${WORK_DIR:-${REPO_DIR}/Geant4_condor}"
BUILD_DIR="${BUILD_DIR:-${REPO_DIR}/Geant4_build}"
EXE="${EXE:-${BUILD_DIR}/exampleB1}"
SETUP="${SETUP:-/cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-dbg/setup.sh}"
THREADS="${THREADS:-2}"
EVENTS="${EVENTS:-20000}"
REPLICAS="${REPLICAS:-5}"
ENV_SIZE_Z="${ENV_SIZE_Z:-23.0}"
BEAM_Z_CM="${BEAM_Z_CM:--130}"
REQUEST_MEMORY_MB="${REQUEST_MEMORY_MB:-12288}"
DRYRUN=0
PARTICLE_FILTER=""

usage() {
  cat <<EOF
Usage: $0 [--dryrun] [--particle LABEL_OR_PDG] [--replicas N]

Generate CMS ECal/HCal Geant4 Condor jobs.

Environment overrides:
  WORK_DIR     Output area for generated mac/sh/root/log files
  BUILD_DIR    Geant4 build directory, default: ${BUILD_DIR}
  EXE          Path to exampleB1 executable
  SETUP        Environment setup script sourced by each job
  THREADS      Geant4 threads per job, default: ${THREADS}
  EVENTS       Events per job, default: ${EVENTS}
  REPLICAS     Independent seed replicas per particle/energy sample, default: ${REPLICAS}
  ENV_SIZE_Z   Detector envSizeZ command value, default: ${ENV_SIZE_Z}
  BEAM_Z_CM    Gun z position in cm, default: ${BEAM_Z_CM}
  REQUEST_MEMORY_MB  Condor memory request in MB, default: ${REQUEST_MEMORY_MB}

By default this generates files and runs condor_submit. Use --dryrun to only
generate files.

With --particle, only submit one particle species, for example:
  $0 --particle photon
  $0 --particle 2212
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dryrun|--dry-run)
      DRYRUN=1
      shift
      ;;
    --particle)
      if [[ $# -lt 2 ]]; then
        echo "--particle requires a label or PDG ID" >&2
        exit 2
      fi
      PARTICLE_FILTER="$2"
      shift 2
      ;;
    --replicas)
      if [[ $# -lt 2 ]]; then
        echo "--replicas requires a positive integer" >&2
        exit 2
      fi
      REPLICAS="$2"
      shift 2
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

echo "Building Geant4 executable before Condor submission..."
echo "Build directory: ${BUILD_DIR}"
echo "Executable:      ${EXE}"
mkdir -p "${BUILD_DIR}"
set +u
source "${SETUP}"
set -u
cmake -S "${REPO_DIR}/Geant4" -B "${BUILD_DIR}"
cmake --build "${BUILD_DIR}" -- -j4
if [[ ! -x "${EXE}" ]]; then
  echo "Build completed, but executable was not found or is not executable: ${EXE}" >&2
  exit 1
fi

mkdir -p "${MAC_DIR}" "${SH_DIR}" "${ROOT_DIR}" "${LOG_DIR}" "${SUBMIT_DIR}"

JOBS_LIST="${SUBMIT_DIR}/jobs.list"
SUBMIT_FILES_LIST="${SUBMIT_DIR}/submit_files.list"

python3 - "$MAC_DIR" "$SH_DIR" "$ROOT_DIR" "$SUBMIT_DIR" "$JOBS_LIST" "$SUBMIT_FILES_LIST" "$EXE" "$SETUP" "$THREADS" "$EVENTS" "$REPLICAS" "$ENV_SIZE_Z" "$BEAM_Z_CM" "$REQUEST_MEMORY_MB" "$LOG_DIR" "$PARTICLE_FILTER" <<'PY'
import math
import os
import stat
import sys

mac_dir, sh_dir, root_dir, submit_dir, jobs_list, submit_files_list, exe, setup, threads, events, replicas, env_size_z, beam_z_cm, request_memory_mb, log_dir, particle_filter = sys.argv[1:]
event_label = f"{int(events):.0E}".replace("E+0", "E").replace("E+", "E")
threads_int = int(threads)
replicas = int(replicas)
if threads_int < 1:
    raise SystemExit("THREADS must be a positive integer")
if replicas < 1:
    raise SystemExit("REPLICAS/--replicas must be a positive integer")

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

if particle_filter:
    particles = [
        p for p in particles
        if particle_filter in {str(p[0]), p[1], p[2]}
    ]
    if not particles:
        raise SystemExit(f"No particle matched --particle {particle_filter!r}")

energy_bins = []
log_e_min = math.log10(1.0e-3)
log_e_max = math.log10(5.0e3)
log_e_step = 0.1
n_log_bins = math.ceil((log_e_max - log_e_min) / log_e_step)
for i in range(n_log_bins):
    low_edge = math.pow(10.0, log_e_min + i * log_e_step)
    high_edge = math.pow(10.0, log_e_min + (i + 1) * log_e_step)
    ebin = i + 1
    if low_edge < 10.0:
        continue
    energy_bins.append((ebin, math.sqrt(low_edge * high_edge)))

submit_files = []
with open(jobs_list, "w", encoding="utf-8") as jobs:
    job_index = 0
    for pdgid, label, g4name in particles:
        batch = f"CMS_ECal_HCal_{label}_{pdgid}_{event_label}"
        particle_jobs_list = os.path.join(submit_dir, f"{batch}.jobs")
        submit_file = os.path.join(submit_dir, f"{batch}.submit")
        submit_files.append(submit_file)
        particle_jobs = open(particle_jobs_list, "w", encoding="utf-8")
        for ebin, energy in energy_bins:
            for replica in range(replicas):
                job_index += 1
                name = f"CMS_ECal_HCal_{label}_{pdgid}_{ebin}_{event_label}_{replica}"
                macro_path = os.path.join(mac_dir, f"{name}.mac")
                shell_path = os.path.join(sh_dir, f"{name}.sh")
                root_base = os.path.join(root_dir, name)
                seed_values = [
                    str(100000 + ((job_index * 10007 + i * 1009) % 900000))
                    for i in range(threads_int + 1)
                ]
                seed_line = " ".join(seed_values)

                with open(macro_path, "w", encoding="utf-8") as macro:
                    macro.write(f"""/random/setSeeds {seed_line}
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

                line = f"{shell_path} {name}\n"
                jobs.write(line)
                particle_jobs.write(line)
        particle_jobs.close()
        with open(submit_file, "w", encoding="utf-8") as submit:
            submit.write(f"""universe = vanilla
executable = $(script)
output = {log_dir}/$(name).out
error = {log_dir}/$(name).err
log = {log_dir}/condor.log
request_cpus = {threads}
request_memory = {request_memory_mb} MB
getenv = True
accounting_group = group_cms
+JobBatchName = "{batch}"
priority = 1000000
queue script,name from {particle_jobs_list}
""")

with open(submit_files_list, "w", encoding="utf-8") as submit_files_out:
    for submit_file in submit_files:
        submit_files_out.write(f"{submit_file}\n")

print(f"Generated {len(particles) * len(energy_bins) * replicas} jobs")
print(f"Replicas per particle/energy sample: {replicas}")
print(
    f"Energy bins: {len(energy_bins)} "
    f"indices {energy_bins[0][0]}..{energy_bins[-1][0]} "
    f"centers {energy_bins[0][1]:.17g}..{energy_bins[-1][1]:.17g} GeV"
)
PY

echo "Macro directory: ${MAC_DIR}"
echo "Shell directory: ${SH_DIR}"
echo "ROOT directory:  ${ROOT_DIR}"
echo "Log directory:   ${LOG_DIR}"
echo "Submit files:    ${SUBMIT_FILES_LIST}"

if [[ "${DRYRUN}" -eq 1 ]]; then
  echo "Dry run only. Submit with:"
  echo "  while read -r submit_file; do condor_submit \"\${submit_file}\"; done < ${SUBMIT_FILES_LIST}"
else
  while read -r submit_file; do
    condor_submit "${submit_file}"
  done < "${SUBMIT_FILES_LIST}"
fi
