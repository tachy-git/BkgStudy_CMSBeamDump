#!/usr/bin/env bash
set -euo pipefail

base_dir="/cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Pythia"
submit_file="${base_dir}/condor/submit_rivet_all.generated.sub"
events=10000

mkdir -p "${base_dir}/condor/logs" "${base_dir}/root"

cat > "${submit_file}" <<EOT
universe = vanilla
executable = ${base_dir}/run_rivet_condor_job.sh
accounting_group = group_cms
getenv = True

log = ${base_dir}/condor/logs/rivet_all.log
EOT

add_job() {
  local sample="$1"
  local config="$2"
  local pthat_min="$3"
  local pthat_max="$4"
  local seed="$5"

  cat >> "${submit_file}" <<EOT
arguments = ${sample} ${config} ${pthat_min} ${pthat_max} ${seed} ${events}
output = ${base_dir}/condor/logs/${sample}_${seed}.out
error = ${base_dir}/condor/logs/${sample}_${seed}.err
queue

EOT
}

for seed in $(seq 42 141); do
  add_job "SoftQCD" "pythia_softQCD_rivet.py" "-1" "-1" "${seed}"
done

pthat_bins=(
  "15 20"
  "20 30"
  "30 50"
  "50 80"
  "80 120"
  "120 170"
  "170 300"
  "300 470"
  "470 600"
  "600 800"
  "800 1000"
  "1000 1500"
  "1500 2000"
  "2000 2500"
  "2500 3000"
  "3000 -1"
)

for bin in "${pthat_bins[@]}"; do
  read -r pthat_min pthat_max <<< "${bin}"
  if [[ "${pthat_max}" == "-1" ]]; then
    sample="HardQCD_Bin-PT-${pthat_min}"
  else
    sample="HardQCD_Bin-PT-${pthat_min}to${pthat_max}"
  fi

  for seed in $(seq 42 141); do
    add_job "${sample}" "pythia_hardQCD_rivet.py" "${pthat_min}" "${pthat_max}" "${seed}"
  done
done

echo "Wrote ${submit_file}"
echo "Submitting 1700 jobs: 100 SoftQCD jobs and 1600 HardQCD pTHat-bin jobs."
condor_submit "${submit_file}"
