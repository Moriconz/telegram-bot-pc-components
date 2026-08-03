#!/usr/bin/env python3
"""
Gestione link PC pre-assemblati EU (64GB RAM) con aggiornamento automatico dei LINK.

Comportamento:
 - Verifica che ogni URL prodotto sia VIVO (HTTP 200). Se non risponde -> broken=True
   e il frontend lo esclude (cosi' non restano link rotti nel sito).
 - I PREZZI restano curati (verificati a mano via ricerca): lo scraping dei prezzi dai
   siti vendor e' inaffidabile (JS-rendered, anti-bot, prezzi parziali). Li aggiorno
   manualmente quando cambiano. Qui aggiorniamo solo lo STATO del link.
 - Salva in data.json["prebuilt"] + data.json["prebuilt_updated_at"].
   Il frontend e il bot leggono da li': i link si aggiornano da soli a ogni run
   (rotti esclusi, vivi mostrati). Per "trovare di meglio" si amplia la lista KNOWN.

Per il futuro: se vuoi prezzi live, serve Playwright mirato per estrarre il prezzo
esatto dal DOM (es. selettore prezzo Dubaro), da aggiungere qui.
"""
import os
import json
import requests
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, "data.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

# Lista PC noti (verificati a mano). 'better'=specifiche superiori al fai-da-te.
# price = prezzo curato (EUR, IVA incl.), aggiornato manualmente quando cambia.
# Rivenditori EU fuori Italia inclusi (DE/FR/NL/UK) + aggregatori + generici.
KNOWN = [
    {"name": "VIST PRO — R7 7800X3D + RTX 5080 + 64GB (DE)", "url": "https://www.idealo.de/preisvergleich/OffersOfProduct/206078581_-pro-pc-ryzen-7-7800x3d-rtx-5080-64gb-1tb-vi2401-vist-pc.html", "better": False, "price": 3089.90},
    {"name": "Dubaro — R7 7800X3D + RTX 5080 + 64GB (DE)", "url": "https://www.dubaro.de/Gaming-PC-Ryzen-7-7800X3D-mit-RTX5080-102157/", "better": False, "price": 2949.00},
    {"name": "memorypc — R7 7800X3D + RTX 5080 + 64GB (DE)", "url": "https://www.memorypc.eu/high-end-gaming-pc/geforce-rtx-566076/", "better": False, "price": 2839.00},
    {"name": "memorypc.fr — R7 7800X3D + RTX 5080 + 64GB (FR)", "url": "https://www.memorypc.fr/pc-gamer-high-end/nvidia-geforce-552908/", "better": False, "price": 2899.00},
    {"name": "LDLC — PC RTX 5080 + R7 7800X3D + 64GB (FR)", "url": "https://www.ldlc.com/informatique/ordinateur-de-bureau/pc-de-marque/c4250/+fb-C000000888+fv121-126519.html", "better": False, "price": 3379.00},
    {"name": "PC Specialist — RTX 5080 + R7 7800X3D + 64GB (UK)", "url": "https://www.pcspecialist.co.uk/desktop-pcs/nvidia-rtx-50-series/", "better": False, "price": 3799.00},
    {"name": "Dubaro — R9 7950X3D + RTX 5080 + 64GB (DE)", "url": "https://www.dubaro.de/Gaming-PC-Ryzen-7-7800X3D-mit-RTX5080-102157/", "better": True, "price": 3450.00},
]


def is_alive(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False


def check_links():
    results = []
    for item in KNOWN:
        alive = is_alive(item["url"])
        rec = dict(item)
        rec["alive"] = alive
        rec["broken"] = not alive
        if alive:
            print(f"  OK   {item['name']} @ {item['url']}")
        else:
            print(f"  BROKEN {item['name']} @ {item['url']}  -> escluso dal sito")
        results.append(rec)
    return results


def update_data_json(prebuilt):
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH) as f:
            d = json.load(f)
    else:
        d = {}
    d["prebuilt"] = prebuilt
    d["prebuilt_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DATA_PATH, "w") as f:
        json.dump(d, f, indent=2)
    alive = sum(1 for p in prebuilt if not p["broken"])
    print(f"Salvato data.json: {alive}/{len(prebuilt)} PC pre-assemblati vivi")


if __name__ == "__main__":
    print("Controllo link PC pre-assemblati...")
    prebuilt = check_links()
    update_data_json(prebuilt)
    print("Done.")
