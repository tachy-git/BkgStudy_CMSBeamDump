#!/usr/bin/env python3
import argparse
import math
import pickle
import re
from array import array
from pathlib import Path


ENERGY_BIN_START = 1.0e-3
ENERGY_BIN_STOP = 5.0e3
ENERGY_BIN_FACTOR = math.pow(10.0, 0.1)


def build_energy_edges():
    edges = []
    value = ENERGY_BIN_START
    while value < ENERGY_BIN_STOP:
        edges.append(value)
        value *= ENERGY_BIN_FACTOR
    edges.append(value)
    return edges


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name))


def load_calw(path):
    with path.open("rb") as handle:
        data = pickle.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"Expected {path} to contain a dict, got {type(data).__name__}")
    return data


def make_histograms(data, edges):
    import ROOT

    ROOT.gROOT.SetBatch(True)

    nbins = len(edges) - 1
    root_edges = array("d", edges)
    histograms = {}
    skipped = 0

    for key, weight in data.items():
        if not isinstance(key, tuple) or len(key) != 3:
            skipped += 1
            continue

        particle, energy_index, _angle_index = key
        try:
            root_bin = int(energy_index)
            bin_weight = float(weight)
        except (TypeError, ValueError):
            skipped += 1
            continue

        if root_bin < 1 or root_bin > nbins:
            skipped += 1
            continue

        if particle not in histograms:
            hist_name = f"h_energy_{safe_name(particle)}"
            hist = ROOT.TH1D(
                hist_name,
                f"Energy distribution: {particle};Energy [GeV];Weight",
                nbins,
                root_edges,
            )
            hist.Sumw2()
            histograms[particle] = hist

        histograms[particle].AddBinContent(root_bin, bin_weight)

    return histograms, skipped


def save_outputs(histograms, output_dir, edges):
    import ROOT

    output_dir.mkdir(parents=True, exist_ok=True)

    canvas = ROOT.TCanvas("c_energy", "c_energy", 900, 700)
    canvas.SetLogx(True)
    canvas.SetLogy(True)

    for particle, hist in sorted(histograms.items(), key=lambda item: str(item[0])):
        hist.SetLineWidth(2)
        hist.GetXaxis().SetRangeUser(10.0, edges[-1])
        hist.SetStats(0)
        hist.Draw("HIST")
        canvas.SaveAs(str(output_dir / f"hist_{safe_name(particle)}.png"))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Draw per-particle energy histogram PNGs from CalW pickle files."
    )
    parser.add_argument(
        "--input",
        nargs="+",
        default=["CalW.pkl"],
        help="Input pickle file(s). Each file gets its own output subdirectory.",
    )
    parser.add_argument(
        "--output-dir",
        default="plots",
        help="Base directory for PNG histogram files.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_base = Path(args.output_dir)
    edges = build_energy_edges()

    for input_name in args.input:
        input_path = Path(input_name)
        output_dir = output_base / safe_name(input_path.stem)

        data = load_calw(input_path)
        histograms, skipped = make_histograms(data, edges)
        save_outputs(histograms, output_dir, edges)

        print(f"Input pickle: {input_path}")
        print(f"Loaded entries: {len(data)}")
        print(f"Created particle histograms: {len(histograms)}")
        print(f"Skipped entries: {skipped}")
        print(f"PNG output directory: {output_dir}")


if __name__ == "__main__":
    main()
