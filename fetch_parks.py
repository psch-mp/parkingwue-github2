#!/usr/bin/env python3
# fetch_parks.py
# -*- coding: utf-8 -*-

import re
import requests
import pandas as pd
from datetime import datetime

API_URL = "https://geostadtplan.wuerzburg.de/services/getData.php?client=207&catid=39368&lang=de&admin_mode=false"
OUTPUT_CSV = "Parkplaetze.csv"

def clean_name(name: str) -> str:
    """Entfernt PP, PH, DH und 'Würzburg' aus dem Namen"""
    if not isinstance(name, str):
        return ""
    name = re.sub(r'\b(PP|PH|DH)\.?\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bW[üu]rzburg\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-/]+', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_from_ci(ci_html: str):
    """Extrahiert freie Plätze und Auslastung aus dem HTML-String"""
    if not isinstance(ci_html, str):
        return ("", "")
    bolds = re.findall(r'<b>(.*?)</b>', ci_html, flags=re.IGNORECASE)
    free_spaces = bolds[0].strip() if len(bolds) >= 1 else ""
    occupancy = bolds[1].strip() if len(bolds) >= 2 else ""
    return (free_spaces, occupancy)

def google_maps_place_link(lat, lng):
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

def google_maps_directions_link(lat, lng, travelmode="driving"):
    return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode={travelmode}"

def main():
    try:
        resp = requests.get(API_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print("Fehler beim Abrufen der API:", e)
        raise

    rows = []
    cats = data.get("cats") or []
    jetzt = datetime.now()
    zeit_str = jetzt.strftime("%d.%m.%y %H:%M")

    for category in cats:
        for p in category.get("p", []):
            name_raw = p.get("co")
            name = clean_name(name_raw)

            lat = p.get("lat")
            lng = p.get("lng")
            try:
                lat_f = float(lat) if lat is not None else None
                lng_f = float(lng) if lng is not None else None
            except:
                lat_f, lng_f = None, None

            ci = p.get("ci", "")
            free_spaces, occupancy = extract_from_ci(ci)

            # Sicherstellen, dass keine None-Werte in die CSV kommen
            free_spaces = free_spaces or ""
            occupancy = occupancy or ""

            # HTML-Links mit Parkplatznamen
            place_url = f'<a href="{google_maps_place_link(lat_f, lng_f)}">Standort {name}</a>' if lat_f and lng_f else ""
            directions_url = f'<a href="{google_maps_directions_link(lat_f, lng_f)}">Anfahrt {name}</a>' if lat_f and lng_f else ""

            rows.append({
                "Parkplatz": name,
                "Freie Plätze": free_spaces,
                "Auslastung in %": occupancy,
                "Karte": place_url,
                "Anfahrt": directions_url,
                "Zuletzt aktualisiert am": zeit_str
            })

    df = pd.DataFrame(rows)
    df = df.sort_values(by=["Parkplatz"])
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"CSV geschrieben: {OUTPUT_CSV} ({len(df)} Einträge)")

if __name__ == "__main__":
    main()
