#!/usr/bin/env python3
"""No-tilt dimuon histograms with cumulative energy, pT, DeltaR, eta selection."""
import argparse
import math
import os
import pickle
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import ROOT


ROOT.gROOT.SetBatch(True)

G4POT = 1.0e5
LUMI_SCALE = 3.0  # CalW.pkl is normalized to 1 ab^-1; target normalization is 3 ab^-1
IE_MIN = 41
IE_MAX = 66
ENERGY_MIN = 10.0
Z_MAX_CM = 20.0
MUON_PT_MIN = 10.0
MUON_ABS_ETA_MAX = 2.4
N_DECAYS = 10000
DEFAULT_SEED = 42
RNG = np.random.default_rng(DEFAULT_SEED)
WORKER_WEIGHTS = None
OUTPUT_DIR = Path("condor/dimuon")
DIMUON_DR_MIN = 0.02

MUON_MASS = 0.1056583755
PI0_MASS = 0.1349768
DETECTOR_RADIUS_M = {"ECal": 1.29, "HCal": 1.79}
DETECTORS = ("ECal", "HCal")
FILE_RE = re.compile(r"^CMS_ECal_HCal_(.+)_(\d+)_1E5\.root$")

INCIDENT = {
    "e": 11,
    "ep": -11,
    "km": -321,
    "kp": 321,
    "n": 2112,
    "nb": -2112,
    "p": 2212,
    "pb": -2212,
    "pim": -211,
    "pip": 211,
    "photon": 22,
}

MODES = {
    "eta_221": {
        "kind": "two_body",
        "label": "eta -> mu mu",
        "mass": 0.547862,
        "width": 1.31e-6,
        "br": 5.8e-6,
    },
    "rho_113": {
        "kind": "two_body",
        "label": "rho -> mu mu",
        "mass": 0.77526,
        "width": 0.1474,
        "br": 4.55e-5,
    },
    "omega_223": {
        "kind": "two_body",
        "label": "omega -> mu mu",
        "mass": 0.78266,
        "width": 0.00868,
        "br": 7.4e-5,
    },
    "phi_333": {
        "kind": "two_body",
        "label": "phi -> mu mu",
        "source": "omega_223",
        "scale": 0.5,
        "mass": 1.019461,
        "width": 0.004249,
        "br": None,
    },
    "eta_continuum": {
        "kind": "three_body",
        "product": "eta_221",
        "label": "eta -> mu mu gamma",
        "mass": 0.547862,
        "m3": 0.0,
        "dalitz": "pseudoscalar_to_gamma",
        "br": 3.1e-4,
    },
    "omega_continuum": {
        "kind": "three_body",
        "product": "omega_223",
        "label": "omega -> mu mu pi0",
        "mass": 0.78266,
        "m3": PI0_MASS,
        "dalitz": "vector_to_pseudoscalar",
        "br": 1.73e-4,
    },
}

ETA_REGIONS = (
    ("abseta_lt0p8", 0.0, 0.8, "abs eta < 0.8"),
    ("abseta_0p8_to2p4", 0.8, 2.4, "0.8 < abs eta < 2.4"),
)

HIST_1D_SPECS = {
    "pt": ("muon pT [GeV]", 200, 0.0, 200.0),
    "meson_energy": ("meson energy before decay [GeV]", 200, 0.0, 200.0),
    "abs_eta": ("muon |eta|", 60, 0.0, 3.0),
    "dimuon_dr": ("#DeltaR(#mu,#mu)", 100, 0.0, 1.0),
    "dimuon_mass_fine": ("m_{#mu#mu} [GeV]", 300, 0.0, 3.0),
}

# All arrays include ROOT underflow and overflow bins.
HISTOGRAMS = (
    ("meson_energy_before_cut", "meson_energy", "meson energy before energy cut"),
    ("meson_energy_after_cut", "meson_energy", "meson energy after energy cut"),
    ("pt", "pt", "muon pT before muon cuts"),
    ("abs_eta", "abs_eta", "muon |eta| before muon cuts"),
    ("dimuon_dr", "dimuon_dr", "dimuon DeltaR before muon cuts"),
    ("dimuon_dr_after_pT_cut", "dimuon_dr", "dimuon DeltaR after pT cut only"),
    ("dimuon_mass_fine_before_cuts", "dimuon_mass_fine", "mass before muon cuts"),
    ("dimuon_mass_fine_after_pT_cut", "dimuon_mass_fine", "mass after pT cut only"),
    ("dimuon_mass_fine_after_all_cuts", "dimuon_mass_fine", "mass after pT DeltaR eta cuts"),
)
CUTFLOW_STAGES = ("before_energy_cut", "energy", "energy_pt", "energy_pt_dr", "energy_pt_dr_eta")


def log(message):
    print(message, flush=True)


def mode_product(mode):
    if "product" in mode:
        return mode["product"]
    if "source" in mode:
        return mode["source"]
    return None


def mode_weight_factor(mode):
    if mode["br"] is not None:
        return mode["br"]
    return mode["scale"] * mode_weight_factor(MODES[mode["source"]])


def mode_parent_factor(mode):
    if "source" not in mode:
        return 1.0
    return mode["scale"] * mode_parent_factor(MODES[mode["source"]])


def parse_input_file(path):
    match = FILE_RE.match(Path(path).name)
    if not match:
        raise ValueError(f"unexpected input file name: {path}")
    return match.group(1), int(match.group(2))


def open_root(path):
    if (not path.exists()) or path.stat().st_size < 1024:
        return None
    try:
        rf = ROOT.TFile.Open(str(path))
    except OSError:
        return None
    if not rf or rf.IsZombie():
        return None
    return rf


def energy_bin_allowed(axis, ix):
    return axis.GetBinLowEdge(ix) >= ENERGY_MIN - 1.0e-12


def z_bin_allowed(axis, iz):
    return axis.GetBinUpEdge(iz) <= Z_MAX_CM + 1.0e-12


def eta_from_theta(theta_rad):
    return -math.log(math.tan(theta_rad / 2.0))


def eta_region_from_theta(theta_rad):
    abs_eta = abs(eta_from_theta(theta_rad))
    for name, low, high, _ in ETA_REGIONS:
        if low <= abs_eta < high:
            return name
    return None


def sample_breit_wigner(mass, width, n, min_mass):
    if width < 1.0e-5:
        return np.full(n, mass)
    out = []
    while sum(len(x) for x in out) < n:
        cand = mass + 0.5 * width * RNG.standard_cauchy(n)
        keep = cand > min_mass
        out.append(cand[keep])
    return np.concatenate(out)[:n]


def rotate_to_lab(p, incident_angle_rad):
    st = math.sin(incident_angle_rad)
    ct = math.cos(incident_angle_rad)
    px_lab = ct * p[:, 0] + st * p[:, 2]
    pz_lab = -st * p[:, 0] + ct * p[:, 2]
    return np.column_stack((px_lab, p[:, 1], pz_lab))


def pseudorapidity(momentum):
    pt = np.hypot(momentum[:, 0], momentum[:, 1])
    return np.arcsinh(momentum[:, 2] / pt)


def azimuth(momentum):
    return np.arctan2(momentum[:, 1], momentum[:, 0])


def delta_phi(phi1, phi2):
    return (phi1 - phi2 + np.pi) % (2.0 * np.pi) - np.pi


def invariant_mass(p1, e1, p2, e2):
    total_p = p1 + p2
    mass2 = (e1 + e2) ** 2 - np.sum(total_p * total_p, axis=1)
    return np.sqrt(np.maximum(mass2, 0.0))


def build_decay_sample(p1, e1, p2, e2, radius, incident_angle_rad):
    pt1 = np.hypot(p1[:, 0], p1[:, 1])
    pt2 = np.hypot(p2[:, 0], p2[:, 1])
    eta1 = pseudorapidity(p1)
    eta2 = pseudorapidity(p2)
    abs_eta1 = np.abs(eta1)
    abs_eta2 = np.abs(eta2)
    mass = invariant_mass(p1, e1, p2, e2)
    dr = np.sqrt((eta1 - eta2) ** 2 + delta_phi(azimuth(p1), azimuth(p2)) ** 2)
    pt_mask = (pt1 > MUON_PT_MIN) & (pt2 > MUON_PT_MIN)
    eta_mask = (abs_eta1 < MUON_ABS_ETA_MAX) & (abs_eta2 < MUON_ABS_ETA_MAX)
    masks = {"pt": pt_mask, "eta": eta_mask}

    observables = {
        "pt1": pt1,
        "pt2": pt2,
        "abs_eta1": abs_eta1,
        "abs_eta2": abs_eta2,
        "pt_min": np.minimum(pt1, pt2),
        "abs_eta_max": np.maximum(abs_eta1, abs_eta2),
        "dimuon_mass": mass,
        "dimuon_dr": dr,
    }
    return {"observables": observables, "masks": masks, "n_valid": len(mass)}


def empty_decay_sample():
    empty_bool = np.zeros(0, dtype=bool)
    empty_float = np.zeros(0, dtype=float)
    masks = {"pt": empty_bool, "eta": empty_bool}
    observables = {
        "pt1": empty_float,
        "pt2": empty_float,
        "abs_eta1": empty_float,
        "abs_eta2": empty_float,
        "pt_min": empty_float,
        "abs_eta_max": empty_float,
        "dimuon_mass": empty_float,
        "dimuon_dr": empty_float,
    }
    return {"observables": observables, "masks": masks, "n_valid": 0}


def two_body_sample(mode, parent_energy, incident_angle_rad, radius):
    masses = sample_breit_wigner(mode["mass"], mode["width"], N_DECAYS, 2.0 * MUON_MASS)
    valid = parent_energy > masses
    if not np.any(valid):
        return empty_decay_sample()
    masses = masses[valid]

    parent_p = np.sqrt(np.maximum(parent_energy * parent_energy - masses * masses, 0.0))
    beta = parent_p / parent_energy
    gamma = parent_energy / masses
    e_star = masses / 2.0
    p_star = np.sqrt(np.maximum(e_star * e_star - MUON_MASS * MUON_MASS, 0.0))

    cos_star = RNG.uniform(-1.0, 1.0, len(masses))
    sin_star = np.sqrt(1.0 - cos_star * cos_star)
    phi = RNG.uniform(0.0, 2.0 * np.pi, len(masses))
    px = p_star * sin_star * np.cos(phi)
    py = p_star * sin_star * np.sin(phi)
    pz = p_star * cos_star

    pz1 = gamma * (pz + beta * e_star)
    pz2 = gamma * (-pz + beta * e_star)
    e1 = gamma * (e_star + beta * pz)
    e2 = gamma * (e_star - beta * pz)
    p1 = rotate_to_lab(np.column_stack((px, py, pz1)), incident_angle_rad)
    p2 = rotate_to_lab(np.column_stack((-px, -py, pz2)), incident_angle_rad)

    return build_decay_sample(p1, e1, p2, e2, radius, incident_angle_rad)


def kallen(x, y, z):
    return x * x + y * y + z * z - 2.0 * (x * y + y * z + z * x)


def dalitz_q2_weight(q2, parent_mass, m3, dalitz_type):
    """Legacy dimuon-mass model from 260624_TH.py, with form factors set to 1."""
    lepton = np.sqrt(np.maximum(1.0 - 4.0 * MUON_MASS * MUON_MASS / q2, 0.0))
    lepton *= 1.0 + 2.0 * MUON_MASS * MUON_MASS / q2

    if dalitz_type == "pseudoscalar_to_gamma":
        x = q2 / (parent_mass * parent_mass)
        return np.maximum(1.0 - x, 0.0) ** 3 * lepton / q2

    if dalitz_type == "vector_to_pseudoscalar":
        delta = parent_mass * parent_mass - m3 * m3
        bracket = (1.0 + q2 / delta) ** 2 - 4.0 * parent_mass * parent_mass * q2 / (delta * delta)
        return np.maximum(bracket, 0.0) ** 1.5 * lepton / q2

    raise ValueError(f"unknown Dalitz type {dalitz_type}")


def sample_s12(parent_mass, m1, m2, m3, n, dalitz_type):
    s_min = (m1 + m2) ** 2
    s_max = (parent_mass - m3) ** 2
    if parent_mass <= m1 + m2 + m3:
        raise ValueError("parent mass must exceed the three-body mass threshold")
    if n < 0:
        raise ValueError("sample size must be nonnegative")
    if n == 0:
        return np.zeros(0, dtype=float)
    # On the physical interval the lepton and Dalitz factors are each <= 1.
    # This bound avoids underestimating the rejection envelope on a finite grid.
    w_max = 1.0 / s_min
    out = []
    accepted = 0
    while accepted < n:
        cand = RNG.uniform(s_min, s_max, n)
        w = dalitz_q2_weight(cand, parent_mass, m3, dalitz_type)
        keep = cand[RNG.uniform(0.0, w_max, n) < w]
        out.append(keep)
        accepted += len(keep)
    return np.concatenate(out)[:n]


def random_unit(n):
    c = RNG.uniform(-1.0, 1.0, n)
    s = np.sqrt(1.0 - c * c)
    phi = RNG.uniform(0.0, 2.0 * np.pi, n)
    return np.column_stack((s * np.cos(phi), s * np.sin(phi), c))


def boost_along(v, energy, direction, beta):
    gamma = 1.0 / np.sqrt(1.0 - beta * beta)
    p_par = np.sum(v * direction, axis=1)
    v_perp = v - p_par[:, None] * direction
    p_par_boost = gamma * (p_par + beta * energy)
    e_boost = gamma * (energy + beta * p_par)
    return v_perp + p_par_boost[:, None] * direction, e_boost


def three_body_sample(mode, parent_energy, incident_angle_rad, radius):
    """Legacy fixed-mass Dalitz model; muon directions in the pair frame are isotropic."""
    parent_mass = mode["mass"]
    if parent_energy <= parent_mass or parent_mass <= 2.0 * MUON_MASS + mode["m3"]:
        return empty_decay_sample()

    s12 = sample_s12(parent_mass, MUON_MASS, MUON_MASS, mode["m3"], N_DECAYS, mode["dalitz"])
    m12 = np.sqrt(s12)
    q_p = np.sqrt(np.maximum(kallen(parent_mass**2, s12, mode["m3"] ** 2), 0.0)) / (2.0 * parent_mass)
    q_e = (parent_mass**2 + s12 - mode["m3"] ** 2) / (2.0 * parent_mass)
    q_dir = random_unit(N_DECAYS)

    mu_p_q = np.sqrt(np.maximum(kallen(s12, MUON_MASS**2, MUON_MASS**2), 0.0)) / (2.0 * m12)
    mu_e_q = m12 / 2.0
    mu_dir = random_unit(N_DECAYS)
    p1_q = mu_p_q[:, None] * mu_dir
    p2_q = -p1_q

    beta_q = q_p / q_e
    p1_parent, e1_parent = boost_along(p1_q, mu_e_q, q_dir, beta_q)
    p2_parent, e2_parent = boost_along(p2_q, mu_e_q, q_dir, beta_q)

    parent_p = math.sqrt(max(parent_energy * parent_energy - parent_mass * parent_mass, 0.0))
    beta_parent = parent_p / parent_energy
    gamma_parent = parent_energy / parent_mass
    p1_parent_z = p1_parent[:, 2].copy()
    p2_parent_z = p2_parent[:, 2].copy()
    e1_lab = gamma_parent * (e1_parent + beta_parent * p1_parent_z)
    e2_lab = gamma_parent * (e2_parent + beta_parent * p2_parent_z)
    p1_parent[:, 2] = gamma_parent * (p1_parent[:, 2] + beta_parent * e1_parent)
    p2_parent[:, 2] = gamma_parent * (p2_parent[:, 2] + beta_parent * e2_parent)

    p1 = rotate_to_lab(p1_parent, incident_angle_rad)
    p2 = rotate_to_lab(p2_parent, incident_angle_rad)
    return build_decay_sample(p1, e1_lab, p2, e2_lab, radius, incident_angle_rad)


def make_1d_arrays():
    return {name: np.zeros(HIST_1D_SPECS[key][1] + 2, dtype=float)
            for name, key, _ in HISTOGRAMS}

def make_outputs():
    return {
        mode_name: {
            det: {
                region: {
                    "h1": make_1d_arrays(),
                    "cutflow": np.zeros(len(CUTFLOW_STAGES), dtype=float),
                }
                for region, _, _, _ in ETA_REGIONS
            }
            for det in DETECTORS
        }
        for mode_name in MODES
    }


def fill_1d(target, values, weight, spec_key):
    if len(values) == 0 or weight == 0.0:
        return
    _, nbins, xmin, xmax = HIST_1D_SPECS[spec_key]
    indices = np.searchsorted(np.linspace(xmin, xmax, nbins + 1), values, side="right")
    target += np.bincount(indices, weights=np.full(len(values), weight), minlength=nbins + 2)

def merge_outputs(target, source):
    for mode_name in MODES:
        for det in DETECTORS:
            for region, _, _, _ in ETA_REGIONS:
                for name in target[mode_name][det][region]["h1"]:
                    target[mode_name][det][region]["h1"][name] += source[mode_name][det][region]["h1"][name]
                target[mode_name][det][region]["cutflow"] += source[mode_name][det][region]["cutflow"]


def get_max_workers(n_tasks):
    try:
        requested = int(os.environ.get("N_WORKERS", 17))
    except ValueError:
        requested = 17
    return max(1, min(requested, n_tasks))


def init_worker(weights, seed):
    global WORKER_WEIGHTS
    WORKER_WEIGHTS = weights
    globals()["DEFAULT_SEED"] = seed
    ROOT.gROOT.SetBatch(True)


def z_limited_integral(hist, ix):
    last_z_bin = 0
    zaxis = hist.GetZaxis()
    for iz in range(1, hist.GetNbinsZ() + 1):
        if z_bin_allowed(zaxis, iz):
            last_z_bin = iz
    if last_z_bin == 0:
        return 0.0
    return float(hist.Integral(ix, ix, 1, hist.GetNbinsY(), 1, last_z_bin))


def fill_meson_energy_before_decay(outputs, hist, weights, pname, e_weight_bin, mode_name, mode, det):
    parent_factor = mode_parent_factor(mode)
    if parent_factor <= 0.0:
        return

    xaxis = hist.GetXaxis()
    for ix in range(1, hist.GetNbinsX() + 1):
        parent_energy = xaxis.GetBinCenterLog(ix)
        yield_z = z_limited_integral(hist, ix)
        if yield_z <= 0.0:
            continue
        for a in range(1, 85):
            w = weights.get((pname, e_weight_bin, a), 0.0)
            if w <= 0.0:
                continue
            region = eta_region_from_theta(math.radians(a + 5.5))
            if region is None:
                continue
            weight = yield_z * w / G4POT * parent_factor * LUMI_SCALE
            h1 = outputs[mode_name][det][region]["h1"]
            fill_1d(h1["meson_energy_before_cut"], np.asarray([parent_energy]), weight, "meson_energy")
            if energy_bin_allowed(xaxis, ix):
                fill_1d(h1["meson_energy_after_cut"], np.asarray([parent_energy]), weight, "meson_energy")


def fill_region_outputs(region_output, sample, decay_weight, energy_pass=True):
    obs = sample["observables"]
    h1 = region_output["h1"]
    cutflow = region_output["cutflow"]
    cutflow[0] += sample["n_valid"] * decay_weight
    if not energy_pass:
        return
    pt = sample["masks"]["pt"]
    pt_dr = pt & (obs["dimuon_dr"] > DIMUON_DR_MIN)
    final = pt_dr & sample["masks"]["eta"]
    for i, mask in enumerate((np.ones(sample["n_valid"], dtype=bool), pt, pt_dr, final), start=1):
        cutflow[i] += np.count_nonzero(mask) * decay_weight
    fill_1d(h1["pt"], np.concatenate((obs["pt1"], obs["pt2"])), decay_weight, "pt")
    fill_1d(h1["abs_eta"], np.concatenate((obs["abs_eta1"], obs["abs_eta2"])), decay_weight, "abs_eta")
    fill_1d(h1["dimuon_dr"], obs["dimuon_dr"], decay_weight, "dimuon_dr")
    fill_1d(h1["dimuon_dr_after_pT_cut"], obs["dimuon_dr"][pt], decay_weight, "dimuon_dr")
    for name, mask in (("dimuon_mass_fine_before_cuts", slice(None)),
                       ("dimuon_mass_fine_after_pT_cut", pt),
                       ("dimuon_mass_fine_after_all_cuts", final)):
        fill_1d(h1[name], obs["dimuon_mass"][mask], decay_weight, "dimuon_mass_fine")

def process_root_file(input_path, weights, task_index=0, seed=DEFAULT_SEED):
    global RNG
    RNG = np.random.default_rng(seed + task_index)
    outputs = make_outputs()

    input_path = Path(input_path)
    pname, e_index = parse_input_file(input_path)
    e_weight_bin = IE_MIN + e_index
    rf = open_root(input_path)
    if not rf:
        return pname, e_index, e_weight_bin, "skip: missing/bad ROOT file", outputs

    summed_w = sum(weights.get((pname, e_weight_bin, a), 0.0) for a in range(1, 85))
    if summed_w <= 0.0:
        rf.Close()
        return pname, e_index, e_weight_bin, "skip: zero weight", outputs

    for det in DETECTORS:
        radius = DETECTOR_RADIUS_M[det]
        for mode_name, mode in MODES.items():
            hist_mode_name = mode_product(mode) or mode_name
            hist = rf.Get(f"{det}_{hist_mode_name}")
            if not hist:
                continue
            fill_meson_energy_before_decay(outputs, hist, weights, pname, e_weight_bin, mode_name, mode, det)
            weight_factor = mode_weight_factor(mode)
            for ix in range(1, hist.GetNbinsX() + 1):
                parent_energy = hist.GetXaxis().GetBinCenterLog(ix)
                yield_z = z_limited_integral(hist, ix)
                if yield_z <= 0.0:
                    continue
                for a in range(1, 85):
                    w = weights.get((pname, e_weight_bin, a), 0.0)
                    if w <= 0.0:
                        continue
                    incident_angle_rad = math.radians(a + 5.5)
                    region = eta_region_from_theta(incident_angle_rad)
                    if region is None:
                        continue
                    if mode["kind"] == "two_body":
                        sample = two_body_sample(mode, parent_energy, incident_angle_rad, radius)
                    elif mode["kind"] == "three_body":
                        sample = three_body_sample(mode, parent_energy, incident_angle_rad, radius)
                    else:
                        raise ValueError(f"unknown decay kind {mode['kind']}")
                    if sample["n_valid"] == 0:
                        continue
                    # Integrate Y once; the mother follows the untilted incident direction.
                    decay_weight = yield_z * w / G4POT * weight_factor * LUMI_SCALE / N_DECAYS
                    fill_region_outputs(outputs[mode_name][det][region], sample, decay_weight,
                                        energy_bin_allowed(hist.GetXaxis(), ix))

    rf.Close()
    return pname, e_index, e_weight_bin, "done", outputs


def process_energy_bin(task):
    task_index, inc_name, inc_pdgid, e_index, e_weight_bin, seed = task
    input_path = Path(f"CMS_ECal_HCal_{inc_name}_{inc_pdgid}_{e_index}_1E5.root")
    return process_root_file(input_path, WORKER_WEIGHTS, task_index=task_index, seed=seed)


def calculate(weights, seed=DEFAULT_SEED):
    log("Start calculation")
    outputs = make_outputs()
    tasks = [
        (task_index, inc_name, inc_pdgid, e_index, e_weight_bin, seed)
        for task_index, (inc_name, inc_pdgid, e_index, e_weight_bin) in enumerate(
            (
                (inc_name, inc_pdgid, e_index, e_weight_bin)
                for inc_name, inc_pdgid in INCIDENT.items()
                for e_index, e_weight_bin in enumerate(range(IE_MIN, IE_MAX + 1))
            )
        )
    ]
    max_workers = get_max_workers(len(tasks))
    log(f"Using {max_workers} workers, N_DECAYS={N_DECAYS}")
    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers, initializer=init_worker, initargs=(weights, seed)) as executor:
        futures = [executor.submit(process_energy_bin, task) for task in tasks]
        for future in as_completed(futures):
            pname, e_index, e_weight_bin, status, partial = future.result()
            merge_outputs(outputs, partial)
            completed += 1
            log(f"[{completed}/{len(tasks)}] {pname} energy bin {e_index} weight bin {e_weight_bin}: {status}")
    log("Calculation done")
    return outputs


def make_root_hist(name, title, values, spec_key):
    axis_title, nbins, xmin, xmax = HIST_1D_SPECS[spec_key]
    hist = ROOT.TH1D(name, f"{title};{axis_title};events / 3 ab^{{-1}}", nbins, xmin, xmax)
    for i, value in enumerate(values):
        hist.SetBinContent(i, float(value))
    return hist


def make_cutflow_hist(name, title, values):
    hist = ROOT.TH1D(name, f"{title};selection stage;events / 3 ab^{{-1}}", len(CUTFLOW_STAGES), 0.5, len(CUTFLOW_STAGES) + 0.5)
    for index, (stage, value) in enumerate(zip(CUTFLOW_STAGES, values), start=1):
        hist.SetBinContent(index, float(value))
        hist.GetXaxis().SetBinLabel(index, stage)
    return hist


def write_metadata(root_file):
    root_file.cd()
    ROOT.TNamed("metadata", (
        "no-tilt dimuon analysis; parent_tilt=disabled; "
        "parent_yield=Z-selected TH3 yield integrated over all Y bins; "
        "eta_region=untilted CalW mother direction; normalization=3 ab^-1; "
        "meson_energy=parent yield without branching ratio; "
        "cutflow=dimuon yield including branching ratio and valid toy decay fraction; "
        "pt_abs_eta=both muons independently after energy cut before muon cuts; "
        "dimuon_dr_mass=one entry per pair after energy cut; "
        "D0_and_radial_angle_cuts=disabled; all_histograms=ROOT underflow and overflow retained; "
        "two_body_mass_model=Breit-Wigner above dimuon threshold, no upper mass cap; "
        "three_body_model=legacy Dalitz q2 weights, form factors 1, isotropic pair-frame muons; "
        f"modes={','.join(MODES)}; energy_bin_low_edge_min_GeV={ENERGY_MIN}; "
        f"z_bin_upper_edge_max_cm={Z_MAX_CM}; muon_pt_strict_min_GeV={MUON_PT_MIN}; "
        f"dimuon_dr_strict_min={DIMUON_DR_MIN}; muon_abs_eta_strict_max={MUON_ABS_ETA_MAX}; "
        f"n_decays={N_DECAYS}; seed={DEFAULT_SEED}; cutflow_stages={','.join(CUTFLOW_STAGES)}"
    )).Write()

def write_outputs(outputs, root_path=None):
    if root_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        root_path = OUTPUT_DIR / "dimuon_selection_histograms.root"
    else:
        root_path = Path(root_path)
        root_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"Writing ROOT histograms to {root_path}")
    root_file = ROOT.TFile(str(root_path), "RECREATE")
    write_metadata(root_file)

    for mode_name, mode in MODES.items():
        for det in DETECTORS:
            for region, _, _, region_label in ETA_REGIONS:
                region_dir = root_file.mkdir(f"{mode_name}_{det}_{region}")
                region_dir.cd()
                region_output = outputs[mode_name][det][region]
                title_prefix = f"{mode['label']} {det}, {region_label}"

                for hist_name, spec_key, label in HISTOGRAMS:
                    hist = make_root_hist(hist_name, f"{title_prefix} {label}", region_output["h1"][hist_name], spec_key)
                    hist.Write()

                cutflow_hist = make_cutflow_hist("cutflow", f"{title_prefix} cutflow", region_output["cutflow"])
                cutflow_hist.Write()

    root_file.Close()
    log("Done writing ROOT histograms")


def partial_output_path(output_dir, input_file):
    stem = Path(input_file).stem
    return Path(output_dir) / f"hist_{stem}.root"


def parse_args():
    parser = argparse.ArgumentParser(description="Build no-tilt dimuon histograms with radial mother meson directions.")
    parser.add_argument("--weights", default="../Pythia8/CalW.pkl", help="path to CalW.pkl")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="output directory")
    parser.add_argument("--input-file", default=None, help="single CMS_ECal_HCal ROOT file for Condor partial mode")
    parser.add_argument("--n-decays", type=int, default=N_DECAYS, help="toy decays per selected ROOT bin and angle")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="base random seed")
    return parser.parse_args()


def main():
    global N_DECAYS, OUTPUT_DIR, DEFAULT_SEED, RNG
    args = parse_args()
    if args.n_decays <= 0:
        raise ValueError("--n-decays must be positive")
    N_DECAYS = args.n_decays
    OUTPUT_DIR = Path(args.output_dir)
    DEFAULT_SEED = args.seed
    RNG = np.random.default_rng(DEFAULT_SEED)

    log("Loading weights")
    with open(args.weights, "rb") as f:
        weights = pickle.load(f)
    if args.input_file:
        log(f"Processing single input file {args.input_file}")
        _, _, _, status, outputs = process_root_file(args.input_file, weights, seed=DEFAULT_SEED)
        log(status)
        write_outputs(outputs, partial_output_path(OUTPUT_DIR, args.input_file))
    else:
        outputs = calculate(weights, seed=DEFAULT_SEED)
        write_outputs(outputs)
    log("Done")


if __name__ == "__main__":
    main()
