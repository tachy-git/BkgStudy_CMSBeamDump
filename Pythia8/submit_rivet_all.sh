#!/usr/bin/env bash
set -euo pipefail

base_dir="/cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Pythia8"
production_dir="${base_dir}/condor"
if [[ "${1:-}" == "--output-dir" && $# == 2 ]]; then
  production_dir="$2"
  [[ "$production_dir" = /* ]] || production_dir="${PWD}/${production_dir}"
elif [[ $# != 0 ]]; then
  echo "Usage: $0 [--output-dir DIRECTORY]" >&2
  exit 2
fi
submit_file="${production_dir}/submit_rivet_all.generated.sub"
events=10000

mkdir -p "${production_dir}/logs" "${production_dir}/root"

cat > "${submit_file}" <<EOT
universe = vanilla
executable = ${base_dir}/run_rivet_condor_job.sh
accounting_group = group_cms
getenv = True
request_memory = 8 GB

log = ${production_dir}/logs/rivet_all.log
EOT

add_job() {
  local sample="$1"
  local config="$2"
  local pthat_min="$3"
  local pthat_max="$4"
  local seed="$5"

  cat >> "${submit_file}" <<EOT
arguments = ${sample} ${config} ${pthat_min} ${pthat_max} ${seed} ${events} ${production_dir}
output = ${production_dir}/logs/${sample}_${seed}.out
error = ${production_dir}/logs/${sample}_${seed}.err
queue

EOT
}

pthat_bins=(
  "5 15"
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

  for seed in $(seq 42 241); do
    add_job "${sample}" "pythia_hardQCD_rivet.py" "${pthat_min}" "${pthat_max}" "${seed}"
  done
done

echo "Wrote ${submit_file}"
condor_submit "${submit_file}"
