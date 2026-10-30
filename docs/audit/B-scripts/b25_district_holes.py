from _common import *
import json, tempfile, os
def ring(x0, y0, x1, y1): return [[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]
# District 1 is a donut: outer square with a square hole. District 2 fills the hole.
donut = {"type":"Polygon","coordinates":[ring(-74.0,40.60,-73.90,40.80), ring(-73.97,40.68,-73.93,40.72)]}
plug  = {"type":"Polygon","coordinates":[ring(-73.97,40.68,-73.93,40.72)]}
gj = {"type":"FeatureCollection","features":[
  {"type":"Feature","properties":{"senate_district":1,"assembly_district":1,"council_district":1},"geometry":donut},
  {"type":"Feature","properties":{"senate_district":2,"assembly_district":2,"council_district":2},"geometry":plug}]}
p = os.path.join(tempfile.mkdtemp(prefix="distB_"), "d.geojson"); json.dump(gj, open(p, "w"))
feats, meta = engine.load_district_index(p)
print("point inside the hole (-73.95, 40.70), which belongs to district 2:", engine.assign_districts(40.70, -73.95, feats))
print("point in the donut body (-73.99, 40.62), district 1:", engine.assign_districts(40.62, -73.99, feats))
# real shipped file: any polygons with holes?
g = json.load(open("nyc_districts.geojson"))
print("shipped district file features:", len(g["features"]), "rings per polygon:", [len(f["geometry"]["coordinates"]) if f["geometry"]["type"]=="Polygon" else [len(p) for p in f["geometry"]["coordinates"]] for f in g["features"]])
