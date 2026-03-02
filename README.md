# 🚢 Arabian Gulf Fleet Monitor

**Automated AIS vessel tracking for the Arabian Gulf using GitHub Actions**

Captures all vessels west of the Strait of Hormuz via [aisstream.io](https://aisstream.io), saves as CSV, and provides a browser-based dashboard for analysis.

## How It Works

```
GitHub Actions (runs capture.py every 6 hours or on-demand)
        ↓
aisstream.io WebSocket → streams AIS data for 5 minutes
        ↓
Saves CSV to data/ag_fleet_latest.csv (auto-committed to repo)
        ↓
Open index.html → Upload the CSV → Full fleet dashboard
```

## Quick Start (One-Time Setup)

### Step 1: Add your API key as a GitHub Secret

1. Get a free API key from [aisstream.io](https://aisstream.io)
2. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `AISSTREAM_API_KEY`
5. Value: paste your API key
6. Click **Add secret**

### Step 2: Run the capture

1. Go to your repo → **Actions** tab
2. Click **"Capture AG Fleet Data"** on the left
3. Click **"Run workflow"** → **"Run workflow"**
4. Wait ~6 minutes — it captures data for 5 minutes then saves

### Step 3: Analyse the data

1. The CSV appears in `data/ag_fleet_latest.csv` in your repo
2. Download it, OR
3. Open `index.html` (via GitHub Pages or locally)
4. Select **"Upload Enriched Data"** mode → drop in the CSV → done

## Automatic Scheduling (Optional)

To run the capture automatically every 6 hours, edit `.github/workflows/capture.yml` and uncomment the schedule lines:

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
```

## What Data You Get

| Column | Source |
|--------|--------|
| IMO | AIS Message 5 |
| MMSI | AIS broadcast |
| Vessel Name | AIS broadcast |
| Type (Tanker/Cargo/etc.) | AIS type code, mapped to labels |
| Length / Beam | AIS dimensions |
| Draught | AIS broadcast |
| Flag | Derived from MMSI country code |
| Nav Status | At Anchor, Moored, Under Way, etc. |
| Speed (SOG) | Knots |
| Destination | As input by vessel crew |
| Lat / Lon | Last known position |

### To get DWT & Owner
Take the IMO numbers from the CSV → look up in Clarksons, Equasis, or your internal Gibson database → export enriched data → upload into the dashboard.

## Coverage

Strictly **west of the Strait of Hormuz**: UAE, Saudi, Qatar, Bahrain, Kuwait, Iraq, Iranian AG coast.

## Files

```
├── capture.py                        # AIS data capture script
├── index.html                        # Browser dashboard (upload CSV to analyse)
├── requirements.txt                  # Python dependencies
├── .github/workflows/capture.yml     # GitHub Actions workflow
├── data/
│   ├── ag_fleet_latest.csv           # Most recent capture
│   └── ag_fleet_YYYY-MM-DD_HHMM.csv # Timestamped archives
└── README.md
```

## Author

Built by **Sri** @ Gibson Shipbrokers, Singapore
