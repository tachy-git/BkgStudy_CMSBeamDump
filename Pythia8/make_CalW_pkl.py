#!/usr/bin/env python3
import argparse
import pickle

import ROOT


ROOT.gROOT.SetBatch(True)

INPUT_ROOT = "allParticles_hardQCD_weighted.root"
OUTPUT_PKL = "CalW.pkl"
WEIGHT_SCALE = 2.0e6
ENERGY_FIRST_BIN = 41
ENERGY_LAST_BIN = 66
ANGLE_MIN_DEG = 6.0
ANGLE_MAX_DEG = 90.0

PDGID = {
    "e": 11,
    "ep": -11,
    "eta": 221,
    "km": -321,
    "kp": 321,
    "lambda": 2114,
    "mum": 13,
    "mup": -13,
    "n": 2112,
    "nb": -2112,
    "nue": 12,
    "nueb": -12,
    "numu": 14,
    "numub": -14,
    "nutau": 16,
    "nutaub": -16,
    "p": 2212,
    "pb": -2212,
    "photon": 22,
    "pi0": 111,
    "pim": -211,
    "pip": 211,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Create CalW.pkl from the pre-weighted allParticles ROOT histograms."
        )
    )
    parser.add_argument(
        "--input",
        default=INPUT_ROOT,
        help="Input ROOT file containing pre-weighted allParticles TH2 histograms",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_PKL,
        help="Output pickle file for the CalW weight dictionary",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=WEIGHT_SCALE,
        help="Scale factor applied to each stored histogram bin content",
    )
    return parser.parse_args()


def open_root(path):
    root_file = ROOT.TFile.Open(path)
    if not root_file or root_file.IsZombie():
        raise OSError("Could not open ROOT file: {}".format(path))
    return root_file


def get_histograms(root_file):
    histograms = {}
    for key in root_file.GetListOfKeys():
        obj = key.ReadObj()
        if not obj.InheritsFrom("TH2"):
            continue

        name = obj.GetName()
        if name not in PDGID:
            raise KeyError(
                "No PDG ID is configured for histogram '{}'".format(name)
            )
        histograms[name] = obj

    if not histograms:
        raise ValueError("No TH2 histograms found in input ROOT file")
    return histograms


def angle_bin_range(hist):
    y_axis = hist.GetYaxis()
    first_bin = y_axis.FindBin(ANGLE_MIN_DEG)
    last_bin = y_axis.FindBin(ANGLE_MAX_DEG) - 1

    if first_bin < 1 or last_bin > hist.GetNbinsY() or first_bin > last_bin:
        raise ValueError(
            "{} has no valid angle-bin range for [{}, {}) deg".format(
                hist.GetName(), ANGLE_MIN_DEG, ANGLE_MAX_DEG
            )
        )

    return first_bin, last_bin


def validate_energy_range(hist):
    if ENERGY_FIRST_BIN < 1 or ENERGY_LAST_BIN > hist.GetNbinsX():
        raise ValueError(
            "{} has {} X bins, cannot read energy bins {}-{}".format(
                hist.GetName(),
                hist.GetNbinsX(),
                ENERGY_FIRST_BIN,
                ENERGY_LAST_BIN,
            )
        )


def build_calw(histograms, scale):
    calw = {}
    for name in sorted(histograms):
        hist = histograms[name]
        validate_energy_range(hist)
        first_angle_bin, last_angle_bin = angle_bin_range(hist)
        pname = "{}_{}".format(name, PDGID[name])

        for energy_bin in range(ENERGY_FIRST_BIN, ENERGY_LAST_BIN + 1):
            for angle_index, root_angle_bin in enumerate(
                range(first_angle_bin, last_angle_bin + 1), start=1
            ):
                calw[pname, energy_bin, angle_index] = (
                    hist.GetBinContent(energy_bin, root_angle_bin) * scale
                )

    return calw


def main():
    args = parse_args()
    root_file = open_root(args.input)
    try:
        histograms = get_histograms(root_file)
        calw = build_calw(histograms, args.scale)
    finally:
        root_file.Close()

    with open(args.output, "wb") as output_file:
        pickle.dump(calw, output_file)

    print(
        "Wrote {} weights from {} histograms to {}".format(
            len(calw), len(histograms), args.output
        )
    )


if __name__ == "__main__":
    main()
