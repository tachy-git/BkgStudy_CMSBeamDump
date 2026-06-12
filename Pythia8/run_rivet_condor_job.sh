#!/usr/bin/env bash
set -euo pipefail

sample="$1"
config="$2"
pthat_min="$3"
pthat_max="$4"
seed="$5"
events="$6"

base_dir="/cms/ldap_home/taehee/BkgStudy_CMSBeamDump/Pythia"
cmssw_src="/cms/ldap_home/taehee/CMSSW_14_0_18/src"
output_dir="${base_dir}/root"
output_base="${sample}_${seed}"
work_dir="${_CONDOR_SCRATCH_DIR:-/tmp}/rivet_${sample}_${seed}_$$"

mkdir -p "${work_dir}" "${output_dir}"
cd "${cmssw_src}"

source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsenv

export RIVET_ANALYSIS_PATH="${base_dir}"

cd "${work_dir}"

cmsrun_args=(
  "${base_dir}/${config}"
  "maxEvents=${events}"
  "iSeed=${seed}"
  "outputBase=${output_base}"
)

if [[ "${config}" == "pythia_hardQCD_rivet.py" ]]; then
  cmsrun_args+=("pTHatMin=${pthat_min}")
  cmsrun_args+=("pTHatMax=${pthat_max}")
fi

cmsRun "${cmsrun_args[@]}"

mv allParticles.root "${output_dir}/${output_base}.root"
if [[ -f "${output_base}.yoda" ]]; then
  mv "${output_base}.yoda" "${output_dir}/${output_base}.yoda"
fi
