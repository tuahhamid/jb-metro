"""Find freely licensed Commons photos for JB places. Prints candidates for review; writes mock/photos.json."""
import json, sys, re, urllib.parse, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "jb-metro-mockup/0.1 (research prototype)"}
API = "https://commons.wikimedia.org/w/api.php?"
OK = re.compile(r"^(CC BY(-SA)? [0-9.]+|CC0|Public domain|PD)", re.I)
PLACES = {
 "woodlands_rts": "RTS Link Johor Bahru Singapore viaduct", "jb_sentral": "JB Sentral station Johor Bahru",
 "bsi_ciq": "Bangunan Sultan Iskandar Johor Bahru", "abu_bakar": "Sultan Abu Bakar Mosque Johor Bahru",
 "dataran": "Dataran Bandaraya Johor Bahru clock tower", "danga_bay": "Danga Bay Johor Bahru", "legoland": "Legoland Malaysia",
 "bukit_indah": "Bukit Indah Johor", "ksl": "KSL City Mall Johor Bahru", "plaza_pelangi": "Plaza Pelangi Johor Bahru",
 "ikea_tebrau": "IKEA Tebrau", "aeon_tebrau": "AEON Tebrau City", "ulu_tiram": "Ulu Tiram",
 "city_square": "Johor Bahru City Square", "komtar": "Komtar JBCC", "southkey": "Mid Valley Southkey",
 "larkin": "Larkin Sentral", "paradigm": "Paradigm Mall Johor Bahru", "puteri_harbour": "Puteri Harbour",
 "sultan_iskandar_mosque": "Masjid Sultan Iskandar Johor Bahru", "causeway": "Johor-Singapore Causeway",
}
import time
def get(params):
    for attempt in range(6):
        time.sleep(3)
        try:
            with urllib.request.urlopen(urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(20 * (attempt + 1))
    raise RuntimeError("rate limited")
out = {}
for key, q in PLACES.items():
    s = get({"action": "query", "format": "json", "list": "search", "srsearch": q + " filetype:bitmap", "srnamespace": 6, "srlimit": 8})
    titles = [h["title"] for h in s["query"]["search"]]
    if not titles: print(f"{key}: none"); continue
    info = get({"action": "query", "format": "json", "titles": "|".join(titles), "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 640})
    pages = {p["title"]: p for p in info["query"]["pages"].values()}
    pick = None
    for t in titles:
        ii = pages.get(t, {}).get("imageinfo", [{}])[0]; m = ii.get("extmetadata", {})
        lic = m.get("LicenseShortName", {}).get("value", "")
        if ii.get("mime") != "image/jpeg" or not OK.match(lic) or ii.get("width", 0) < 800: continue
        artist = re.sub("<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip()
        pick = {"title": t, "thumb": ii["thumburl"], "page": ii["descriptionurl"], "license": lic, "license_url": m.get("LicenseUrl", {}).get("value", ""), "artist": artist[:80], "query": q}
        break
    out[key] = pick
    print(f"{key}: {pick['title'] if pick else 'NO FREE JPEG'} | {pick['license'] if pick else ''} | {pick['artist'] if pick else ''}")
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
