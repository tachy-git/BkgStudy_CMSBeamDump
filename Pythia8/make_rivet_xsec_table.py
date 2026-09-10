#!/usr/bin/env python3
import argparse
import re
from collections import defaultdict
from pathlib import Path


XSEC_RE = re.compile(
    r"After filter:\s+final cross section\s*=\s*([0-9.+\-eE]+)\s*\+-\s*([0-9.+\-eE]+)\s*pb"
)
EVENT_RE = re.compile(
    r"Filter efficiency \(event-level\)=\s*\(([0-9.+\-eE]+)\)\s*/\s*\(([0-9.+\-eE]+)\)"
)
FALLBACK_EVENT_RE = re.compile(
    r"Filter efficiency \(taking into account weights\)=\s*\(([0-9.+\-eE]+)\)\s*/\s*\(([0-9.+\-eE]+)\)"
)
LOG_NAME_RE = re.compile(r"^(.+)_(\d+)\.err$")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a process-level cross section table from Rivet Condor logs."
    )
    parser.add_argument("--log-dir", default="condor/logs", help="Directory containing *.err files")
    parser.add_argument("--output", default="rivet_xsec_table.txt", help="Output TSV file")
    return parser.parse_args()


def category_for(process):
    if process.startswith("HardQCD_Bin-PT-"):
        return "HardQCD"
    raise ValueError(f"Cannot infer category for process '{process}'")


def parse_log(path):
    text = path.read_text(errors="replace")

    xsec_match = XSEC_RE.search(text)
    if not xsec_match:
        raise ValueError(f"Missing final cross section line in {path}")

    event_match = EVENT_RE.search(text) or FALLBACK_EVENT_RE.search(text)
    if not event_match:
        raise ValueError(f"Missing filter efficiency event count line in {path}")

    passed_events = float(event_match.group(1))
    if passed_events <= 0:
        raise ValueError(f"Non-positive generated event count in {path}: {passed_events}")

    return float(xsec_match.group(1)), passed_events


def main():
    args = parse_args()
    log_dir = Path(args.log_dir)
    output = Path(args.output)

    if not log_dir.is_dir():
        raise SystemExit(f"Log directory does not exist: {log_dir}")

    by_process = defaultdict(list)
    for path in sorted(log_dir.glob("*.err")):
        match = LOG_NAME_RE.match(path.name)
        if not match:
            continue

        process, seed = match.groups()
        if not process.startswith("HardQCD_Bin-PT-"):
            continue

        xsec_pb, events = parse_log(path)
        by_process[process].append((int(seed), xsec_pb, events, path))

    if not by_process:
        raise SystemExit(f"No HardQCD logs found in {log_dir}")

    rows = []
    for process in sorted(by_process):
        entries = by_process[process]
        n_logs = len(entries)
        total_events = sum(events for _, _, events, _ in entries)
        xsec_mean_pb = sum(xsec for _, xsec, _, _ in entries) / n_logs
        events_per_log = total_events / n_logs
        rows.append(
            (
                process,
                category_for(process),
                n_logs,
                events_per_log,
                total_events,
                xsec_mean_pb,
            )
        )

    with output.open("w") as handle:
        handle.write("process\tcategory\tn_logs\tevents_per_log\ttotal_events\txsec_mean_pb\n")
        for process, category, n_logs, events_per_log, total_events, xsec_mean_pb in rows:
            handle.write(
                f"{process}\t{category}\t{n_logs:d}\t{events_per_log:.12g}\t"
                f"{total_events:.12g}\t{xsec_mean_pb:.12e}\n"
            )

    print(f"Wrote {output}")
    print(f"Processes: {len(rows)}")
    for process, category, n_logs, events_per_log, total_events, xsec_mean_pb in rows:
        print(
            f"{process:30s} {category:7s} logs={n_logs:4d} "
            f"events/log={events_per_log:.12g} total_events={total_events:.12g} "
            f"xsec_mean_pb={xsec_mean_pb:.12e}"
        )


if __name__ == "__main__":
    main()
