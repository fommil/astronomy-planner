#!/usr/bin/env python3

# This script reads all the NGC/IC catalog entries and filters them with rules
# similar to those that capture the Messier and Caldwell entries, differing by
# type. It then outputs the entries in increasing DEC in tables that correspond
# to the pages of the Pocket Sky Atlas, along with other useful information such
# as type, magnitude and size. This makes it a useful table for unplanned /
# adhoc star gazing with no technology to hand. The tables are used to select
# targets, and the atlas is used to actually find them; this effectively
# produces a very practical index.
#
# The sectors are:
#
# - Nh - (N + 3)h
# - split into:
#   - 90...60 (plus all RA to 80), one chart.
#   - 60...30 (3h...1.5h <=> 1.5h...0h page split, repeated)
#   - 30...0
#   -  0...-30
#   - 30...-60
#    -60...-90 (plus all RA from -80), one chart.
#
# Page number 1 is 0h.
# Page number 11 is 3h, etc, until page 80.
#
# The txt file must be extracted from https://www.saguaroastro.org/sac-downloads/
# and placed in this folder.
#
# The following data can be used (with small changes) but isn't great for observation:
#
# wget https://github.com/mattiaverga/OpenNGC/raw/refs/tags/v20231203/database_files/NGC.csv

import csv
import math
import re

# A zero or positive number will remove from the northern sky.
# A negative number will remove from the southern sky.
# Use 90 or higher to see everything.
my_limit = -20

# Manually created file with lookup from NGC/IC to Messier/Caldwell.
# Some entries are not present because they don't have an NGC/IC.
#
# We use these to rewrite the name of entries.
#
# Code,Alias,Name
codes = {}
pops = {}
with open("names.csv", newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        codes[row["Alias"]] = row["Code"]
        pops[row["Alias"]] = row["Name"]

ngc = []

# From OpenNGC
#
# Name;Type;RA;Dec;Const;MajAx;MinAx;PosAng;B-Mag;V-Mag;J-Mag;H-Mag;K-Mag;SurfBr;Hubble;Pax;Pm-RA;Pm-Dec;RadVel;Redshift;Cstar U-Mag;Cstar B-Mag;Cstar V-Mag;M;NGC;IC;Cstar Names;Identifiers;Common names;NED notes;OpenNGC notes;Sources
def parse_openngc():
    with open("NGC.csv", newline="") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            if row["Type"] in {"NonEx", "Dup"}:
                continue

            name = row.get("Name").strip()
            name = re.sub("IC[0]+", "IC", name)
            name = re.sub("NGC[0]+", "NGC", name)
            row["Name"] = re.sub("NGC", "", name)
            if name in codes:
                cat = codes.pop(name)
                # print(f"found {name} as {cat}")
                row["Index"] = name
                row["Name"] = cat
                row["Popular"] = pops[name]

            ra = row.get("RA")
            h, m, s = [float(x) for x in ra.split(":")]
            row["ra_deg"] = (h + m/60.0 + s/3600.0)

            dec = row.get("Dec").strip()
            sign = -1 if dec.startswith("-") else 1
            parts = dec.replace("+", "").replace("-", "").split(":")
            d, m, s = [float(x) for x in parts]
            dec = sign * (d + m/60.0 + s/3600.0)
            row["dec_deg"] = dec

            if abs(my_limit) >= 90 or (my_limit <= 0 and dec > my_limit) or (my_limit > 0 and dec < my_limit):
                ngc.append(row)

sac_to_openngc_type = {
  "GALXY": "G",
  "1STAR": "*",
  "2STAR": "**",
  "3STAR": "Other",
  "4STAR": "Other",
  "8STAR": "Other",
  "NONEX": "NonEx",
  "G+C+N": "*Ass",
  "OPNCL": "OCl",
  "PLNNB": "PN",
  "GALCL": "GGroup",
  "GLOCL": "GCl",
  "ASTER": "Other",
  "DRKNB": "Neb",
  "BRTNB": "Neb",
  "SNREM": "Nova",
  "CL+NB": "Cl+N",
  "QUASR": "Other",
  "GX+DN": "Neb",
  "LMCOC": "OCl",
  "LMCGC": "GCl",
  "LMCDN": "Neb",
  "LMCCN": "*Ass",
  "GX+GC": "GCl",
  "SMCCN": "*Ass",
  "SMCGC": "GCl",
  "SMCOC": "OCl",
  "SMCDN": "Neb"
}

# From SAC
#
# And coerced into the fieldnames used by OpenNGC and by this script.
#
#|OBJECT|OTHER|TYPE|CON|RA|DEC|MAG|SUBR|U2K|TI|SIZE_MAX|SIZE_MIN|PA|CLASS|NSTS|BRSTR|BCHM|NGC DESCR|NOTES|
# PK131+2.1|Abell3|PLNNB|CAS|0212.2|+6409|18.2|16|17|1|60s|||3b||18.8||||
def parse_sac():
    with open("SAC_DeepSky_Ver81_QCQ.TXT", newline="") as f:
        fields = [c.replace("\"", "").strip() for c in f.readline().split(",") if c.strip()]
        r = csv.DictReader(f, delimiter=",", fieldnames=fields)
        next(r)
        for row in r:
            row["Name"] = row["OBJECT"].replace(" ", "")
            row["Type"] = sac_to_openngc_type[row["TYPE"].strip()]
            if row["Type"] in {"NonEx", "Dup"}:
                continue

            name = row["Name"]
            if name in {"NGC651"}:
                # not flagged as dup
                continue

            row["Name"] = re.sub("NGC", "", name)
            if name in codes:
                cat = codes.pop(name)
                row["Index"] = name
                row["Name"] = cat
                row["Popular"] = pops[name]
            else:
                # sometimes Other is much nicer
                other = row["OTHER"].strip()
                if other.startswith("Abell") and name.startswith("PK"):
                    row["Name"] = other

            row["V-Mag"] = float(row["MAG"].strip())

            def parse_size(v):
                if not v:
                    return None
                elif v.endswith("s"):
                    return float(v[:-1].strip()) / 60.0
                elif v.endswith("m"):
                    return float(v[:-1].strip())

            row["MajAx"] = parse_size(row["SIZE_MAX"].strip())
            row["MinAx"] = parse_size(row["SIZE_MIN"].strip())

            v = float(row["SUBR"].strip())
            if v < 99:
                row["SurfBr"] = v

            ra = row["RA"].strip()
            h, m = [float(x) for x in ra.split()]
            ra = (h + m / 60.0)
            row["ra_deg"] = ra
            frac, whole = math.modf(ra)
            s = frac * 60
            row["RA"] = f"{round(h)}:{round(m)}:{round(s)}"

            dec = row["DEC"].strip()
            sign = -1 if dec.startswith("-") else 1
            d, m = [float(x) for x in dec.replace('-', '').replace('+', '').split()]
            dec = sign * (d + m / 60.0)
            row["dec_deg"] = dec

            notes = row["NOTES"].strip()
            if notes:
                note = notes.split(";")[0]
                if not any(ch.isdigit() for ch in note):
                    row["Common names"] = notes.replace(";", ",")

            if abs(my_limit) >= 90 or (my_limit <= 0 and dec > my_limit) or (my_limit > 0 and dec < my_limit):
                ngc.append(row)

#parse_openngc()
parse_sac()

if len(codes) > 0:
    print(f"[WARNING] the following Catalog entries were not found: {codes}")

# why the db doesn't have this is frustrating...
def mu_from_fallback(m, a, b):
    if m < 99:
        if a > 0 and b > 0:
            return round(m + 2.5 * math.log10(a * b) + 8.63, 2)
        if a > 0 or b > 0:
            d = a or b
            return round(m + 5*math.log10(d) + 8.63, 2)
    return None

def visual_filter(row, debug=False):
    name = row["Name"]
    m = float(row.get("V-Mag") or row.get("B-Mag") or 99)
    A = float(row.get("MajAx") or 0)
    B = float(row.get("MinAx") or 0)
    mu = float(row.get("SurfBr") or mu_from_fallback(m, A, B) or 99)
    typ = (row.get("Type") or "")
    size = max(A, B)

    if debug:
        return f"m={m}, A={A}, B={B}, mu={mu}, typ={typ}, size={size}"

    if re.match(r'^[MC]\d+', name):
        # force inclusion of the known catalog entries
        # print(f"{name} m={m}, A={A}, B={B}, mu={mu}, typ={typ}, size={size}")
        return True
    elif typ in {"G", "GPair", "GGroup", "GTrpl"}:
        # C5 sets the bar at mu=25, but we don't want to miss M101 big fuzzies
        return ((m <= 11 or mu <= 15) and 5 <= size) or 15 <= size and mu < 25
    elif typ == "GCl":
        # size is fine, because this naturally enforces a brightness
        return 5 <= size
    elif typ == "OCl":
        # C8 sets the bar at m=10
        # M29 sets the bar at size=3.6
        # C94 (size=7.8), C102 doesn't have any m data
        # print(f"{name} is {mu}")
        return 10 <= size and mu < 15
    elif typ == "PN":
        # I struggle to see anything smaller than
        # the Cats Eye Nebula (size = 0.9, mu = 17)
        return (m <= 10.0 or mu <= 18) and 0.9 <= size
    elif typ in {"HII", "RfN", "SNR", "Neb", "Cl+N", "*Ass", "EMN"}:
        # C31 sets the bar at mu=27
        # M78 sets the bar at size=4.5
        #
        # C49 (NGC2237) and C68 doesn't have mu, so we have a fallback for big things
        #
        # C46 is bright but small, matching globular cluster rules
        return mu <= 20 and 5 <= size
    else:
        if typ not in {"*", "**", "Other", "Nova"}:
            print(f"[WARNING] unknown type {typ}")
            exit(1)
        return False

filtered = [e for e in ngc if visual_filter(e)]
def for_pages(ra_min, ra_max, dec_min, dec_max):
    if ra_min < 0:
        ra_min = 24.0 - ra_min
    if ra_max > 24:
        ra_max = ra_max - 24.0
    low, high = sorted((ra_min, ra_max))
    return [e for e in filtered if low <= e["ra_deg"] <= high and dec_min <= e["dec_deg"] <= dec_max]

def dedupe(lst):
    deduped = []
    for e in lst:
        if e not in deduped:
            deduped.append(e)
    return deduped

print('<style>')
print('@page { margin-left: 5cm; }')
print('h1 { font-size: 60%; }')
print('.no_break { break-inside: avoid; }')
print('table { border-collapse: collapse; width: 100%; text-align: left; border: 0; font-size: 60%; }')
print('th, td { border: 0; white-space: nowrap; }')
print('thead th { border-bottom: 2px solid #000; }')
print('table tr:nth-child(even) { background-color: #f0f0f0; }')
print('tbody tr + tr td { border-top: 1px solid #ccc; }')

print('</style><body>\n')

def render_size(i):
    arcmin, arcsec_dec = divmod(i, 1)
    degs, arcmin = divmod(arcmin, 60)
    arcsec = arcsec_dec * 60

    d = ""
    m = ""
    s = ""

    if degs > 0:
        d = f"{round(degs)}°"
    if arcmin > 0 or (degs > 0 and arcsec > 0):
        m = f"{round(arcmin)}'"
    if arcsec > 0 and degs == 0:
        s = f"{round(arcsec)}\""

    return f"{d}{m}{s}"

for page in range(1, 81):
    relevant = []
    ra = int((page - 1) / 10) * 3
    dec = 90

    # the commented lines here are an alternative way of constructing the data
    # that tries to put more into the sheets, with heavy duplication on the
    # boundaries, as it captures more of what's physically on the pages instead
    # of falling exactly within the RA boundaries. I don't want to delete it
    # because it took me a long time to figure out the bounds by hand!
    if page % 10 == 1:
        # opening page
        dec = 90
        # relevant = dedupe(for_pages(ra, ra + 3, 55, 90) + for_pages(ra - 1, ra + 4, 60, 70) + for_pages(ra - 2, ra + 5, 70, 80) + for_pages(0, 24, 80, 90))
        relevant = for_pages(0, 24, 80, 90)
    elif page % 10 == 2:
        dec = 60
        # relevant = dedupe(for_pages(ra - 0.5, ra + 3.5, 25, 30) + for_pages(ra - 1, ra + 4, 30, 60))
    elif page % 10 == 4:
        dec = 30
        # relevant = for_pages(ra - 0.2, ra + 3.2, -5, 35)
    elif page % 10 == 6:
        dec = 0
        # relevant = for_pages(ra - 0.2, ra + 3.2, -35, 5)
    elif page % 10 == 8:
        dec = -30
        # relevant = dedupe(for_pages(ra - 0.5, ra + 3.5, -30, -25) + for_pages(ra - 1, ra + 4, -60, -30))
    elif page % 10 == 0:
        dec = -60
        # closing page
        # relevant = dedupe(for_pages(ra, ra + 3, -90, -55) + for_pages(ra - 1, ra + 4, -70, -60) + for_pages(ra - 2, ra + 5, -80, -70) + for_pages(0, 24, -90, -80))
        relevant = for_pages(0, 24, -90, -80)
    else:
        # right side pages are included in the lefts
        continue

    relevant = dedupe(relevant + for_pages(ra, ra + 3, dec - 30, dec))
    if not relevant:
        continue

    relevant.sort(key=lambda x: x["dec_deg"], reverse=True)

    if page > 1 and page % 10 == 1:
        print('\n\n<div style="page-break-after: always;"></div>\n')

    print('<div class="no_break">')
    print(f"<h1>Chart {page} ({ra}<sup>h</sup>...{ra+3}<sup>h</sup> / {dec-30}°...{dec}°)</h1>")
    print('<table><thead>')
    print('<tr><th>Name</th><th>RA</th><th>Dec</th><th>Type</th><th>Mag</th><th>Size</th><th>Bright</th><th>Notes</th></tr>')
    print('</thead><tbody>')
    for e in relevant:
        name = e["Name"]
        ra = e["RA"]
        h, m, s = [float(x) for x in ra.split(":")]
        ra = f"{h:g}h {m:g}m"

        dec = round(e["dec_deg"], 1)
        if dec >= 0:
            dec = f"+{dec}"

        typ = e["Type"]
        mag = round(float(e.get("V-Mag") or e.get("B-Mag") or 99), 1)
        a = round(float(e.get("MajAx") or 0), 1)
        b = round(float(e.get("MinAx") or 0), 1)
        bright = e.get("SurfBr") or mu_from_fallback(mag, a, b) or "-"
        if bright != "-":
            bright = round(float(bright), 1)

        if mag >= 99:
            mag = "-"
        size = "-"
        if a > 0 and b > 0:
            #size = f"{render_size(a)}x{render_size(b)}"
            size = render_size(max(a, b))
        elif a:
            size = render_size(a)
        elif b:
            size = render_size(b)

        notes = e.get("Index") or ""

        if (common := e.get("Popular")):
            notes += "; " if notes else ""
            notes += common
        elif (common := e.get("Common names")):
            # these are usually lower quality notes
            notes += "; " if notes else ""
            notes += common

        notes = notes[:30]

        if not notes:
            notes = "-"

        print(f"<tr><td>{name}</td><td>{ra}</td><td>{dec}</td><td>{typ}</td><td>{mag}</td><td>{size}</td><td>{bright}</td><td>{notes}</tr>")

    print('</tbody></table></div>')
print('</body>')

# Local Variables:
# compile-command: "./planner.py > plan.html && firefox plan.html"
# End:
