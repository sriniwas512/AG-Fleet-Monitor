"""
Arabian Gulf Fleet Monitor — AIS Data Capture Script
Connects to aisstream.io WebSocket, captures all vessels west of the
Strait of Hormuz for a set duration, and saves results as CSV.

Optionally enriches data with Planet Insights satellite vessel detections.
Requires PLANET_API_KEY and PLANET_COLLECTION_ID to enable Planet data.

Designed to run via GitHub Actions or locally.
"""

import asyncio
import websockets
import json
import csv
import os
import sys
from datetime import datetime, timezone

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

# ============================================================
#  CONFIG
# ============================================================
API_KEY = os.environ.get("AISSTREAM_API_KEY", "")
CAPTURE_DURATION_SECONDS = int(os.environ.get("CAPTURE_DURATION", "300"))  # default 5 mins
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "ag_fleet_latest.csv")

# Planet Insights config (optional — skipped if not set)
PLANET_API_KEY = os.environ.get("PLANET_API_KEY", "")
PLANET_COLLECTION_ID = os.environ.get("PLANET_COLLECTION_ID", "")

# Arabian Gulf bounding box (rectangle that covers the AG)
AG_BBOX = [[23.5, 48.0], [30.5, 56.5]]

# ============================================================
#  AIS LOOKUP TABLES
# ============================================================
AIS_TYPE_MAP = {
    20: "WIG", 21: "WIG", 22: "WIG", 23: "WIG", 24: "WIG", 25: "WIG",
    30: "Fishing", 31: "Towing", 32: "Towing", 33: "Dredger", 34: "Diving Ops",
    35: "Military", 36: "Sailing", 37: "Pleasure Craft",
    40: "HSC", 41: "HSC", 42: "HSC", 43: "HSC", 44: "HSC", 45: "HSC",
    50: "Pilot", 51: "SAR", 52: "Tug", 53: "Port Tender", 54: "Anti-Pollution",
    55: "Law Enforce", 58: "Medical", 59: "Special",
    60: "Passenger", 61: "Passenger", 62: "Passenger", 63: "Passenger",
    64: "Passenger", 65: "Passenger", 66: "Passenger", 67: "Passenger",
    68: "Passenger", 69: "Passenger",
    70: "Cargo", 71: "Cargo (DG)", 72: "Cargo (DG)", 73: "Cargo (DG)",
    74: "Cargo (DG)", 75: "Cargo", 76: "Cargo", 77: "Cargo", 78: "Cargo", 79: "Cargo",
    80: "Tanker", 81: "Tanker (DG)", 82: "Tanker (DG)", 83: "Tanker (DG)",
    84: "Tanker (DG)", 85: "Tanker", 86: "Tanker", 87: "Tanker", 88: "Tanker", 89: "Tanker",
    90: "Other", 91: "Other", 92: "Other", 93: "Other", 94: "Other",
    95: "Other", 96: "Other", 97: "Other", 98: "Other", 99: "Other",
}

MID_TO_FLAG = {
    "201": "Albania", "205": "Belgium", "209": "Cyprus", "210": "Cyprus",
    "211": "Germany", "212": "Cyprus", "215": "Malta", "218": "Germany",
    "219": "Denmark", "220": "Denmark", "224": "Spain", "225": "Spain",
    "226": "France", "227": "France", "228": "France", "229": "Malta",
    "230": "Finland", "232": "UK", "233": "UK", "234": "UK", "235": "UK",
    "236": "Gibraltar", "237": "Greece", "238": "Croatia", "239": "Greece",
    "240": "Greece", "241": "Greece", "244": "Netherlands", "245": "Netherlands",
    "246": "Netherlands", "247": "Italy", "248": "Malta", "249": "Malta",
    "250": "Ireland", "255": "Madeira", "256": "Malta", "257": "Norway",
    "258": "Norway", "259": "Norway", "261": "Poland", "263": "Portugal",
    "265": "Sweden", "266": "Sweden", "271": "Turkey", "272": "Ukraine",
    "273": "Russia", "275": "Latvia", "276": "Estonia", "277": "Lithuania",
    "304": "Antigua", "305": "Antigua", "308": "Bahamas", "309": "Bahamas",
    "310": "Bermuda", "311": "Bahamas", "312": "Belize", "314": "Barbados",
    "316": "Canada", "319": "Cayman Is.", "338": "USA", "339": "USA",
    "341": "St Kitts", "345": "Mexico", "351": "Panama", "352": "Panama",
    "353": "Panama", "354": "Panama", "355": "Panama", "356": "Panama",
    "357": "Panama", "366": "USA", "367": "USA", "368": "USA", "369": "USA",
    "370": "Panama", "371": "Panama", "372": "Panama", "373": "Panama",
    "374": "Panama", "375": "St Vincent", "376": "St Vincent", "377": "St Vincent",
    "378": "BVI", "403": "Saudi Arabia", "405": "Bangladesh", "408": "Bahrain",
    "412": "China", "413": "China", "414": "China", "416": "Taiwan",
    "417": "Sri Lanka", "419": "India", "422": "Iran", "425": "Iraq",
    "428": "Israel", "431": "Japan", "432": "Japan", "436": "Kazakhstan",
    "438": "Jordan", "440": "South Korea", "441": "South Korea",
    "447": "Kuwait", "450": "Lebanon", "453": "Macao", "455": "Maldives",
    "461": "Oman", "463": "Pakistan", "466": "Qatar", "470": "UAE",
    "471": "UAE", "473": "Yemen", "475": "Thailand", "477": "Hong Kong",
    "503": "Australia", "508": "Brunei", "512": "New Zealand",
    "514": "Cambodia", "515": "Cambodia", "525": "Indonesia",
    "533": "Malaysia", "536": "Marshall Is.", "538": "Marshall Is.",
    "548": "Philippines", "563": "Singapore", "564": "Singapore",
    "565": "Singapore", "566": "Singapore", "574": "Vietnam",
    "576": "Vanuatu", "577": "Vanuatu",
    "601": "South Africa", "605": "Algeria", "621": "Djibouti",
    "622": "Egypt", "625": "Eritrea", "627": "Ghana", "634": "Kenya",
    "636": "Liberia", "637": "Liberia", "642": "Libya", "645": "Mauritius",
    "650": "Mozambique", "657": "Nigeria", "664": "Seychelles",
    "671": "Togo", "672": "Tunisia", "674": "Tanzania", "677": "Tanzania",
}

NAV_STATUS = {
    0: "Under Way (Engine)", 1: "At Anchor", 2: "Not Under Command",
    3: "Restricted Manoeuvrability", 4: "Constrained by Draught",
    5: "Moored", 6: "Aground", 7: "Fishing", 8: "Under Way (Sailing)",
    11: "Towing Astern", 12: "Pushing/Towing", 14: "AIS-SART", 15: "Not Defined",
}


def get_flag(mmsi):
    if not mmsi:
        return ""
    mid = str(mmsi)[:3]
    return MID_TO_FLAG.get(mid, "")


def get_type(code):
    if code is None:
        return ""
    return AIS_TYPE_MAP.get(code, f"Type {code}")


def get_nav(code):
    if code is None:
        return ""
    return NAV_STATUS.get(code, f"Status {code}")


def is_in_ag(lat, lon):
    """Filter out vessels east of Strait of Hormuz."""
    if lat is None or lon is None:
        return True
    if lat < 25.0:
        return lon <= 55.5
    if lat < 26.0:
        return lon <= 56.0
    if lat < 27.0:
        return lon <= 56.5
    return True


# ============================================================
#  PLANET INSIGHTS INTEGRATION
# ============================================================
async def fetch_planet_vessels():
    """
    Fetch satellite-detected vessels from Planet Insights Platform.

    Uses the Planet Analytics API to retrieve vessel detections within
    the Arabian Gulf bounding box. Vessels matched to AIS data by MMSI
    are flagged 'AIS+Satellite'; unmatched detections are flagged
    'Satellite' (potential dark/non-broadcasting vessels).

    Returns a dict keyed by MMSI (or 'PLN_<idx>' for unidentified vessels).
    Returns empty dict if Planet credentials are not configured.
    """
    if not PLANET_API_KEY or not PLANET_COLLECTION_ID:
        print("  [Planet] Skipping: PLANET_API_KEY or PLANET_COLLECTION_ID not set.")
        return {}

    if not HAS_AIOHTTP:
        print("  [Planet] Skipping: aiohttp not installed.")
        return {}

    print("  [Planet] Fetching satellite vessel detections from Planet Insights...")

    min_lat, min_lon = AG_BBOX[0]
    max_lat, max_lon = AG_BBOX[1]
    # WKT polygon covering the Arabian Gulf bounding box
    geometry = (
        f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},"
        f"{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
    )

    url = f"https://api.planet.com/analytics/collections/{PLANET_COLLECTION_ID}/items"
    headers = {"Authorization": f"api-key {PLANET_API_KEY}"}
    params = {"geometry": geometry, "limit": 1000}

    planet_vessels = {}
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 401:
                    print("  [Planet] Auth error: check PLANET_API_KEY.")
                    return {}
                if resp.status == 404:
                    print("  [Planet] Collection not found: check PLANET_COLLECTION_ID.")
                    return {}
                if resp.status != 200:
                    print(f"  [Planet] API error: HTTP {resp.status}")
                    return {}
                data = await resp.json()
    except Exception as e:
        print(f"  [Planet] Request failed: {e}")
        return {}

    features = data.get("features", [])
    print(f"  [Planet] Received {len(features)} satellite detections.")

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        lon_p = coords[0] if coords else None
        lat_p = coords[1] if coords else None

        if lat_p and lon_p and not is_in_ag(lat_p, lon_p):
            continue

        mmsi = str(props.get("mmsi", "")).strip().lstrip("0") or ""
        # Re-pad MMSI to 9 digits if it was stripped
        if mmsi and mmsi.isdigit():
            mmsi = mmsi.zfill(9)

        imo_raw = props.get("imo", 0)
        imo = int(imo_raw) if imo_raw and str(imo_raw).isdigit() else 0

        ts_raw = props.get("timestamp", "")
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                last_seen = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
            except ValueError:
                last_seen = ts_raw
        else:
            last_seen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        key = mmsi if mmsi else f"PLN_{idx}"

        v = {
            "mmsi": mmsi,
            "imo": imo if imo > 0 else "",
            "name": props.get("vessel_name", "").strip(),
            "lat": lat_p,
            "lon": lon_p,
            "length": props.get("length_m"),
            "beam": props.get("width_m"),
            "sog": props.get("speed_knots"),
            "flag": get_flag(mmsi) if mmsi else "",
            "source": "Satellite",
            "last_seen": last_seen,
        }

        planet_vessels[key] = v

    return planet_vessels


def merge_planet_into_ais(vessels, planet_vessels):
    """
    Merge Planet Insights detections into the AIS vessel dict.

    - AIS vessels matched by MMSI → source upgraded to 'AIS+Satellite';
      missing dimensions filled from satellite data if available.
    - Planet-only detections (no matching MMSI in AIS) → added as
      'Satellite' entries (potential dark/non-broadcasting vessels).

    Returns count of satellite-only (dark) vessel detections.
    """
    dark_count = 0

    for key, pv in planet_vessels.items():
        mmsi = pv.get("mmsi", "")
        if mmsi and mmsi in vessels:
            # Matched: enrich AIS record with satellite confirmation
            v = vessels[mmsi]
            v["source"] = "AIS+Satellite"
            if not v.get("length") and pv.get("length"):
                v["length"] = pv["length"]
            if not v.get("beam") and pv.get("beam"):
                v["beam"] = pv["beam"]
        else:
            # Unmatched: satellite-only detection (possible dark vessel)
            vessels[key] = pv
            dark_count += 1

    # Tag remaining AIS-only vessels
    for v in vessels.values():
        if "source" not in v:
            v["source"] = "AIS"

    return dark_count


# ============================================================
#  MAIN CAPTURE LOGIC
# ============================================================
async def capture():
    if not API_KEY:
        print("ERROR: No API key. Set AISSTREAM_API_KEY environment variable.")
        sys.exit(1)

    vessels = {}  # keyed by MMSI
    msg_count = 0
    start_time = datetime.now(timezone.utc)

    print(f"[{start_time.strftime('%H:%M:%S')}] Connecting to aisstream.io...")
    print(f"  Bounding box: {AG_BBOX}")
    print(f"  Capture duration: {CAPTURE_DURATION_SECONDS} seconds")
    print(f"  Output file: {OUTPUT_FILE}")
    if PLANET_API_KEY and PLANET_COLLECTION_ID:
        print(f"  Planet Insights: enabled (collection {PLANET_COLLECTION_ID})")
    else:
        print("  Planet Insights: disabled (set PLANET_API_KEY + PLANET_COLLECTION_ID to enable)")
    print()

    try:
        async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
            # Send subscription within 3 seconds
            subscribe_message = {
                "APIKey": API_KEY,
                "BoundingBoxes": [AG_BBOX],
                "FilterMessageTypes": [
                    "ShipStaticData",
                    "PositionReport",
                    "StandardClassBPositionReport",
                ],
            }
            await ws.send(json.dumps(subscribe_message))
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Subscribed! Streaming data...\n")

            while True:
                # Check if capture duration exceeded
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= CAPTURE_DURATION_SECONDS:
                    print(f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Capture duration reached ({CAPTURE_DURATION_SECONDS}s). Stopping.")
                    break

                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=10)
                except asyncio.TimeoutError:
                    continue

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                meta = data.get("MetaData")
                if not meta or not meta.get("MMSI"):
                    continue

                mmsi = str(meta["MMSI"])
                lat = meta.get("latitude")
                lon = meta.get("longitude")

                # Filter: only keep vessels inside the AG (west of Hormuz)
                if lat and lon and not is_in_ag(lat, lon):
                    continue

                msg_count += 1

                # Merge into existing vessel record
                v = vessels.get(mmsi, {"mmsi": mmsi})

                if meta.get("ShipName") and meta["ShipName"].strip():
                    v["name"] = meta["ShipName"].strip()
                if lat:
                    v["lat"] = lat
                if lon:
                    v["lon"] = lon

                msg_type = data.get("MessageType")

                if msg_type == "ShipStaticData":
                    sd = data.get("Message", {}).get("ShipStaticData", {})
                    if sd.get("ImoNumber") and sd["ImoNumber"] > 0:
                        v["imo"] = sd["ImoNumber"]
                    if sd.get("Type") is not None:
                        v["type_code"] = sd["Type"]
                        v["type"] = get_type(sd["Type"])
                    if sd.get("CallSign"):
                        v["callsign"] = sd["CallSign"].strip()
                    if sd.get("Destination"):
                        v["destination"] = sd["Destination"].strip()
                    if sd.get("MaximumStaticDraught"):
                        v["draught"] = sd["MaximumStaticDraught"]
                    dim = sd.get("Dimension", {})
                    if dim:
                        length = (dim.get("A") or 0) + (dim.get("B") or 0)
                        beam = (dim.get("C") or 0) + (dim.get("D") or 0)
                        if length > 0:
                            v["length"] = length
                        if beam > 0:
                            v["beam"] = beam

                if msg_type == "PositionReport":
                    pr = data.get("Message", {}).get("PositionReport", {})
                    if pr.get("Sog") is not None:
                        v["sog"] = pr["Sog"]
                    if pr.get("NavigationalStatus") is not None:
                        v["nav_status_code"] = pr["NavigationalStatus"]
                        v["nav_status"] = get_nav(pr["NavigationalStatus"])

                if msg_type == "StandardClassBPositionReport":
                    pr = data.get("Message", {}).get("StandardClassBPositionReport", {})
                    if pr.get("Sog") is not None:
                        v["sog"] = pr["Sog"]

                v["flag"] = get_flag(mmsi)
                v["last_seen"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

                vessels[mmsi] = v

                # Progress logging
                if msg_count % 100 == 0:
                    mins_left = max(0, (CAPTURE_DURATION_SECONDS - elapsed)) / 60
                    print(f"  {msg_count} messages | {len(vessels)} unique vessels | {mins_left:.1f} min remaining")

    except Exception as e:
        print(f"ERROR: {e}")
        if not vessels:
            sys.exit(1)

    # ============================================================
    #  PLANET INSIGHTS ENRICHMENT
    # ============================================================
    print(f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Fetching Planet Insights satellite data...")
    planet_vessels = await fetch_planet_vessels()
    dark_count = 0
    if planet_vessels:
        dark_count = merge_planet_into_ais(vessels, planet_vessels)
        confirmed = sum(1 for v in vessels.values() if v.get("source") == "AIS+Satellite")
        print(f"  [Planet] {confirmed} AIS vessels confirmed by satellite.")
        print(f"  [Planet] {dark_count} satellite-only detections (potential dark vessels).")
    else:
        # Tag all vessels as AIS-only when Planet data is unavailable
        for v in vessels.values():
            v.setdefault("source", "AIS")

    # ============================================================
    #  SAVE CSV
    # ============================================================
    print(f"\n{'='*60}")
    print(f"  CAPTURE COMPLETE")
    print(f"  Total AIS messages processed: {msg_count}")
    print(f"  Unique vessels captured: {len(vessels)}")
    if planet_vessels:
        print(f"  Dark ship detections (satellite only): {dark_count}")
    print(f"{'='*60}\n")

    headers = [
        "IMO", "MMSI", "Name", "Type_Code", "Type", "Length_m", "Beam_m",
        "Draught_m", "Flag", "Nav_Status", "SOG_kn", "Callsign",
        "Destination", "Latitude", "Longitude", "Last_Seen", "Source",
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for v in sorted(vessels.values(), key=lambda x: x.get("name", "")):
            writer.writerow([
                v.get("imo", ""),
                v.get("mmsi", ""),
                v.get("name", ""),
                v.get("type_code", ""),
                v.get("type", ""),
                v.get("length", ""),
                v.get("beam", ""),
                v.get("draught", ""),
                v.get("flag", ""),
                v.get("nav_status", ""),
                round(v["sog"], 1) if v.get("sog") is not None else "",
                v.get("callsign", ""),
                v.get("destination", ""),
                round(v["lat"], 6) if v.get("lat") else "",
                round(v["lon"], 6) if v.get("lon") else "",
                v.get("last_seen", ""),
                v.get("source", "AIS"),
            ])

    print(f"Saved to: {OUTPUT_FILE}")

    # Print summary by type
    type_counts = {}
    for v in vessels.values():
        t = v.get("type", "Unknown")
        if "Tanker" in t:
            t = "Tanker"
        elif "Cargo" in t:
            t = "Cargo"
        type_counts[t] = type_counts.get(t, 0) + 1

    print("\nVessel breakdown:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    if planet_vessels:
        print(f"\nData sources:")
        src_counts = {}
        for v in vessels.values():
            s = v.get("source", "AIS")
            src_counts[s] = src_counts.get(s, 0) + 1
        for s, count in sorted(src_counts.items()):
            print(f"  {s}: {count}")


if __name__ == "__main__":
    asyncio.run(capture())
