# 🚢 Arabian Gulf Fleet Monitor

**Real-time AIS vessel tracking + fleet analysis dashboard for the Arabian Gulf**

![License](https://img.shields.io/badge/license-MIT-blue)
![AIS](https://img.shields.io/badge/data-AISStream.io-00bcd4)

A two-mode fleet intelligence tool:
1. **Live AIS Stream** — captures all vessels currently west of the Strait of Hormuz in real-time
2. **Upload Enriched Data** — upload your CSV/Excel from Clarksons, Equasis, or any internal database with DWT, Owner, Year Built etc. for full fleet analysis

## Coverage Area

**Strictly west of the Strait of Hormuz** — the tool uses a bounding box plus a polygon filter to exclude the Gulf of Oman. This covers:
- UAE (Jebel Ali, Abu Dhabi, Das Island, Ruwais)
- Saudi Arabia (Ras Tanura, Jubail, Dammam)
- Qatar (Ras Laffan, Doha)
- Bahrain
- Kuwait
- Iraq (Umm Qasr, Basra)
- Iranian AG ports (Bandar Abbas western side, Bushehr, Kharg Island)

## Two-Mode Workflow

### Mode 1: Live AIS Stream → Export IMOs
1. Connect with your free [aisstream.io](https://aisstream.io) API key
2. Let it run for 5–10 minutes to capture vessel broadcasts
3. Click **"Export CSV"** to download the list with IMO numbers

### Mode 2: Enrich → Re-upload for Analysis
4. Take the exported IMO list and look them up in your internal database (Clarksons, Gibson, Equasis, etc.)
5. Export the enriched data (with DWT, Owner, Year Built, etc.) as CSV or Excel
6. Open the tool again, select **"Upload Enriched Data"**, drop in your file
7. The dashboard displays the full enriched fleet view with DWT, Owner, and all columns

## Data from AIS (Live Mode)

| Column | Available | Notes |
|--------|-----------|-------|
| IMO Number | ✅ | From AIS Message 5 |
| Vessel Name | ✅ | As broadcast |
| Type | ✅ | Mapped from AIS type code (Tanker, Cargo, etc.) |
| Length / Beam | ✅ | From AIS dimensions |
| Draught | ✅ | As reported |
| Flag | ✅ | Derived from MMSI country code |
| Nav Status | ✅ | At Anchor, Moored, Under Way, etc. |
| Speed (SOG) | ✅ | Knots |
| Destination | ✅ | As input by crew |
| **DWT** | ❌ | Not in AIS — needs external database |
| **Owner** | ❌ | Not in AIS — needs external database |

## Upload Mode — Smart Column Matching

The upload parser automatically detects columns by name. It looks for:
- `IMO`, `Name` / `Vessel Name`, `Type` / `Vessel Type`
- `DWT` / `Deadweight`, `Owner` / `Operator`
- `Flag` / `Country`, `Length` / `LOA`, `Beam` / `Breadth`
- `Draught` / `Draft`, `Destination`, `Year Built`
- `Speed` / `SOG`, `Status`

Column names are matched flexibly (case-insensitive, partial matching).

## Quick Start

1. Download `index.html`
2. Open in any browser (Chrome, Firefox, Edge)
3. No installation. No server. No build tools.

## Tech Stack

- Vanilla HTML/CSS/JS (zero dependencies except SheetJS for Excel parsing)
- [aisstream.io](https://aisstream.io) WebSocket API (free)
- [SheetJS](https://sheetjs.com/) for .xlsx/.xls parsing (loaded from CDN)

## Author

Built by **Sri** @ Gibson Shipbrokers, Singapore

## License

MIT
