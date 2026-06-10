# Methodology

FraudMap UK+EU uses a lightweight public-source intelligence workflow designed for Google Colab.

## Collection

The dashboard collects public records from:

- public RSS feeds;
- Google News RSS queries;
- public consumer or cybersecurity information pages where accessible from Colab.

No API keys are required.

## Processing

The script parses each record for:

- title;
- source group;
- original publisher when available;
- publication date;
- summary text;
- URL.

Records are deduplicated using stable hashes derived from source, title and URL.

## Classification

Fraud and scam records are classified using transparent keyword rules. Categories include phishing, investment fraud, crypto fraud, banking fraud, courier scams, job scams, authority impersonation and broader general fraud.

For broad `General Fraud / Scam` records, the app adds:

- secondary theme;
- reason why the record stayed general;
- recommended verification sources;
- recommended next search query.

## Location extraction

The app extracts UK and EU location mentions from titles, summaries and source labels. Location mentions are treated as signals only. They are not proof that an incident occurred there.

## Scoring

Each record receives:

- risk score;
- risk band;
- confidence score;
- confidence band.

Scores are analytical indicators based on source type, terminology, loss amounts, vulnerability indicators and classification strength. They require manual review.

## Outputs

The app generates:

- charts;
- HTML dashboard;
- Markdown report;
- PDF report;
- CSV dataset;
- SQLite database;
- AI review prompt;
- ZIP export.
