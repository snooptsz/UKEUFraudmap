# ============================================================
# FraudMap UK+EU v1.0 — Google Colab Script
# Public sources only | Google News RSS | No API keys | Download only on request
# ============================================================

import sys
import subprocess
import importlib.util
import os
import re
import sqlite3
import hashlib
import time
import shutil
import zipfile
import base64
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse
from xml.sax.saxutils import escape as xml_escape

REQUIRED = [
    "requests",
    "beautifulsoup4",
    "feedparser",
    "pandas",
    "matplotlib",
    "lxml",
    "reportlab",
    "python-dateutil",
    "tabulate",
]


def install_if_missing(package_name):
    module_name = package_name.replace("-", "_")
    if package_name == "beautifulsoup4":
        module_name = "bs4"
    if package_name == "python-dateutil":
        module_name = "dateutil"
    if importlib.util.find_spec(module_name) is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package_name])


for package in REQUIRED:
    install_if_missing(package)

import requests
import feedparser
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, Table, TableStyle
from reportlab.lib import colors

try:
    from google.colab import files
    from IPython.display import display, HTML, Image
except Exception:
    raise RuntimeError("This script is designed for Google Colab only.")

APP_NAME = "FraudMap UK+EU"
VERSION = "1.0"
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

BASE_DIR = f"/content/fraudmap_ukeu_{RUN_ID}"
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
CHART_DIR = os.path.join(EXPORT_DIR, "charts")
REPORT_DIR = os.path.join(EXPORT_DIR, "reports")
DATA_DIR = os.path.join(EXPORT_DIR, "data")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

for folder in [EXPORT_DIR, CHART_DIR, REPORT_DIR, DATA_DIR, TEMP_DIR]:
    os.makedirs(folder, exist_ok=True)

HEADERS = {"User-Agent": "FraudMapUK-EU/1.0 public-interest OSINT fraud-awareness dashboard"}
REQUEST_TIMEOUT = 15
SLEEP_SECONDS = 0.25

print("=" * 100)
print(f"{APP_NAME} v{VERSION}")
print("Colab-only | Public sources only | Google News RSS | No API keys | Download only on request")
print("=" * 100)

print("\nChoose intelligence scope:")
print("1 = UK overview")
print("2 = EU overview")
print("3 = UK + EU overview")
print("4 = Specific scam/fraud focus")
scope_choice = input("Select scope [1/2/3/4]: ").strip() or "3"

if scope_choice == "1":
    SCOPE = "UK"
    focus_query = "UK scam fraud"
elif scope_choice == "2":
    SCOPE = "EU"
    focus_query = "EU scam fraud"
elif scope_choice == "4":
    region_input = input("Focus region: UK / EU / UK+EU [default UK+EU]: ").strip().upper() or "UK+EU"
    SCOPE = region_input if region_input in ["UK", "EU", "UK+EU"] else "UK+EU"
    focus_query = input("Enter focus, e.g. job scam, crypto fraud, delivery scam, HMRC scam: ").strip() or "scam fraud"
else:
    SCOPE = "UK+EU"
    focus_query = "UK EU scam fraud"

print("\nRun depth:")
print("1 = Balanced")
print("2 = Detailed portfolio scan")
depth = input("Select run depth [1/2]: ").strip() or "1"
DETAILED = depth == "2"
MAX_ITEMS_PER_FEED = 40 if DETAILED else 25

print("\nReady. Results, charts and dashboard will display automatically. Download starts only if confirmed.")

UK_TERMS = [
    "UK scam warning",
    "UK fraud warning",
    "UK phishing scam",
    "UK banking fraud",
    "UK authorised push payment fraud",
    "UK investment fraud",
    "UK courier delivery scam",
    "UK romance fraud",
    "UK job scam",
    "UK recruitment scam",
    "UK marketplace scam",
    "UK crypto scam",
    "UK AI scam",
    "UK WhatsApp scam",
    "UK text message scam",
    "UK HMRC scam",
    "UK pension scam",
    "UK QR code scam",
    "UK fake police scam",
    "UK clone firm scam",
]

EU_TERMS = [
    "EU scam warning",
    "Europe fraud warning",
    "European online fraud warning",
    "Europol online fraud",
    "Europol cybercrime fraud",
    "EU phishing warning",
    "ENISA phishing",
    "ENISA cyber fraud",
    "CERT-EU phishing",
    "CERT-EU security advisory phishing",
    "OLAF scam alert",
    "European Commission consumer scam",
    "EU investment scam",
    "Europe crypto scam",
    "Europe romance scam",
    "Europe job scam",
    "Europe marketplace scam",
    "EU fake bank scam",
    "EU deepfake scam",
    "EU AI scam",
]

if scope_choice == "4":
    if SCOPE == "UK":
        SEARCH_TERMS = [
            f"{focus_query} UK",
            f"{focus_query} warning UK",
            f"{focus_query} scam alert UK",
            f"{focus_query} fraud warning UK",
            f"{focus_query} victims UK",
            f"{focus_query} prevention UK",
            f"{focus_query} police warning UK",
        ]
    elif SCOPE == "EU":
        SEARCH_TERMS = [
            f"{focus_query} EU",
            f"{focus_query} Europe",
            f"{focus_query} Europol",
            f"{focus_query} ENISA",
            f"{focus_query} CERT-EU",
            f"{focus_query} European Commission",
        ]
    else:
        SEARCH_TERMS = [
            f"{focus_query} UK",
            f"{focus_query} EU",
            f"{focus_query} Europe",
            f"{focus_query} warning",
            f"{focus_query} fraud victims",
            f"{focus_query} prevention",
        ]
elif SCOPE == "UK":
    SEARCH_TERMS = UK_TERMS
elif SCOPE == "EU":
    SEARCH_TERMS = EU_TERMS
else:
    SEARCH_TERMS = UK_TERMS + EU_TERMS


def google_news_rss(query):
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-GB&gl=GB&ceid=GB:en"


RSS_FEEDS = {}

if SCOPE in ["UK", "UK+EU"]:
    RSS_FEEDS.update(
        {
            "FCA Warnings": "https://www.fca.org.uk/news/rss.xml?category=warnings",
            "BBC UK": "https://feeds.bbci.co.uk/news/uk/rss.xml",
            "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
            "Guardian Money": "https://www.theguardian.com/uk/money/rss",
        }
    )

if SCOPE in ["EU", "UK+EU"]:
    RSS_FEEDS.update(
        {
            "ENISA News": "https://www.enisa.europa.eu/news/enisa-news/RSS",
            "CERT-EU Advisories": "https://cert.europa.eu/publications/security-advisories-rss",
        }
    )

for term in SEARCH_TERMS:
    RSS_FEEDS[f"Google News: {term}"] = google_news_rss(term)

OPTIONAL_PUBLIC_PAGES = {}

if SCOPE in ["UK", "UK+EU"]:
    OPTIONAL_PUBLIC_PAGES["Which? Scams"] = "https://www.which.co.uk/consumer-rights/scams"

if SCOPE in ["EU", "UK+EU"]:
    OPTIONAL_PUBLIC_PAGES.update(
        {
            "European Commission Consumer Rights": "https://commission.europa.eu/live-work-travel-eu/consumer-rights-and-complaints_en",
            "OLAF Fraud Reporting": "https://anti-fraud.ec.europa.eu/olaf-and-you/report-fraud_en",
            "ENISA News": "https://www.enisa.europa.eu/news",
            "Europol Cybercrime": "https://www.europol.europa.eu/crime-areas-and-statistics/crime-areas/cybercrime",
        }
    )

UK_LOCATION_ALIASES = {
    "Co Antrim": "Antrim",
    "County Antrim": "Antrim",
    "Co Down": "Down",
    "County Down": "Down",
    "Co Derry": "Derry",
    "County Derry": "Derry",
    "Letchworth": "Hertfordshire",
    "Petersfield": "Hampshire",
    "Penarth": "Wales",
    "Bishop's Stortford": "Hertfordshire",
    "Greater Manchester": "Greater Manchester",
    "West Midlands": "West Midlands",
    "West Yorkshire": "West Yorkshire",
    "South Yorkshire": "South Yorkshire",
    "Northern Ireland": "Northern Ireland",
    "Isle of Man": "Isle of Man",
    "Channel Islands": "Channel Islands",
}

UK_LOCATIONS = [
    "London", "Birmingham", "Manchester", "Leeds", "Liverpool", "Bristol", "Sheffield",
    "Nottingham", "Leicester", "Coventry", "Bradford", "Cardiff", "Belfast", "Edinburgh",
    "Glasgow", "Newcastle", "Southampton", "Portsmouth", "Brighton", "Plymouth", "Derby",
    "Swansea", "Oxford", "Cambridge", "York", "Norwich", "Exeter", "Bath", "Reading",
    "Milton Keynes", "Luton", "Wolverhampton", "Hull", "Preston", "Middlesbrough",
    "Aberdeen", "Dundee", "Sunderland", "Stoke", "Warrington", "Slough", "Croydon",
    "Suffolk", "Norfolk", "Essex", "Kent", "Surrey", "Hampshire", "Lancashire",
    "Merseyside", "Devon", "Cornwall", "Dorset", "Sussex", "Wiltshire", "Cambridgeshire",
    "Hertfordshire", "Bedfordshire", "Buckinghamshire", "Berkshire", "Oxfordshire",
    "Warwickshire", "Staffordshire", "Derbyshire", "Nottinghamshire", "Lincolnshire",
    "Yorkshire", "Cumbria", "Northumberland", "Durham", "Antrim", "Derry", "Down",
    "Scotland", "Wales", "Northern Ireland", "England", "Jersey", "Guernsey", "Isle of Man",
]

EU_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Czechia",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Ireland",
    "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands", "Poland",
    "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
    "Norway", "Switzerland", "Iceland", "Liechtenstein",
]

EU_CITY_ALIASES = {
    "Paris": "France",
    "Berlin": "Germany",
    "Madrid": "Spain",
    "Rome": "Italy",
    "Milan": "Italy",
    "Amsterdam": "Netherlands",
    "Brussels": "Belgium",
    "Vienna": "Austria",
    "Warsaw": "Poland",
    "Lisbon": "Portugal",
    "Dublin": "Ireland",
    "Stockholm": "Sweden",
    "Copenhagen": "Denmark",
    "Helsinki": "Finland",
    "Prague": "Czechia",
    "Athens": "Greece",
    "Budapest": "Hungary",
    "Tallinn": "Estonia",
    "Riga": "Latvia",
    "Vilnius": "Lithuania",
    "Bucharest": "Romania",
    "Sofia": "Bulgaria",
    "Zagreb": "Croatia",
    "Ljubljana": "Slovenia",
    "Bratislava": "Slovakia",
}

SCAM_KEYWORDS = {
    "Police / Authority Impersonation": [
        "fake police", "bogus police", "police officer", "spoofed number",
        "impersonating police", "posing as police", "claimed to be police",
        "authority impersonation", "public authority scam",
    ],
    "Investment Fraud": [
        "investment", "clone firm", "unauthorised firm", "forex", "pension",
        "shares", "savings", "trading scam", "investment scam", "ponzi", "boiler room",
    ],
    "Crypto Fraud": ["crypto", "bitcoin", "wallet", "exchange", "token", "pig butchering", "cryptocurrency", "blockchain scam"],
    "Banking / APP Fraud": [
        "bank", "banking", "authorised push payment", "app fraud", "payment fraud",
        "bank transfer", "sort code", "bank account", "iban", "sepa transfer",
    ],
    "Delivery / Courier Scam": ["delivery", "courier", "parcel", "royal mail", "evri", "dpd", "post office", "missed delivery", "courier fraud"],
    "Phishing / Smishing": ["phishing", "smishing", "fake email", "fake text", "sms scam", "malicious link", "text message scam", "email scam", "suspicious link"],
    "Job / Recruitment Scam": ["job scam", "recruitment scam", "remote job", "work from home", "fake recruiter", "job offer", "employment scam", "task scam"],
    "HMRC / Tax Scam": ["hmrc", "tax refund", "tax scam", "self assessment", "tax rebate"],
    "EU Consumer / Cross-border Scam": ["consumer scam", "cross-border scam", "consumer protection", "online shopping scam", "unfair commercial practices", "consumer rights"],
    "Romance Fraud": ["romance", "dating", "relationship scam", "love scam"],
    "Marketplace Scam": ["marketplace", "facebook marketplace", "gumtree", "ebay", "vinted", "depop", "online seller", "seller scam"],
    "Ticket Scam": ["ticket scam", "concert ticket", "festival ticket", "football ticket", "event ticket"],
    "AI / Deepfake Scam": ["ai scam", "deepfake", "voice clone", "fake ai advert", "artificial intelligence", "synthetic voice"],
    "Identity Theft": ["identity theft", "fake profile", "stolen identity", "identity fraud"],
    "Loan Fee Fraud": ["loan fee", "advance fee", "upfront fee", "credit broker"],
    "QR / Quishing": ["qr code", "quishing", "fake qr"],
}

GENERAL_THEMES = {
    "Online consumer scam": ["consumer", "shopping", "purchase", "online shop", "retailer", "goods", "seller"],
    "Platform / social media scam": ["facebook", "instagram", "tiktok", "whatsapp", "telegram", "social media", "platform"],
    "Financial / investment suspicion": ["investment", "bank", "payment", "transfer", "crypto", "savings", "pension"],
    "Cyber-enabled fraud": ["phishing", "malware", "cyber", "email", "sms", "credential", "account"],
    "Public authority impersonation": ["police", "hmrc", "tax", "government", "authority", "europol", "commission"],
    "Marketplace / e-commerce risk": ["marketplace", "ebay", "vinted", "depop", "gumtree", "seller"],
    "Unknown general fraud": [],
}

HIGH_RISK_TERMS = [
    "lost", "loss", "stolen", "victim", "victims", "elderly", "pensioner", "bank details",
    "life savings", "£", "€", "thousands", "million", "crypto", "investment", "identity",
    "clone firm", "unauthorised", "urgent warning", "warning", "police warning",
    "fraudsters", "criminals", "scammers", "fake", "impersonating", "targeting",
    "bank transfer", "high value", "savings", "vulnerable", "confiscation", "charged",
]

SOURCE_WEIGHT = {
    "FCA": 15,
    "Action Fraud": 15,
    "Police": 12,
    "BBC": 8,
    "Guardian": 7,
    "Which": 7,
    "ENISA": 12,
    "CERT-EU": 12,
    "Europol": 12,
    "OLAF": 12,
    "European Commission": 10,
    "Google News": 4,
}

CATEGORY_SOURCES = {
    "Investment Fraud": ["FCA Warning List", "National financial regulator", "European Securities and Markets Authority", "Police / fraud reporting service"],
    "Crypto Fraud": ["FCA cryptoasset warnings", "Europol cybercrime resources", "National cyber security centre", "Police / fraud reporting service"],
    "Phishing / Smishing": ["National cyber security centre", "CERT-EU advisories", "ENISA awareness resources", "Report suspicious emails/texts through official channels"],
    "Banking / APP Fraud": ["Your bank official fraud team", "National fraud reporting service", "Consumer protection authority", "Police"],
    "Delivery / Courier Scam": ["Courier official website", "Consumer protection authority", "National fraud reporting service"],
    "Job / Recruitment Scam": ["Company official website", "LinkedIn company verification", "Employment rights authority", "Fraud reporting service"],
    "EU Consumer / Cross-border Scam": ["European Commission consumer rights", "European Consumer Centres Network", "National consumer protection authority"],
    "General Fraud / Scam": ["National fraud reporting service", "Consumer protection authority", "Police cyber/fraud unit", "Official company/regulator website"],
}


def clean_text(text):
    if not text:
        return ""
    text = BeautifulSoup(str(text), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def stable_id(*parts):
    raw = "||".join(str(p or "") for p in parts).lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:18]


def safe_get(url):
    try:
        time.sleep(SLEEP_SECONDS)
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code >= 400:
            return None
        return response
    except Exception:
        return None


def extract_date(entry):
    if entry.get("published_parsed"):
        try:
            return datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
        except Exception:
            pass
    for key in ["published", "updated", "created"]:
        if entry.get(key):
            raw = clean_text(entry.get(key))
            try:
                return date_parser.parse(raw).strftime("%Y-%m-%d")
            except Exception:
                return raw
    return ""


def infer_geo_scope(text):
    text_l = f" {text.lower()} "
    uk_hit = any(loc.lower() in text_l for loc in UK_LOCATIONS) or " uk " in text_l or "united kingdom" in text_l or "britain" in text_l or "british" in text_l
    eu_hit = any(country.lower() in text_l for country in EU_COUNTRIES) or "europe" in text_l or " eu " in text_l or "europol" in text_l or "enisa" in text_l or "cert-eu" in text_l or "european commission" in text_l or "olaf" in text_l
    if uk_hit and eu_hit:
        return "UK+EU"
    if uk_hit:
        return "UK"
    if eu_hit:
        return "EU"
    return "Unknown"


def infer_location(text):
    text_l = text.lower()
    found = []
    for alias, canonical in UK_LOCATION_ALIASES.items():
        if alias.lower() in text_l:
            found.append(canonical)
    for loc in UK_LOCATIONS:
        if re.search(rf"\b{re.escape(loc.lower())}\b", text_l):
            found.append(loc)
    for city, country in EU_CITY_ALIASES.items():
        if re.search(rf"\b{re.escape(city.lower())}\b", text_l):
            found.append(country)
    for country in EU_COUNTRIES:
        if re.search(rf"\b{re.escape(country.lower())}\b", text_l):
            found.append(country)
    found = sorted(set(found))
    return ", ".join(found) if found else "Unknown"


def infer_scam_type(text):
    text_l = text.lower()
    priority_rules = [
        ("Police / Authority Impersonation", ["fake police", "bogus police", "impersonating police", "claimed to be police", "police officer scam"]),
        ("Delivery / Courier Scam", ["courier fraud", "parcel scam", "missed delivery", "royal mail", "evri", "dpd"]),
        ("Investment Fraud", ["clone firm", "unauthorised firm", "investment scam", "ponzi", "boiler room"]),
        ("Crypto Fraud", ["crypto", "bitcoin", "pig butchering", "cryptocurrency"]),
        ("HMRC / Tax Scam", ["hmrc", "tax refund", "tax rebate", "self assessment"]),
        ("Job / Recruitment Scam", ["job scam", "recruitment scam", "fake recruiter", "task scam"]),
        ("EU Consumer / Cross-border Scam", ["consumer protection", "cross-border scam", "consumer rights", "online shopping scam"]),
    ]
    for category, terms in priority_rules:
        if any(term in text_l for term in terms):
            return category
    scores = {category: sum(1 for keyword in keywords if keyword.lower() in text_l) for category, keywords in SCAM_KEYWORDS.items()}
    scores = {category: score for category, score in scores.items() if score > 0}
    if scores:
        return max(scores, key=scores.get)
    if "fraud" in text_l or "scam" in text_l:
        return "General Fraud / Scam"
    return "Unclassified"


def infer_general_theme(text, scam_type):
    if scam_type != "General Fraud / Scam":
        return ""
    text_l = text.lower()
    for theme, terms in GENERAL_THEMES.items():
        if terms and any(term in text_l for term in terms):
            return theme
    return "Unknown general fraud"


def explain_general_classification(text, scam_type, theme):
    if scam_type != "General Fraud / Scam":
        return ""
    if theme == "Unknown general fraud":
        return "The item contains fraud/scam indicators but lacks enough specific wording to classify it into a narrower fraud type."
    return f"The item contains fraud/scam indicators and appears related to {theme.lower()}, but does not provide enough specific wording for a narrower category."


def extract_loss(text):
    raw = re.findall(r"[£€]\s?[\d,]+(?:\.\d+)?\s?(?:m|million|bn|billion|k)?", text, re.I)
    cleaned = []
    seen = set()
    for item in raw:
        item = re.sub(r"\s+", " ", item.strip()).replace("£ ", "£").replace("€ ", "€")
        key = item.lower().replace(" ", "")
        if key not in seen:
            seen.add(key)
            cleaned.append(item)
    return ", ".join(cleaned[:4]) if cleaned else ""


def numeric_loss_score(text):
    score = 0
    amounts = re.findall(r"[£€]\s?([\d,]+)(?:\.\d+)?\s?(m|million|bn|billion|k)?", text.lower(), re.I)
    seen = set()
    for amount, suffix in amounts:
        key = f"{amount}{suffix}".lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            value = float(amount.replace(",", ""))
            suffix = suffix.lower()
            if suffix == "k":
                value *= 1_000
            elif suffix in ["m", "million"]:
                value *= 1_000_000
            elif suffix in ["bn", "billion"]:
                value *= 1_000_000_000
            if value >= 1_000_000:
                score += 22
            elif value >= 100_000:
                score += 18
            elif value >= 10_000:
                score += 12
            elif value >= 1_000:
                score += 7
        except Exception:
            pass
    return min(score, 25)


def source_score(source, original_source=""):
    text_l = f"{source} {original_source}".lower()
    score = 0
    for key, value in SOURCE_WEIGHT.items():
        if key.lower() in text_l:
            score += value
    return min(score, 20)


def risk_score(text, source, scam_type, original_source=""):
    text_l = text.lower()
    score = 18
    score += min(38, sum(4 for term in HIGH_RISK_TERMS if term.lower() in text_l))
    score += numeric_loss_score(text)
    score += source_score(source, original_source)
    if scam_type in ["Investment Fraud", "Crypto Fraud", "Banking / APP Fraud", "Police / Authority Impersonation"]:
        score += 12
    elif scam_type in ["Phishing / Smishing", "Delivery / Courier Scam", "Job / Recruitment Scam", "HMRC / Tax Scam", "EU Consumer / Cross-border Scam"]:
        score += 8
    elif scam_type == "General Fraud / Scam":
        score += 1
    if any(term in text_l for term in ["elderly", "pensioner", "life savings", "vulnerable"]):
        score += 10
    if any(term in text_l for term in ["urgent warning", "police warning", "residents warned", "customers warned"]):
        score += 7
    return max(1, min(100, score))


def risk_band(score):
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 28:
        return "Medium"
    return "Low"


def confidence_score(row):
    score = 35
    if row.get("date"):
        score += 10
    if row.get("original_source"):
        score += 10
    if row.get("location") != "Unknown":
        score += 10
    if row.get("scam_type") not in ["Unclassified", "General Fraud / Scam"]:
        score += 15
    if row.get("loss_amount"):
        score += 10
    if "Google News" not in row.get("source", ""):
        score += 10
    return max(1, min(100, score))


def confidence_band(score):
    if score >= 75:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def prevention_advice(scam_type):
    tips = {
        "Phishing / Smishing": "Do not click unknown links. Verify sender domains and access services directly.",
        "Investment Fraud": "Check the relevant financial regulator, avoid pressure tactics and reject guaranteed-return claims.",
        "Crypto Fraud": "Do not trust unsolicited crypto offers. Never share wallet seed phrases.",
        "Banking / APP Fraud": "Pause before transferring money. Verify payment requests through official channels.",
        "Delivery / Courier Scam": "Do not pay through unexpected delivery links. Use the courier official site/app.",
        "Romance Fraud": "Be cautious of money requests, secrecy or urgent help. Speak to someone trusted.",
        "Job / Recruitment Scam": "Verify recruiters and company domains. Never pay fees to get a job.",
        "Marketplace Scam": "Use platform payment protection and avoid direct bank transfers.",
        "Ticket Scam": "Use official sellers or protected resale platforms.",
        "AI / Deepfake Scam": "Verify unusual requests through a second trusted channel.",
        "Identity Theft": "Use MFA, limit public personal data and monitor accounts.",
        "Loan Fee Fraud": "Do not pay upfront fees for guaranteed loans.",
        "QR / Quishing": "Avoid random QR stickers. Use official apps or type known URLs manually.",
        "HMRC / Tax Scam": "Use gov.uk directly. Do not trust urgent tax-refund links.",
        "Police / Authority Impersonation": "Do not share financial details with unexpected callers. Hang up and verify through official numbers.",
        "EU Consumer / Cross-border Scam": "Use official consumer protection channels and verify sellers before paying.",
    }
    return tips.get(scam_type, "Verify the source, avoid pressure tactics and report suspected fraud officially.")


def report_route(geo_scope):
    if geo_scope == "EU":
        return "Contact your bank immediately if money is involved. Preserve evidence. Use national police/fraud reporting routes, national consumer protection authorities, and the European Consumer Centres Network for cross-border consumer issues."
    if geo_scope == "UK":
        return "Contact your bank immediately if money is involved. Preserve evidence. Report fraud through official UK routes. Forward suspicious texts to 7726 and suspicious emails to report@phishing.gov.uk where applicable."
    return "Contact your bank immediately if money is involved. Preserve evidence. Use the relevant national fraud, police, cybercrime or consumer protection reporting route."


def recommended_sources(row):
    category = row.get("scam_type", "General Fraud / Scam")
    sources = CATEGORY_SOURCES.get(category, CATEGORY_SOURCES["General Fraud / Scam"])
    if row.get("geo_scope") == "EU":
        sources = sources + ["European Commission consumer rights", "Europol", "ENISA", "CERT-EU"]
    elif row.get("geo_scope") == "UK":
        sources = sources + ["FCA", "Action Fraud", "NCSC", "Which? scam alerts"]
    return "; ".join(sorted(set(sources)))


def recommended_next_search(row):
    base = row.get("detail_theme") or row.get("scam_type") or "scam fraud"
    location = row.get("location", "")
    if location and location != "Unknown":
        return f"{base} {location} warning fraud prevention"
    if row.get("geo_scope") == "EU":
        return f"{base} Europe EU warning fraud prevention"
    if row.get("geo_scope") == "UK":
        return f"{base} UK warning fraud prevention"
    return f"{base} scam fraud warning prevention"


def local_intelligence_note(row):
    target = "general public"
    text_l = f"{row.get('title','')} {row.get('summary','')} {row.get('text_sample','')}".lower()
    if any(term in text_l for term in ["elderly", "pensioner"]):
        target = "older or vulnerable residents"
    elif any(term in text_l for term in ["bank", "payment", "transfer", "iban", "sepa"]):
        target = "banking customers"
    elif any(term in text_l for term in ["investment", "crypto", "pension", "savings"]):
        target = "investors and savers"
    elif any(term in text_l for term in ["job", "recruitment", "remote"]):
        target = "job seekers"
    elif any(term in text_l for term in ["parcel", "delivery", "courier"]):
        target = "online shoppers"
    elif any(term in text_l for term in ["consumer", "shopping", "seller"]):
        target = "online consumers"
    return f"Classified as {row.get('scam_type')} with {row.get('risk_band')} risk and {row.get('confidence_band')} data confidence. Likely target group: {target}. Primary prevention: {row.get('prevention')}"


def normalise_record(source, title, url, summary="", date="", raw="", original_source=""):
    classification_text = clean_text(f"{title} {summary} {raw} {original_source}")
    location_text = clean_text(f"{title} {summary} {original_source}")
    scam_type = infer_scam_type(classification_text)
    geo_scope = infer_geo_scope(classification_text)
    location = infer_location(location_text)
    detail_theme = infer_general_theme(classification_text, scam_type)
    score = risk_score(classification_text, source, scam_type, original_source)
    row = {
        "id": stable_id(original_source, title, url),
        "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "date": date,
        "source": source,
        "original_source": original_source,
        "geo_scope": geo_scope,
        "title": clean_text(title)[:350],
        "url": url,
        "summary": clean_text(summary)[:1200],
        "location": location,
        "scam_type": scam_type,
        "detail_theme": detail_theme,
        "why_general": explain_general_classification(classification_text, scam_type, detail_theme),
        "loss_amount": extract_loss(classification_text),
        "risk_score": score,
        "risk_band": risk_band(score),
        "prevention": prevention_advice(scam_type),
        "reporting": report_route(geo_scope),
        "text_sample": classification_text[:1800],
    }
    row["confidence_score"] = confidence_score(row)
    row["confidence_band"] = confidence_band(row["confidence_score"])
    row["recommended_sources"] = recommended_sources(row)
    row["recommended_next_search"] = recommended_next_search(row)
    row["intelligence_note"] = local_intelligence_note(row)
    return row


def collect_rss():
    print("\n[1/2] Collecting public RSS and Google News RSS...")
    records = []
    for source, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.entries[:MAX_ITEMS_PER_FEED]
            print(f" - {source}: {len(entries)} items")
            for entry in entries:
                title = clean_text(entry.get("title", ""))
                url = entry.get("link", "")
                summary = clean_text(entry.get("summary", entry.get("description", "")))
                date = extract_date(entry)
                original_source = ""
                try:
                    if hasattr(entry, "source") and entry.source:
                        original_source = clean_text(entry.source.get("title", ""))
                except Exception:
                    pass
                combined = f"{title} {summary} {original_source} {focus_query}"
                if any(keyword in combined.lower() for keyword in ["fraud", "scam", "phishing", "warning", "cyber", "crime", "unauthorised", "investment", "victim", "lost", "bank", "crypto", "hmrc", "police", "consumer", "europol", "enisa", "cert-eu", "olaf"]):
                    records.append(normalise_record(source, title, url, summary, date, combined, original_source))
        except Exception:
            pass
    return records


def collect_optional_pages():
    print("\n[2/2] Checking public advice pages...")
    records = []
    for source, url in OPTIONAL_PUBLIC_PAGES.items():
        response = safe_get(url)
        if not response:
            continue
        soup = BeautifulSoup(response.text, "lxml")
        links = []
        for link in soup.find_all("a", href=True):
            title = clean_text(link.get_text(" ", strip=True))
            href = link["href"]
            if len(title) < 5:
                continue
            if href.startswith("/"):
                parsed = urlparse(url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            blob = f"{title} {href}"
            if any(keyword in blob.lower() for keyword in ["scam", "fraud", "warning", "phishing", "unauthorised", "alert", "cyber", "consumer", "complaint", "report"]):
                links.append((title, href))
        seen = set()
        unique_links = []
        for title, href in links:
            marker = stable_id(title, href)
            if marker not in seen:
                seen.add(marker)
                unique_links.append((title, href))
        print(f" - {source}: {len(unique_links[:25])} linked items")
        for title, href in unique_links[:25]:
            records.append(normalise_record(source, title, href, title, "", title, source))
    return records


def collect_all():
    rows = collect_rss() + collect_optional_pages()
    print("\nProcessing, deduplicating and scoring...")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates("id").reset_index(drop=True)
    if scope_choice == "4":
        mask = df.apply(lambda row: focus_query.lower() in f"{row.title} {row.summary} {row.text_sample} {row.scam_type} {row.detail_theme}".lower(), axis=1)
        focused = df[mask]
        if len(focused) >= 8:
            df = focused.reset_index(drop=True)
    df = df.sort_values(["risk_score", "confidence_score", "date"], ascending=[False, False, False]).reset_index(drop=True)
    return df


def explode_counts(df, column, n=10, include_unknown=False):
    values = []
    for item in df[column].fillna("Unknown"):
        parts = [part.strip() for part in str(item).split(",") if part.strip()]
        values += parts or ["Unknown"]
    series = pd.Series(values)
    if not include_unknown:
        series = series[series != "Unknown"]
    if series.empty:
        return pd.Series(dtype=int)
    return series.value_counts().head(n)


def build_stats(df):
    locations = explode_counts(df, "location", 10, include_unknown=False)
    scams = explode_counts(df, "scam_type", 10, include_unknown=True)
    themes = explode_counts(df, "detail_theme", 10, include_unknown=False)
    scopes = explode_counts(df, "geo_scope", 10, include_unknown=True)
    sources = explode_counts(df, "source", 10, include_unknown=True)
    unknown_locations = int((df["location"] == "Unknown").sum())
    known_locations = int(len(df) - unknown_locations)
    return {
        "records": len(df),
        "sources": df["source"].nunique(),
        "critical": int((df["risk_band"] == "Critical").sum()),
        "high": int((df["risk_band"] == "High").sum()),
        "medium": int((df["risk_band"] == "Medium").sum()),
        "low": int((df["risk_band"] == "Low").sum()),
        "high_critical": int(df[df["risk_band"].isin(["High", "Critical"])].shape[0]),
        "unknown_locations": unknown_locations,
        "known_locations": known_locations,
        "location_coverage_pct": round((known_locations / len(df)) * 100, 1) if len(df) else 0,
        "top_location": locations.index[0] if not locations.empty else "Unknown",
        "top_scam": scams.index[0] if not scams.empty else "Unknown",
        "top_theme": themes.index[0] if not themes.empty else "N/A",
        "top_scope": scopes.index[0] if not scopes.empty else "Unknown",
        "top_source": sources.index[0] if not sources.empty else "Unknown",
        "avg_risk": round(float(df["risk_score"].mean()), 1),
        "avg_confidence": round(float(df["confidence_score"].mean()), 1),
        "focus": focus_query if scope_choice == "4" else f"{SCOPE} overview",
        "coverage": SCOPE,
    }


def generate_executive_summary(df, stats):
    return (
        f"This run collected {stats['records']} public scam/fraud-related records from {stats['sources']} source groups. "
        f"The selected scope was {stats['coverage']}. The leading category was {stats['top_scam']}, with an average risk score of {stats['avg_risk']}/100 and average confidence of {stats['avg_confidence']}/100. "
        f"{stats['high_critical']} records were classified as High or Critical priority. Location extraction identified usable location mentions in {stats['location_coverage_pct']}% of records. "
        f"The leading mentioned location was {stats['top_location']}. Where records remain classified as General Fraud / Scam, the dashboard adds secondary themes, next-search recommendations and recommended verification sources. "
        f"Locations are treated as mentions only, not verified incident locations."
    )


def generate_recommendations(df, stats):
    recommendations = [
        "Manually review Critical and High records before external publication.",
        "Use CSV verification columns for analyst review, false-positive removal and final-source validation.",
        "Use secondary themes to improve General Fraud / Scam records before publication.",
        "Track monthly category movement to identify emerging fraud patterns.",
        "Use this output as a monthly Medium/OSINTTEAM intelligence snapshot.",
    ]
    if stats["unknown_locations"] > stats["known_locations"]:
        recommendations.append("Improve location extraction later by adding final publisher-page extraction.")
    if stats["top_scam"] == "General Fraud / Scam":
        recommendations.append("Prioritise manual classification review for General Fraud / Scam records using the recommended_next_search column.")
    if SCOPE in ["EU", "UK+EU"]:
        recommendations.append("For EU records, validate with national consumer authorities, European Consumer Centres Network, Europol, ENISA or CERT-EU where relevant.")
    if SCOPE in ["UK", "UK+EU"]:
        recommendations.append("For UK records, validate with FCA, Action Fraud, NCSC, police or consumer-advice sources where relevant.")
    return recommendations


def make_bar(series, title, filename):
    if series.empty:
        return None
    plt.figure(figsize=(11, 6))
    series.sort_values().plot(kind="barh")
    plt.title(title)
    plt.xlabel("Records")
    plt.tight_layout()
    path = os.path.join(CHART_DIR, filename)
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def make_pie(series, title, filename):
    if series.empty:
        return None
    plt.figure(figsize=(8, 8))
    series.plot(kind="pie", autopct="%1.1f%%", startangle=90)
    plt.title(title)
    plt.ylabel("")
    plt.tight_layout()
    path = os.path.join(CHART_DIR, filename)
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def make_line_trend(df):
    tmp = df.copy()
    tmp["date_parsed"] = pd.to_datetime(tmp["date"], errors="coerce")
    tmp = tmp.dropna(subset=["date_parsed"])
    if tmp.empty:
        return None
    tmp["month"] = tmp["date_parsed"].dt.to_period("M").astype(str)
    trend = tmp.groupby("month").size().tail(12)
    if trend.empty:
        return None
    plt.figure(figsize=(11, 5.8))
    trend.plot(kind="line", marker="o")
    plt.title("Monthly scam/fraud intelligence trend")
    plt.xlabel("Month")
    plt.ylabel("Records")
    plt.xticks(rotation=45)
    plt.tight_layout()
    path = os.path.join(CHART_DIR, "monthly_trend.png")
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def make_stacked_risk_by_scam(df):
    if df.empty:
        return None
    pivot = pd.crosstab(df["scam_type"], df["risk_band"])
    for column in ["Low", "Medium", "High", "Critical"]:
        if column not in pivot.columns:
            pivot[column] = 0
    pivot = pivot[["Low", "Medium", "High", "Critical"]]
    pivot["total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("total", ascending=False).head(8).drop(columns=["total"])
    if pivot.empty:
        return None
    ax = pivot.plot(kind="barh", stacked=True, figsize=(12, 7))
    ax.set_title("Risk distribution by scam category")
    ax.set_xlabel("Records")
    ax.set_ylabel("Scam category")
    plt.tight_layout()
    path = os.path.join(CHART_DIR, "risk_by_scam_category.png")
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def create_charts(df):
    return {
        "scope_distribution": make_pie(explode_counts(df, "geo_scope", 5, include_unknown=True), "Geographic scope distribution", "scope_distribution.png"),
        "top_locations": make_bar(explode_counts(df, "location", 10, include_unknown=False), "Top locations mentioned", "top_locations.png"),
        "top_scams": make_bar(explode_counts(df, "scam_type", 8, include_unknown=True), "Top scam/fraud categories", "top_scams.png"),
        "general_themes": make_bar(explode_counts(df, "detail_theme", 8, include_unknown=False), "Secondary themes for General Fraud / Scam", "general_themes.png"),
        "sources": make_bar(explode_counts(df, "source", 10, include_unknown=True), "Top source groups collected", "sources.png"),
        "risk_distribution": make_pie(explode_counts(df, "risk_band", 4, include_unknown=True), "Risk band distribution", "risk_distribution.png"),
        "monthly_trend": make_line_trend(df),
        "risk_by_scam": make_stacked_risk_by_scam(df),
    }


def image_to_base64(path):
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def save_data(df):
    csv_path = os.path.join(DATA_DIR, "fraudmap_ukeu_records.csv")
    db_path = os.path.join(DATA_DIR, "fraudmap_ukeu.sqlite")
    export_df = df.copy()
    export_df["verified"] = ""
    export_df["false_positive"] = ""
    export_df["final_publisher_url"] = ""
    export_df["confirmed_location"] = ""
    export_df["analyst_notes"] = ""
    export_df.to_csv(csv_path, index=False)
    connection = sqlite3.connect(db_path)
    export_df.to_sql("fraud_records", connection, if_exists="replace", index=False)
    connection.close()
    return csv_path, db_path


def generate_ai_review_prompt(df, stats, executive_summary, recommendations):
    path = os.path.join(REPORT_DIR, "fraudmap_ai_review_prompt.md")
    columns = [
        "title", "source", "original_source", "geo_scope", "scam_type",
        "detail_theme", "location", "loss_amount", "risk_score",
        "risk_band", "confidence_score", "recommended_next_search",
    ]
    sample = df[columns].head(30).to_markdown(index=False)
    prompt = f"""
# FraudMap UK+EU — AI Review Prompt

Project:
FraudMap UK+EU — Scam & Fraud Intelligence Dashboard

Scope:
{stats['focus']}

Coverage:
{stats['coverage']}

Executive summary:
{executive_summary}

Recommendations:
{chr(10).join('- ' + item for item in recommendations)}

Task:
Review the dataset sample below and produce:

1. Executive intelligence summary
2. Top scam/fraud trends
3. UK/EU differences or similarities
4. Top affected or mentioned locations
5. Key public-risk themes
6. Prevention advice
7. Reporting advice
8. Data-quality limitations
9. Suggested dashboard improvements
10. Short LinkedIn/Medium-ready summary

Rules:
- Do not invent facts.
- Use only the dataset content.
- Treat locations as mentions, not confirmed incident locations.
- Avoid naming private individuals.
- Keep the tone professional and public-interest focused.

Dataset sample:
{sample}
"""
    with open(path, "w", encoding="utf-8") as file:
        file.write(prompt.strip())
    return path


def generate_markdown(df, stats, executive_summary, recommendations):
    path = os.path.join(REPORT_DIR, "fraudmap_ukeu_report.md")
    lines = [
        f"# {APP_NAME} Intelligence Report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Mode: {stats['focus']}",
        f"Coverage: {stats['coverage']}",
        "",
        "## Executive Summary",
        "",
        executive_summary,
        "",
        "## Key Metrics",
        f"- Records collected: **{stats['records']}**",
        f"- Unique source groups: **{stats['sources']}**",
        f"- Critical records: **{stats['critical']}**",
        f"- High records: **{stats['high']}**",
        f"- Medium records: **{stats['medium']}**",
        f"- Low records: **{stats['low']}**",
        f"- High/Critical combined: **{stats['high_critical']}**",
        f"- Average risk score: **{stats['avg_risk']} / 100**",
        f"- Average confidence: **{stats['avg_confidence']} / 100**",
        f"- Location coverage: **{stats['location_coverage_pct']}%**",
        f"- Top location mentioned: **{stats['top_location']}**",
        f"- Top scam category: **{stats['top_scam']}**",
        f"- Top secondary theme: **{stats['top_theme']}**",
        f"- Top geographic scope: **{stats['top_scope']}**",
        f"- Top source group: **{stats['top_source']}**",
        "",
        "## Top Locations Mentioned",
    ]
    locations = explode_counts(df, "location", 10, include_unknown=False)
    if locations.empty:
        lines.append("- No strong location mentions extracted.")
    else:
        for key, value in locations.items():
            lines.append(f"- {key}: {value}")
    lines += ["", "## Top Scam/Fraud Categories"]
    for key, value in explode_counts(df, "scam_type", 10, include_unknown=True).items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## Secondary Themes For General Fraud / Scam"]
    themes = explode_counts(df, "detail_theme", 10, include_unknown=False)
    if themes.empty:
        lines.append("- No secondary themes detected.")
    else:
        for key, value in themes.items():
            lines.append(f"- {key}: {value}")
    lines += ["", "## Priority Recommendations"]
    for item in recommendations:
        lines.append(f"- {item}")
    lines += ["", "## High-Priority Records"]
    for _, row in df.head(30).iterrows():
        lines += [
            f"### {row['title']}",
            f"- Geo scope: {row['geo_scope']}",
            f"- Source group: {row['source']}",
            f"- Original source: {row.get('original_source', '') or 'Not extracted'}",
            f"- Type: {row['scam_type']}",
            f"- Detail theme: {row['detail_theme'] or 'N/A'}",
            f"- Why general: {row['why_general'] or 'N/A'}",
            f"- Location mention: {row['location']}",
            f"- Loss mentioned: {row['loss_amount'] or 'Not visible'}",
            f"- Risk: {row['risk_score']} / {row['risk_band']}",
            f"- Confidence: {row['confidence_score']} / {row['confidence_band']}",
            f"- Analyst note: {row['intelligence_note']}",
            f"- Recommended sources: {row['recommended_sources']}",
            f"- Recommended next search: {row['recommended_next_search']}",
            f"- Prevention: {row['prevention']}",
            f"- Reporting: {row['reporting']}",
            f"- URL: {row['url']}",
            "",
        ]
    lines += [
        "",
        "## What To Do If Affected",
        "- Stop communication with the suspected scammer.",
        "- Contact your bank immediately if payment details or money are involved.",
        "- Preserve evidence: screenshots, URLs, emails, phone numbers and payment references.",
        "- Use the relevant national police, fraud, cybercrime or consumer protection reporting route.",
        "- UK: forward suspicious texts to 7726 and suspicious emails to report@phishing.gov.uk where applicable.",
        "- EU: check national consumer authority, European Consumer Centres Network, ENISA/CERT-EU/Europol resources where relevant.",
        "- Change exposed passwords and enable multi-factor authentication.",
        "",
        "## Methodology",
        "The dashboard collects public scam/fraud intelligence from RSS feeds, Google News RSS and public advice pages. It does not use hacked, leaked, private or personal datasets.",
        "",
        "## Limitations",
        "- Results are not exhaustive.",
        "- Google News RSS links may point to Google News redirect URLs rather than final publisher URLs.",
        "- Location mentions are not proof of confirmed incident location.",
        "- Risk scores and confidence scores are analytical indicators only.",
        "- Manual verification is required before external publication.",
    ]
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    return path


def generate_html(df, stats, charts, executive_summary, recommendations):
    path = os.path.join(REPORT_DIR, "fraudmap_ukeu_dashboard.html")
    display_columns = [
        "title", "geo_scope", "source", "original_source", "scam_type",
        "detail_theme", "location", "loss_amount", "risk_score", "risk_band",
        "confidence_score", "confidence_band", "recommended_next_search", "url",
    ]
    table = df[display_columns].head(40).to_html(index=False, escape=True, render_links=True)
    chart_html = ""
    for name, chart_path in charts.items():
        if chart_path and os.path.exists(chart_path):
            encoded = image_to_base64(chart_path)
            if encoded:
                chart_html += f'<section class="card"><h2>{name.replace("_", " ").title()}</h2><img src="data:image/png;base64,{encoded}"></section>'
    recommendations_html = "".join(f"<li>{xml_escape(item)}</li>" for item in recommendations)
    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{APP_NAME}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; background: #f4f4f4; color: #111; }}
header {{ background: #111; color: #fff; padding: 34px 46px; }}
header h1 {{ margin: 0; font-size: 38px; }}
header p {{ color: #ccc; margin-bottom: 0; }}
main {{ padding: 28px 46px; }}
.grid {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }}
.metric {{ background: #fff; padding: 18px; border: 1px solid #ddd; border-radius: 10px; }}
.metric b {{ font-size: 24px; display: block; }}
.card {{ background: #fff; padding: 24px; border: 1px solid #ddd; border-radius: 10px; margin-top: 18px; }}
img {{ max-width: 100%; border: 1px solid #ddd; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th, td {{ border-bottom: 1px solid #ddd; padding: 7px; vertical-align: top; }}
th {{ background: #eee; }}
.badge {{ display: inline-block; background: #111; color: #fff; padding: 4px 8px; border-radius: 6px; font-size: 12px; }}
</style>
</head>
<body>
<header>
<h1>{APP_NAME}</h1>
<p>Scam & Fraud Intelligence Dashboard | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</header>
<main>
<div class="grid">
<div class="metric"><b>{stats['records']}</b>Records</div>
<div class="metric"><b>{stats['sources']}</b>Sources</div>
<div class="metric"><b>{stats['critical']}</b>Critical</div>
<div class="metric"><b>{stats['high']}</b>High</div>
<div class="metric"><b>{stats['avg_risk']}</b>Avg risk</div>
<div class="metric"><b>{stats['location_coverage_pct']}%</b>Location coverage</div>
</div>
<section class="card">
<h2>Executive Summary</h2>
<p>{xml_escape(executive_summary)}</p>
<p><span class="badge">Mode: {xml_escape(stats['focus'])}</span> <span class="badge">Coverage: {xml_escape(stats['coverage'])}</span></p>
</section>
<section class="card"><h2>Priority Recommendations</h2><ul>{recommendations_html}</ul></section>
{chart_html}
<section class="card"><h2>Top Records</h2>{table}</section>
<section class="card">
<h2>How To Avoid & Report</h2>
<ul>
<li>Do not click suspicious links or send money under pressure.</li>
<li>Verify firms, recruiters, banks and deliveries through official websites.</li>
<li>Use multi-factor authentication and unique passwords.</li>
<li>Preserve evidence and report suspected fraud through official national routes.</li>
<li>UK: suspicious texts can be forwarded to 7726 and suspicious emails to report@phishing.gov.uk where applicable.</li>
<li>EU: check national consumer protection authorities, European Consumer Centres Network, Europol, ENISA and CERT-EU where relevant.</li>
</ul>
</section>
<section class="card"><h2>Methodology & Ethics</h2><p>Public sources only. No hacked, leaked, private or personal datasets. Keyword classification, risk scoring and confidence scoring require manual verification.</p></section>
</main>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as file:
        file.write(html)
    return path


def pdf_clean(text, limit=1200):
    text = clean_text(text)
    text = re.sub(r"https?://\S+", "[URL in dataset/report]", text)
    return xml_escape(text[:limit])


def generate_pdf(df, stats, charts, executive_summary, recommendations):
    path = os.path.join(REPORT_DIR, "fraudmap_ukeu_report.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=1.4 * cm, leftMargin=1.4 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    story = []
    story.append(Paragraph(f"{APP_NAME} Intelligence Report", styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Paragraph(f"Mode: {pdf_clean(stats['focus'])}", styles["Normal"]))
    story.append(Paragraph(f"Coverage: {pdf_clean(stats['coverage'])}", styles["Normal"]))
    story.append(Spacer(1, 12))
    metric_data = [
        ["Records", stats["records"], "Sources", stats["sources"]],
        ["Critical", stats["critical"], "High", stats["high"]],
        ["Avg Risk", stats["avg_risk"], "Avg Confidence", stats["avg_confidence"]],
        ["Top Scam", stats["top_scam"], "Top Location", stats["top_location"]],
    ]
    metric_table = Table(metric_data, colWidths=[3.2 * cm, 4.5 * cm, 3.2 * cm, 5.5 * cm])
    metric_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(metric_table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(pdf_clean(executive_summary), styles["Normal"]))
    story.append(Paragraph("Priority Recommendations", styles["Heading2"]))
    for item in recommendations:
        story.append(Paragraph("• " + pdf_clean(item, 400), styles["Normal"]))
    story.append(PageBreak())
    story.append(Paragraph("Charts", styles["Heading2"]))
    for name, chart_path in charts.items():
        if chart_path and os.path.exists(chart_path):
            story.append(Paragraph(name.replace("_", " ").title(), styles["Heading3"]))
            story.append(RLImage(chart_path, width=16 * cm, height=9 * cm))
            story.append(Spacer(1, 10))
    story.append(PageBreak())
    story.append(Paragraph("High-Priority Records", styles["Heading2"]))
    for _, row in df.head(18).iterrows():
        story.append(Paragraph(pdf_clean(row["title"], 300), styles["Heading3"]))
        story.append(Paragraph(pdf_clean(f"{row['geo_scope']} | {row['source']} | {row['scam_type']} | {row['location']} | Risk {row['risk_score']} {row['risk_band']} | Confidence {row['confidence_score']} {row['confidence_band']}", 500), styles["Small"]))
        story.append(Paragraph(pdf_clean(f"Detail theme: {row['detail_theme'] or 'N/A'}", 500), styles["Small"]))
        story.append(Paragraph(pdf_clean(f"Next search: {row['recommended_next_search']}", 500), styles["Small"]))
        story.append(Paragraph(pdf_clean(f"How to avoid: {row['prevention']}", 500), styles["Small"]))
        story.append(Spacer(1, 8))
    story.append(PageBreak())
    story.append(Paragraph("Methodology, Safety & Reporting", styles["Heading2"]))
    story.append(Paragraph("This tool collects public scam and fraud intelligence from RSS feeds, Google News RSS and public advice pages. It does not use hacked, leaked, private or personal datasets.", styles["Normal"]))
    story.append(Paragraph("Location mentions are not proof of incident location. Risk scores and confidence scores are analytical indicators only. Manual verification is required before external publication.", styles["Normal"]))
    doc.build(story)
    return path


def make_zip():
    zip_path = f"/content/fraudmap_ukeu_{RUN_ID}_exports.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, file_names in os.walk(EXPORT_DIR):
            for file_name in file_names:
                full_path = os.path.join(root, file_name)
                archive_name = os.path.relpath(full_path, EXPORT_DIR)
                archive.write(full_path, archive_name)
    return zip_path


def main():
    start_time = time.time()
    df = collect_all()
    if df.empty:
        print("No data collected. Try a broader query or a different scope.")
        return
    stats = build_stats(df)
    charts = create_charts(df)
    executive_summary = generate_executive_summary(df, stats)
    recommendations = generate_recommendations(df, stats)
    csv_path, db_path = save_data(df)
    md_path = generate_markdown(df, stats, executive_summary, recommendations)
    html_path = generate_html(df, stats, charts, executive_summary, recommendations)
    pdf_path = generate_pdf(df, stats, charts, executive_summary, recommendations)
    ai_prompt_path = generate_ai_review_prompt(df, stats, executive_summary, recommendations)
    zip_path = make_zip()
    print("\n" + "=" * 100)
    print("RUN SUMMARY")
    print("=" * 100)
    print(f"Mode:                 {stats['focus']}")
    print(f"Coverage:             {stats['coverage']}")
    print(f"Records:              {stats['records']}")
    print(f"Sources:              {stats['sources']}")
    print(f"Critical:             {stats['critical']}")
    print(f"High:                 {stats['high']}")
    print(f"Medium:               {stats['medium']}")
    print(f"Low:                  {stats['low']}")
    print(f"High/Critical:        {stats['high_critical']}")
    print(f"Average risk:         {stats['avg_risk']}/100")
    print(f"Average confidence:   {stats['avg_confidence']}/100")
    print(f"Known locations:      {stats['known_locations']}")
    print(f"Unknown locations:    {stats['unknown_locations']}")
    print(f"Location coverage:    {stats['location_coverage_pct']}%")
    print(f"Top geo scope:        {stats['top_scope']}")
    print(f"Top location:         {stats['top_location']}")
    print(f"Top scam:             {stats['top_scam']}")
    print(f"Top theme:            {stats['top_theme']}")
    print(f"Top source group:     {stats['top_source']}")
    print(f"Runtime:              {round(time.time() - start_time, 2)} seconds")
    print("=" * 100)
    print("\nEXECUTIVE SUMMARY")
    print("-" * 100)
    print(executive_summary)
    print("\nPRIORITY RECOMMENDATIONS")
    print("-" * 100)
    for item in recommendations:
        print(f"- {item}")
    display_columns = ["title", "geo_scope", "source", "original_source", "scam_type", "detail_theme", "location", "loss_amount", "risk_score", "risk_band", "confidence_score", "confidence_band", "recommended_next_search", "url"]
    display(df[display_columns].head(25))
    print("\nCharts:")
    for name, chart_path in charts.items():
        if chart_path and os.path.exists(chart_path):
            display(HTML(f"<h3>{name.replace('_', ' ').title()}</h3>"))
            display(Image(filename=chart_path))
    print("\nHTML dashboard preview:")
    with open(html_path, "r", encoding="utf-8") as file:
        display(HTML(file.read()))
    print("\nExport files created in this Colab session.")
    print("No download has started.")
    print("ZIP export is ready.")
    if input("\nDownload all exports as ZIP now? [y/N]: ").lower().strip() == "y":
        files.download(zip_path)
    if input("\nShow internal file paths? [y/N]: ").lower().strip() == "y":
        for path in [csv_path, db_path, md_path, html_path, pdf_path, ai_prompt_path, zip_path]:
            print(" -", path)
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("\nTemporary workspace cleaned. Exports remain available during this Colab session.")
    print("\nPortfolio line:")
    print("Built FraudMap UK+EU, a Colab-based OSINT and data-analysis dashboard that collects, classifies, scores and visualises public scam/fraud intelligence across UK and EU source layers, producing professional reports, charts, CSV, SQLite and dashboard exports.")


main()
