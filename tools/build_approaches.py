"""Builds approaches.json for Boston Logan (KBOS) from FAA CIFP (ARINC 424) records.

    python3 build_approaches.py <cifp file> > approaches.json

Same shape as the NYC site's approaches.json: one entry per published approach, with the lateral
path from about 15 nm out to the landing threshold, the glide angle, threshold crossing height and
threshold elevation. Works on the full FAACIFP18 file or an extract holding the KBOS records.
"""
import json, math, sys

APT, ICAO = 'KBOS', 'K6'
lines = [l.rstrip('\n') for l in open(sys.argv[1], encoding='latin-1') if l.startswith('S')]

def ll(s):  # N42211455 / W071003727 -> degrees
    h, v = s[0], s[1:]
    if len(v) == 8: d, m, sec = int(v[:2]), int(v[2:4]), int(v[4:]) / 100
    else: d, m, sec = int(v[:3]), int(v[3:5]), int(v[5:]) / 100
    x = d + m / 60 + sec / 3600
    return -x if h in 'SW' else x

def nm(a, b):
    la = math.radians((a[0] + b[0]) / 2)
    return math.hypot((a[0] - b[0]) * 60, (a[1] - b[1]) * 60 * math.cos(la))

# Fixes: terminal waypoints (P C), enroute waypoints (E A), runways (P G).
fixes, rwys = {}, {}
for l in lines:
    if l[4] == 'P' and l[6:10] == APT and l[12] == 'C' and l[21] == '1':
        fixes[(l[13:18].strip(), 'PC')] = (ll(l[32:41]), ll(l[41:51]))
    elif l[4:6] == 'EA' and l[21] == '1':
        fixes[(l[13:18].strip(), 'EA')] = (ll(l[32:41]), ll(l[41:51]))
    elif l[4] == 'P' and l[6:10] == APT and l[12] == 'G' and l[21] == '1':
        rid = l[13:18].strip()
        el = int(l[66:71])
        tch = l[95:98].strip()
        rwys[rid] = dict(pos=(ll(l[32:41]), ll(l[41:51])), el=el, tch=int(tch) if tch.isdigit() else 50)
        fixes[(rid, 'PG')] = rwys[rid]['pos']

# Approach legs, primary records only.
procs = {}
for l in lines:
    if not (l[4] == 'P' and l[6:10] == APT and l[12] == 'F' and l[38] == '1'): continue
    pid, rt, tr = l[13:19].strip(), l[19], l[20:25].strip()
    va = l[102:106].strip()
    procs.setdefault(pid, []).append(dict(rt=rt, tr=tr, seq=int(l[26:29]), fix=l[29:34].strip(), sec=l[36:38],
                                          desc=l[39:43], pt=l[47:49], va=-int(va) / 100 if va.lstrip('-').isdigit() else None))

KIND = {'I': ('ILS or LOC', True), 'R': ('RNAV (GPS)', False), 'H': ('RNAV (RNP)', False), 'L': ('LOC', False),
        'X': ('LDA', False), 'D': ('VOR/DME', False), 'V': ('VOR', False), 'P': ('GLS', False)}

def path_of(legs):
    pts = []
    for g in legs:
        p = fixes.get((g['fix'], g['sec'])) if g['fix'] else None
        if p is None:
            if pts and g['pt'] in ('IF', 'TF', 'CF', 'DF'): return None  # a fix we don't have, mid-path
            continue  # missing first fix (an enroute fix not in the extract): start at the next one
        if not pts or pts[-1] != p: pts.append(p)
    return pts

out = []
for pid, legs in sorted(procs.items()):
    t = pid[0]
    if t not in KIND: continue
    rwy = pid[1:4].strip('-').strip()
    if not rwy[:2].isdigit(): continue                     # circling-only
    var = pid[4:].strip()
    if t == 'L' and ('I' + pid[1:]) in procs: continue     # covered by "ILS or LOC"
    final = sorted([g for g in legs if g['rt'] == t], key=lambda g: g['seq'])
    rk = 'RW' + rwy
    if rk not in rwys: continue
    end = next((i for i, g in enumerate(final) if g['fix'] == rk), None)
    if end is None:  # missed approach point short of the runway: draw on to the threshold
        end = next((i for i, g in enumerate(final) if g['desc'][3] == 'M'), None)
        if end is None: continue
    final = final[:end + 1]
    pts = path_of(final)
    if not pts: continue
    if pts[-1] != rwys[rk]['pos']:
        if nm(pts[-1], rwys[rk]['pos']) > 3: continue
        pts.append(rwys[rk]['pos'])
    if len(pts) < 2: continue
    # Carry back through the straightest transition that joins at the first fix, out to 15 nm.
    total = sum(nm(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    if total < 15:
        best = None
        for tr in sorted({g['tr'] for g in legs if g['rt'] == 'A'}):
            tl = path_of(sorted([g for g in legs if g['rt'] == 'A' and g['tr'] == tr], key=lambda g: g['seq']))
            if not tl or len(tl) < 2 or tl[-1] != pts[0]: continue
            def brg(a, b): return math.degrees(math.atan2((b[1] - a[1]) * math.cos(math.radians(a[0])), b[0] - a[0]))
            turn = abs((brg(tl[-2], tl[-1]) - brg(pts[0], pts[1]) + 540) % 360 - 180)
            if turn < 35 and (best is None or turn < best[0]): best = (turn, tl)
        if best:
            tl = best[1][:-1]
            while tl and total < 15:
                a, b = tl[-1], pts[0]
                d = nm(a, b)
                if total + d > 15:
                    f = (15 - total) / d
                    a = (b[0] + (a[0] - b[0]) * f, b[1] + (a[1] - b[1]) * f)
                    d = 15 - total
                pts.insert(0, a); total += d; tl.pop()
    va = next((g['va'] for g in final if g['va']), None)
    name_kind, gs = KIND[t]
    label = rwy.lstrip('0') or rwy
    name = f"{name_kind} {var + ' ' if var and t in 'RHX' else ''}RWY {label}"
    out.append(dict(a='BOS', id=pid.replace(' ', '-').ljust(5, '-') if len(pid) < 5 else pid, t=t, rwy=label, name=name, nick='',
                    gpa=round(va or 3.0, 2), tch=rwys[rk]['tch'], el=rwys[rk]['el'], gs=gs,
                    p=[[round(a, 5), round(b, 5)] for a, b in pts]))

print(json.dumps(out, separators=(',', ':')))
print(f"{len(out)} approaches: " + ', '.join(f"{o['name']} ({sum(nm(o['p'][i], o['p'][i+1]) for i in range(len(o['p'])-1)):.1f} nm)" for o in out), file=sys.stderr)
