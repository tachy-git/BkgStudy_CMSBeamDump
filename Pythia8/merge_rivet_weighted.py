#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path

import ROOT


ROOT.gROOT.SetBatch(True)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge allParticles ROOT histograms with process cross-section weights."
    )
    parser.add_argument("--table", default="rivet_xsec_table.txt", help="Input TSV from make_rivet_xsec_table.py")
    parser.add_argument("--root-dir", default="condor/root", help="Directory containing input ROOT files")
    parser.add_argument("--hard-output", default="allParticles_hardQCD_weighted.root")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Skip processes with fewer ROOT files than logs instead of failing",
    )
    return parser.parse_args()


def read_table(path):
    rows = []
    with Path(path).open() as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"process", "category", "n_logs", "total_events", "xsec_mean_pb"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")

        for row in reader:
            rows.append(
                {
                    "process": row["process"],
                    "category": row["category"],
                    "n_logs": int(row["n_logs"]),
                    "total_events": float(row["total_events"]),
                    "xsec_mean_pb": float(row["xsec_mean_pb"]),
                }
            )
    return rows


def open_root(path):
    root_file = ROOT.TFile.Open(str(path))
    if not root_file or root_file.IsZombie():
        raise OSError(f"Could not open ROOT file: {path}")
    return root_file


def add_process_histograms(process, files, scale):
    summed = {}
    for path in files:
        root_file = open_root(path)
        try:
            for key in root_file.GetListOfKeys():
                obj = key.ReadObj()
                if not obj.InheritsFrom("TH1"):
                    continue

                name = obj.GetName()
                if name not in summed:
                    hist = obj.Clone(name)
                    hist.SetDirectory(0)
                    hist.Reset("ICES")
                    summed[name] = hist

                summed[name].Add(obj)
        finally:
            root_file.Close()

    if not summed:
        raise ValueError(f"No TH1/TH2 histograms found for process {process}")

    for hist in summed.values():
        hist.Scale(scale)
    return summed


def merge_into(target, source):
    for name, hist in source.items():
        if name not in target:
            clone = hist.Clone(name)
            clone.SetDirectory(0)
            target[name] = clone
        else:
            target[name].Add(hist)


def write_output(path, histograms):
    output = ROOT.TFile(str(path), "RECREATE")
    if not output or output.IsZombie():
        raise OSError(f"Could not create output ROOT file: {path}")

    try:
        output.cd()
        for name in sorted(histograms):
            histograms[name].Write()
        output.Write()
    finally:
        output.Close()


def print_integral_summary(label, histograms):
    print(f"{label}: wrote {len(histograms)} histograms")
    for name in sorted(histograms):
        print(f"  {name:10s} integral={histograms[name].Integral():.12e}")


def main():
    args = parse_args()
    root_dir = Path(args.root_dir)
    rows = read_table(args.table)

    if not root_dir.is_dir():
        raise SystemExit(f"ROOT directory does not exist: {root_dir}")
    if not rows:
        raise SystemExit(f"No rows found in {args.table}")

    hard_histograms = {}

    for row in rows:
        process = row["process"]
        category = row["category"]
        n_logs = row["n_logs"]
        total_events = row["total_events"]
        xsec_mean_pb = row["xsec_mean_pb"]

        if total_events <= 0:
            raise ValueError(f"Non-positive total_events for {process}: {total_events}")

        files = sorted(root_dir.glob(f"{process}_*.root"))
        if len(files) != n_logs:
            message = (
                f"{process}: found {len(files)} ROOT files in {root_dir}, "
                f"but table has n_logs={n_logs}"
            )
            if args.allow_missing and files:
                print(f"WARNING: {message}; using available files with table normalization")
            else:
                raise RuntimeError(message)

        scale = xsec_mean_pb / total_events
        print(
            f"{process:30s} {category:7s} n_root={len(files):4d} "
            f"total_events={total_events:.12g} xsec_mean_pb={xsec_mean_pb:.12e} "
            f"scale={scale:.12e}"
        )

        process_histograms = add_process_histograms(process, files, scale)
        if category == "HardQCD":
            merge_into(hard_histograms, process_histograms)
        else:
            raise ValueError(f"Unknown category for {process}: {category}")

    if not hard_histograms:
        raise RuntimeError("No HardQCD histograms were merged")

    write_output(args.hard_output, hard_histograms)

    print_integral_summary(args.hard_output, hard_histograms)


if __name__ == "__main__":
    main()
