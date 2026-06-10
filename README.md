# FraudMap UK+EU

**FraudMap UK+EU** is a Google Colab-ready OSINT and data-analysis dashboard for monitoring public scam and fraud intelligence across UK and EU source layers.

It collects public RSS and Google News RSS items, classifies scam/fraud themes, scores risk and confidence, extracts UK/EU location mentions, and generates professional outputs: charts, HTML dashboard, PDF report, Markdown report, CSV, SQLite and ZIP export.

> Public sources only. No API keys. No hacked, leaked, private or personal datasets.

---

## Status

The repository is live and includes the main Google Colab script:

```text
fraudmap_ukeu.py
```

This app is designed specifically for **Google Colab**. It imports `google.colab.files` and uses IPython display functions for tables, charts and dashboard rendering. It may fail or crash on a normal Linux terminal/server because Colab-specific modules and `/content/...` paths may not exist outside Colab.

---

## Features

- UK, EU, UK+EU and specific scam/fraud focus modes.
- Public RSS and Google News RSS collection.
- Transparent keyword-based scam/fraud classification.
- Secondary themes for broad `General Fraud / Scam` records.
- UK and EU location/country mention extraction.
- Risk score, risk band, confidence score and confidence band.
- Prevention advice, reporting route and recommended next searches.
- Charts, dashboard, Markdown report, PDF report, CSV and SQLite exports.
- ZIP download only when the user confirms.

---

## Why this project exists

Fraud and scam reporting is fragmented across news, regulators, cybersecurity bodies, consumer-protection pages and public warnings.

FraudMap UK+EU demonstrates a practical intelligence-led workflow for:

- fraud-awareness monitoring;
- public-risk intelligence;
- trust and safety research;
- cyber-enabled fraud investigation;
- junior data-analysis portfolio evidence;
- OSINT reporting.

It is not an official reporting tool and does not replace police, regulator, bank or consumer-protection advice.

---

## Run in Google Colab

Recommended use:

1. Open Google Colab.
2. Create a new notebook.
3. Open `fraudmap_ukeu.py` from this repository.
4. Copy the full script into one Colab code cell.
5. Run the cell.
6. Select a scope:
   - UK overview
   - EU overview
   - UK + EU overview
   - specific scam/fraud focus
7. Review the automatic dashboard and charts.
8. Download the ZIP export only when prompted.

Do not treat this as a normal Linux CLI app. It is a Colab-first notebook script and may crash on Linux because of Colab-only imports, display handling and `/content/` export paths.

---

## Outputs

A normal run creates:

```text
exports/
├── charts/
│   ├── scope_distribution.png
│   ├── top_locations.png
│   ├── top_scams.png
│   ├── general_themes.png
│   ├── sources.png
│   ├── risk_distribution.png
│   ├── monthly_trend.png
│   └── risk_by_scam_category.png
├── data/
│   ├── fraudmap_ukeu_records.csv
│   └── fraudmap_ukeu.sqlite
└── reports/
    ├── fraudmap_ukeu_dashboard.html
    ├── fraudmap_ukeu_report.md
    ├── fraudmap_ukeu_report.pdf
    └── fraudmap_ai_review_prompt.md
```

The HTML dashboard embeds chart images as Base64 so it remains viewable after export.

---

## Classification examples

The classifier recognises categories such as:

- Police / Authority Impersonation
- Investment Fraud
- Crypto Fraud
- Banking / APP Fraud
- Delivery / Courier Scam
- Phishing / Smishing
- Job / Recruitment Scam
- HMRC / Tax Scam
- EU Consumer / Cross-border Scam
- Romance Fraud
- Marketplace Scam
- Ticket Scam
- AI / Deepfake Scam
- Identity Theft
- Loan Fee Fraud
- QR / Quishing
- General Fraud / Scam

For records that remain broad, the dashboard adds a secondary theme, explanation and recommended next search.

---

## Methodology

The project uses a lightweight public-source pipeline:

1. Query public RSS feeds and Google News RSS.
2. Parse titles, summaries, source labels and dates.
3. Filter for scam/fraud/cyber/consumer-risk signals.
4. Deduplicate records using stable hashes.
5. Classify scam/fraud categories using transparent keyword rules.
6. Extract UK/EU location mentions.
7. Score risk and data confidence.
8. Generate charts, reports and analyst-ready exports.

See [`docs/methodology.md`](docs/methodology.md).

---

## Ethics and limitations

This project uses only public information and does not target private individuals.

It does not use hacked, leaked, private or personal datasets. It does not perform intrusive scanning and does not automate reports to police, banks or regulators.

Locations are treated as mentions only, not verified incident locations. Manual validation is required before publication.

See:

- [`docs/ethics.md`](docs/ethics.md)
- [`docs/limitations.md`](docs/limitations.md)

---

## Portfolio line

> Built FraudMap UK+EU, a Colab-based OSINT and data-analysis dashboard that collects, classifies, scores and visualises public scam/fraud intelligence across UK and EU source layers, producing professional reports, charts, CSV, SQLite and dashboard exports.
