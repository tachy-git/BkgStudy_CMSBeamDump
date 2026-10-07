#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


FILE_RE = re.compile(r"^CMS_ECal_HCal_(.+)_(\d+)_1E5\.root$")
DEFAULT_INPUT_DIR = Path("/cms/ldap_home/taehee/hyun/CMSBeamDump_build/batch/ECalHCal")


def parse_args():
    parser = argparse.ArgumentParser(description="Create Condor jobs for analyze_root.py.")
    parser.add_argument("--analyzer", default="analyze_root.py", help="analyzer script passed to python3")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="directory containing input ROOT files")
    parser.add_argument("--input-glob", default="CMS_ECal_HCal_*_1E5.root", help="input ROOT file glob")
    parser.add_argument("--job-dir", default=None, help="directory for job list and logs")
    parser.add_argument("--submit-file", default=None, help="Condor submit file to write")
    parser.add_argument("--output-dir", default=None, help="partial ROOT output directory")
    parser.add_argument("--weights", default="../Pythia8/CalW.pkl", help="CalW.pkl path passed to analyzer")
    parser.add_argument("--n-decays", type=int, default=10000, help="toy decays per selected ROOT bin and angle")
    parser.add_argument("--seed", type=int, default=42, help="base random seed")
    parser.add_argument("--request-cpus", type=int, default=1, help="Condor RequestCpus")
    parser.add_argument("--request-memory", type=int, default=40000, help="Condor RequestMemory in MB")
    parser.add_argument("--max-jobs", type=int, default=None, help="optional debug limit")
    return parser.parse_args()


def main():
    args = parse_args()
    work_dir = Path.cwd()
    analyzer = Path(args.analyzer)
    input_dir = Path(args.input_dir)
    analyzer_stem = analyzer.stem
    job_dir = Path(args.job_dir) if args.job_dir is not None else Path("condor") / analyzer_stem
    log_dir = job_dir / "log"
    output_dir = Path(args.output_dir) if args.output_dir is not None else job_dir / "root"
    submit_path = Path(args.submit_file) if args.submit_file is not None else job_dir / "condor.sub"
    job_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    submit_path.parent.mkdir(parents=True, exist_ok=True)

    paths = [path.resolve() for path in sorted(input_dir.glob(args.input_glob)) if FILE_RE.match(path.name)]
    if args.max_jobs is not None:
        paths = paths[: args.max_jobs]

    job_list_path = job_dir / "jobs.txt"
    job_list_path.write_text("".join(f"{path}\n" for path in paths))

    command = (
        f"python3 {analyzer} "
        "--input-file $(input_file) "
        f"--weights {args.weights} "
        f"--output-dir {output_dir} "
        f"--n-decays {args.n_decays} "
        f"--seed {args.seed}"
    )

    submit_text = "\n".join(
        [
            "executable              = /usr/bin/env",
            "universe                = vanilla",
            f"initialdir              = {work_dir}",
            f"arguments               = {command}",
            "getenv                  = True",
            f"RequestCpus             = {args.request_cpus}",
            f"RequestMemory           = {args.request_memory}",
            f"output                  = {log_dir}/job.$(Cluster).$(Process).out",
            f"error                   = {log_dir}/job.$(Cluster).$(Process).err",
            f"log                     = {log_dir}/condor.$(Cluster).log",
            "stream_output           = True",
            "stream_error            = True",
            "accounting_group        = group_cms",
            f"queue input_file from {job_list_path}",
            "",
        ]
    )
    submit_path.write_text(submit_text)

    print(f"created_jobs {len(paths)}")
    print(f"job_list {job_list_path}")
    print(f"submit_file {submit_path}")
    print(f"partial_output_dir {output_dir}")
    print(f"submit_command condor_submit {submit_path}")
    print(f"hadd_command hadd {analyzer_stem}.root {output_dir}/hist_*.root")


if __name__ == "__main__":
    main()
