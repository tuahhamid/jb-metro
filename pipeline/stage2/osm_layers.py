"""Read the OSM study clip into the layers Stage 2 needs.

One pass with pyosmium. Everything is returned in a projected CRS (UTM 48N, EPSG:32648)
so that lengths and areas are in meters. Data: (c) OpenStreetMap contributors, ODbL 1.0.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import osmium
import shapely
from pyproj import Transformer
from shapely import wkb

TO_UTM = Transformer.from_crs(4326, 32648, always_xy=True)
TO_WGS = Transformer.from_crs(32648, 4326, always_xy=True)

ROAD_CLASSES = {
    "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
    "secondary", "secondary_link", "tertiary", "tertiary_link",
}
NO_WALK = {"motorway", "motorway_link", "construction", "proposed", "raceway", "bus_guideway",
           "platform", "abandoned", "razed"}
DEPOT_LANDUSE = {"brownfield", "greenfield", "grass", "meadow", "farmland", "orchard",
                 "plantation", "village_green"}
DEPOT_NATURAL = {"scrub", "grassland", "heath"}
WATERWAYS = {"river", "stream", "canal", "drain", "ditch"}


@dataclass
class Layers:
    node_xy: dict = field(default_factory=dict)       # osm node id -> (x, y) for highway nodes
    ways: list = field(default_factory=list)          # dicts: id, nodes, tags (highway ways)
    buildings: list = field(default_factory=list)     # (polygon, levels or None, osm id)
    landuse: list = field(default_factory=list)       # (polygon, kind, name, osm id)
    water_lines: list = field(default_factory=list)   # (linestring, kind, name)
    rail_lines: list = field(default_factory=list)    # (linestring, tags)
    points: list = field(default_factory=list)        # (x, y, tags, osm id) for named/transport nodes
    named_areas: list = field(default_factory=list)   # (centroid x, y, tags, osm id) for named areas
    ped_nodes: list = field(default_factory=list)     # (x, y, tags, osm id) crossings/elevators/entrances
    coastline: list = field(default_factory=list)


def _xy(lon, lat):
    return TO_UTM.transform(lon, lat)


def _proj(geom):
    return shapely.transform(geom, lambda c: np.column_stack(TO_UTM.transform(c[:, 0], c[:, 1])))


class _Handler(osmium.SimpleHandler):
    def __init__(self, L: Layers):
        super().__init__()
        self.L = L
        self.wkb = osmium.geom.WKBFactory()

    def node(self, n):
        t = n.tags
        if not n.location.valid():
            return
        keys = ("highway", "railway", "public_transport", "entrance", "amenity", "shop", "place",
                "crossing", "elevator", "conveying")
        if not any(k in t for k in keys):
            return
        x, y = _xy(n.location.lon, n.location.lat)
        tags = dict(t)
        hw = tags.get("highway", "")
        if hw in ("crossing", "traffic_signals", "elevator") or "entrance" in tags or "crossing" in tags \
                or tags.get("railway") in ("subway_entrance", "train_station_entrance"):
            self.L.ped_nodes.append((x, y, tags, n.id))
        if "name" in tags or tags.get("railway") or tags.get("public_transport"):
            self.L.points.append((x, y, tags, n.id))

    def way(self, w):
        t = w.tags
        if "highway" in t:
            nodes = []
            for nd in w.nodes:
                if not nd.location.valid():
                    continue
                if nd.ref not in self.L.node_xy:
                    self.L.node_xy[nd.ref] = _xy(nd.location.lon, nd.location.lat)
                nodes.append(nd.ref)
            if len(nodes) >= 2:
                self.L.ways.append({"id": w.id, "nodes": nodes, "tags": dict(t)})
            return
        if t.get("waterway") in WATERWAYS or t.get("railway") in ("rail", "light_rail", "subway",
                                                                   "construction") \
                or t.get("natural") == "coastline":
            try:
                ls = _proj(wkb.loads(self.wkb.create_linestring(w), hex=True))
            except Exception:  # noqa: BLE001
                return
            if t.get("waterway") in WATERWAYS:
                self.L.water_lines.append((ls, t.get("waterway"), t.get("name", "")))
            elif t.get("natural") == "coastline":
                self.L.coastline.append(ls)
            else:
                self.L.rail_lines.append((ls, dict(t)))

    def area(self, a):
        t = a.tags
        is_bld = "building" in t and t.get("building") not in ("no", "roof")
        lu = t.get("landuse")
        nat = t.get("natural")
        named = "name" in t and any(k in t for k in ("shop", "amenity", "railway", "public_transport",
                                                      "place", "landuse", "leisure", "building",
                                                      "tourism", "office"))
        if not (is_bld or lu or nat in DEPOT_NATURAL or nat == "water" or named):
            return
        try:
            poly = _proj(wkb.loads(self.wkb.create_multipolygon(a), hex=True))
        except Exception:  # noqa: BLE001
            return
        oid = a.orig_id()
        if is_bld:
            lv = t.get("building:levels")
            try:
                lv = float(lv) if lv else None
            except ValueError:
                lv = None
            self.L.buildings.append((poly, lv, oid))
        if lu or nat in DEPOT_NATURAL or nat == "water":
            kind = lu if lu else f"natural={nat}"
            self.L.landuse.append((poly, kind, t.get("name", ""), oid))
        if named:
            c = poly.representative_point()
            self.L.named_areas.append((c.x, c.y, dict(t), oid))


def read_osm(path: str) -> Layers:
    L = Layers()
    h = _Handler(L)
    h.apply_file(path, locations=True, idx="flex_mem")
    return L
