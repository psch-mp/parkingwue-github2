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
    """
    Entfernt Abkürzungen PP, PH, DH und das Wort 'Würzburg' (fallunabhängig),
    entfernt überflüssige Zeichen und doppelten Leerraum.
    """
    if not isinstance(name, str):
        return name
    # Entferne PP, PH, DH als ganze Wörter (auch mit Punkt), case-insensitive
    name = re.sub(r'\b(PP|PH|DH)\.?\b', '', name, flags=re.IGNORECASE)
    # Entferne 'Würzburg' (inkl. Würzburg-Varianten) case-insensitive
    name = re.sub(r'\bW[üu]rzburg\b', '', name, flags=re.IGNORECASE)
    # Entferne wiederholte Bindestriche, Schrägstriche am Rand und überflüssige Leerzeichen
    name = re.sub(r'[-/]+', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_from_ci(ci_html: str):
    """
    Extrahiert die (erste) Zahl in <b>...</b> als freie Plätze und
    den (möglichen) Prozentsatz in einem späteren <b>...</b>.
    Falls das Format abweicht, liefert None.
    """
    if not isinstance(ci_html, str):
        return (None, None)
    # Finde alle <b>...</b> Inhalte
    bolds = re.findall(r'<b>(.*?)</b>', ci_html, flags=re.IGNORECASE)
    free_spaces = None
    occupancy = None
    if len(bolds) >= 1:
        # erste Bold wird üblicherweise die Zahl der freien Plätze sein
        free_spaces = bolds[0].strip()
    if len(bolds) >= 2:
        occupancy = bolds[1].strip()
    # Falls occupancy wie '65%' mit Prozentzeichen oder als Zahl vorliegt, belassen
    return (free_spaces, occupancy)

def google_maps_place_link(lat, lng):
    # Öffnet die Position (Such/Place)
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

def google_maps_directions_link(lat, lng, travelmode="driving"):
    # Directions mit Ziel. Wenn kein origin angegeben wird, versucht Maps die
    # aktuelle Position des Benutzers zu verwenden (funktioniert auf Mobilgeräten gut).
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
    # Datenstruktur prüfen
    cats = data.get("cats") or []
    for category in cats:
        for p in category.get("p", []):
            name_raw = p.get("co")
            name = clean_name(name_raw)

            lat = p.get("lat")
            lng = p.get("lng")
            # Sicherstellen, dass lat/lng vorhanden sind
            try:
                lat_f = float(lat) if lat is not None else None
                lng_f = float(lng) if lng is not None else None
            except:
                lat_f, lng_f = None, None

            ci = p.get("ci", "")
            free_spaces, occupancy = extract_from_ci(ci)

            place_url = google_maps_place_link(lat_f, lng_f) if lat_f is not None and lng_f is not None else None
            directions_url = google_maps_directions_link(lat_f, lng_f) if lat_f is not None and lng_f is not None else None

            rows.append({
                "Name Parkhaus": name,
                "Name Raw": name_raw,
                "Lat": lat_f,
                "Lng": lng_f,
                "Freie Parkplätze": free_spaces,
                "Auslastung": occupancy,
                "Maps Place URL": place_url,
                "Maps Directions URL": directions_url,
                "Erstellt am (UTC)": datetime.utcnow().isoformat()
            })

    df = pd.DataFrame(rows)
    # Sortierung optional, z.B. nach Name
    df = df.sort_values(by=["Name Parkhaus"])
    # Speichere CSV (utf-8 mit BOM nicht notwendig, Datawrapper kann utf-8 lesen)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"CSV geschrieben: {OUTPUT_CSV} ({len(df)} Einträge)")

if __name__ == "__main__":
    main()
