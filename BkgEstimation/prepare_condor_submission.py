#!/usr/bin/env python3

import argparse
import shlex
import sys
from pathlib import Path


DEFAULT_INPUT_DIR = Path(
    "/cms/ldap_home/taehee/hyun/CMSBeamDump_build/batch/ECalHCal"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create Condor jobs for analyzers supporting --input-file.",
        epilog="Pass analyzer options after --. Use {input_stem} in an option value for the input filename without its extension."
    )

    parser.add_argument(
        "--analyzer",
        required=True,
        help="Analyzer script passed to python3",
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing input ROOT files",
    )
    parser.add_argument(
        "--input-glob",
        default="CMS_ECal_HCal_*_1E5.root",
        help="Input ROOT file glob",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Condor configuration subdirectory under condor/ (default: analyzer name); not the analysis output directory",
    )
    parser.add_argument("--request-disk", type=int,
                        help="Optional worker disk reservation in MB")
    parser.add_argument(
        "--request-cpus",
        type=int,
        default=1,
        help="Condor RequestCpus",
    )
    parser.add_argument(
        "--request-memory",
        type=int,
        default=40000,
        help="Condor RequestMemory in MB",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=None,
        help="Optional debug limit",
    )

    argv = sys.argv[1:]
    separator = argv.index("--") if "--" in argv else len(argv)
    args = parser.parse_args(argv[:separator])
    args.analyzer_args = argv[separator + 1:]
    if args.request_disk is not None and args.request_disk <= 0:
        parser.error("--request-disk must be positive")
    if args.max_jobs is not None and args.max_jobs < 0:
        parser.error("--max-jobs must be nonnegative")
    return args


def main():
    args = parse_args()

    work_dir = Path.cwd().resolve()

    analyzer = Path(args.analyzer).resolve()
    analyzer_stem = analyzer.stem
    request_disk = args.request_disk
    input_dir = Path(args.input_dir).expanduser().resolve()
    if not analyzer.is_file():
        raise FileNotFoundError(analyzer)
    if not input_dir.is_dir():
        raise NotADirectoryError(input_dir)

    # Set the output subdirectory under condor/
    output_name = args.output_dir if args.output_dir is not None else analyzer_stem
    output_subdir = Path(output_name)

    if (
        output_subdir.is_absolute()
        or not output_subdir.parts
        or any(part in (".", "..") for part in output_name.split("/"))
    ):
        raise ValueError("--output-dir must be a relative subdirectory under condor/")

    base_dir = (work_dir / "condor" / output_subdir).resolve()

    if not base_dir.is_relative_to(work_dir / "condor"):
        raise ValueError("--output-dir must remain inside condor/")

    log_dir = base_dir / "log"
    job_list_path = base_dir / "jobs.txt"
    submit_path = base_dir / "condor.sub"
    log_dir.mkdir(parents=True, exist_ok=True)

    paths = [path.resolve() for path in sorted(input_dir.glob(args.input_glob))
             if path.is_file()]

    if args.max_jobs is not None:
        paths = paths[:args.max_jobs]

    if not paths:
        job_list_path.write_text("")
        print("No inputs to submit.")
        return

    # Write job list
    job_list_path.write_text(
        "".join(f"{path}\n" for path in paths)
    )

    # Quote literal pieces separately; only the input stem is expanded by bash.
    def quote_argument(value):
        return '"${input_stem}"'.join(
            shlex.quote(piece) for piece in value.split("{input_stem}"))

    command = " ".join([
        "python3", shlex.quote(str(analyzer)), '--input-file "$1"',
        *(quote_argument(value) for value in args.analyzer_args),
    ])
    queue = f"queue {len(paths)}"

    # Initialize CMSSW on the worker instead of relying on the submitter's shell.
    worker = base_dir / "run_analysis.sh"
    worker.write_text(
        "#!/bin/bash\nset -eo pipefail\n"
        "unset PYTHONHOME PYTHONPATH\n"
        "source /cvmfs/cms.cern.ch/cmsset_default.sh\n"
        "cd /cms/ldap_home/taehee/CMSSW_15_1_0/src\n"
        'cmssw_runtime=$(scram runtime -sh)\n'
        'eval "$cmssw_runtime"\n'
        f"cd {shlex.quote(str(work_dir))}\n"
        # Read the path by job index so Condor never needs to quote filenames.
        + f"mapfile -t input_files < {shlex.quote(str(job_list_path))}\n"
        + 'set -- "${input_files[$1]}"\n'
        + 'input_stem=${1##*/}\ninput_stem=${input_stem%.*}\n'
        + f"exec {command}\n"
    )
    worker.chmod(0o755)
    executable = str(worker)

    # Condor submit file
    submit_text = "\n".join(
        [
            f"executable              = {executable}",
            "universe                = vanilla",
            f"initialdir              = {work_dir}",
            "arguments               = $(Process)",
            "getenv                  = True",
            f"RequestCpus             = {args.request_cpus}",
            f"RequestMemory           = {args.request_memory}",
            *([f"RequestDisk             = {request_disk} MB"] if request_disk is not None else []),
            "should_transfer_files   = NO",
            f"output                  = {log_dir}/job.$(Cluster).$(Process).out",
            f"error                   = {log_dir}/job.$(Cluster).$(Process).err",
            f"log                     = {log_dir}/condor.$(Cluster).log",
            "stream_output           = True",
            "stream_error            = True",
            "accounting_group        = group_cms",
            queue,
            "",
        ]
    )

    submit_path.write_text(submit_text)

    # Summary
    print()
    print("=" * 70)
    print("Condor Job Configuration")
    print("=" * 70)

    print(f"analyzer           {analyzer}")
    print(f"input_dir          {input_dir}")
    print(f"created_jobs       {len(paths)}")
    print(f"analyzer_args      {shlex.join(args.analyzer_args)}")
    print(f"request_cpus       {args.request_cpus}")
    print(f"request_memory     {args.request_memory} MB")
    if request_disk is not None:
        print(f"request_disk       {request_disk} MB")

    print()
    print(f"base_output_dir    {base_dir}")
    print(f"log_dir            {log_dir}")
    print(f"job_list           {job_list_path}")
    print(f"submit_file        {submit_path}")

    print()
    print("=" * 70)
    print("Commands")
    print("=" * 70)

    print(f"condor_submit {shlex.quote(str(submit_path))}")

    print()


if __name__ == "__main__":
    main()
