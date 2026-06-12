#!/bin/bash

for f in condor/logs/*_42.err; do
    [ -e "$f" ] || continue

    base=$(basename "$f")
    name=${base%_42.err}

    # Skip if name does not contain QCD
    [[ "$name" != *QCD* ]] && continue

    nfiles=$(find condor/logs -maxdepth 1 -name "${name}_*.err" | wc -l)

    avg=$(grep -h "After filter: final cross section" condor/logs/${name}_*.err \
        | awk '
            {
                sum += $(NF-3)
                n++
            }
            END {
                if (n > 0) printf "%.6e", sum/n
                else print "nan"
            }
        ')

    printf "%-60s,%5d,%s\n" "$name" "$nfiles" "$avg"
done
