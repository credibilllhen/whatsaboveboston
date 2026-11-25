"""Boston-area land for whatsabove.boston.
Massachusetts: 2020 Census municipalities (clipped to the shoreline). Elsewhere (NH, RI): OSM 10 m land.
Output: land_enc.json, polygons as delta-encoded rings at 1e-4 degrees, [lon, lat] pairs."""
import json, math, sys, warnings
warnings.filterwarnings('ignore')
import shapely
from shapely.geometry import shape, Polygon, MultiPolygon, box, mapping
from shapely.ops import unary_union, transform
X0, Y0, X1, Y1 = -72.1, 41.55, -69.85, 43.15
ma = unary_union([shape(f['geometry']).buffer(0) for f in json.load(open('src/ma-boundaries/ma-municipalities-2020census.geojson'))['features']])
ma = shapely.clip_by_rect(ma, X0, Y0, X1, Y1)
osm = shape(json.load(open('bos_land_raw.json')))
LAT0 = 42.36; K = math.cos(math.radians(LAT0))
fw = lambda x, y, z=None: (x * 111.32 * K, y * 110.57)
bw = lambda x, y, z=None: (x / (111.32 * K), y / 110.57)
mak, osk = transform(fw, ma), transform(fw, osm)
far = osk.difference(mak.buffer(4))            # NH and RI, away from Massachusetts
near = osk.intersection(mak.buffer(4)).difference(mak)
# OSM land within 4 km of Massachusetts: keep the strips along the NH and RI borders (they join the
# far land), drop the coarse coastal pieces around Massachusetts' own shore
keep = [q for q in getattr(near, 'geoms', [near]) if q.distance(far) < 0.05]
land = unary_union([mak, far] + keep)
r = float(sys.argv[1]) if len(sys.argv) > 1 else 0.06
land = land.buffer(r).buffer(-2 * r).buffer(r).simplify(0.045)
def chaikin(c, n=2):
    for _ in range(n):
        o = []
        for i in range(len(c) - 1):
            (a, b), (x, y) = c[i], c[i + 1]
            o += [(.75 * a + .25 * x, .75 * b + .25 * y), (.25 * a + .75 * x, .25 * b + .75 * y)]
        o.append(o[0]); c = o
    return c
polys = []
for p in getattr(land, 'geoms', [land]):
    if p.area < 0.03: continue
    holes = [chaikin(list(h.coords)) for h in p.interiors if Polygon(h).area > 1.0]
    polys.append(Polygon(chaikin(list(p.exterior.coords)), holes))
mm = transform(bw, MultiPolygon(polys)).buffer(0)
json.dump(mapping(mm), open('bos_land.json', 'w'))
enc, n = [], 0
for p in getattr(mm, 'geoms', [mm]):
    pe = []
    for ring in [p.exterior] + list(p.interiors):
        d, px, py = [], 0, 0
        for x, y in list(ring.coords)[:-1]:
            X, Y = round(x * 1e4), round(y * 1e4)
            if d and X == px and Y == py: continue
            d += [X - px, Y - py]; px, py = X, Y
        pe.append(d); n += len(d) // 2
    enc.append(pe)
json.dump(enc, open('land_enc.json', 'w'), separators=(',', ':'))
print(len(enc), 'polygons', n, 'points')
