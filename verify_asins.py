#!/usr/bin/env python3
"""Verifica che ogni ASIN punti realmente al prodotto atteso su ogni TLD EU.
Confronta il titolo reale della pagina con le keyword del componente.
Segnala: titolo non combaciante, pagina 404/inesistente, prezzo presente ma prodotto sbagliato.
"""
import asyncio, json
from playwright.async_api import async_playwright

COMPONENTS = {
    "Ryzen 7 7800X3D":      ("B0BTZB7F88", ["7800x3d"]),
    "Ryzen 9 7950X3D":      ("B0BTRH9MNS", ["7950x3d"]),
    "RTX 5080 16GB":        ("B0BSLJK16Z", ["5080"]),
    "RX 7900 XTX":          ("B0BNLSW23M", ["7900 xtx", "7900xtx"]),
    "DDR5 64GB 6000MHz":    ("B0DSQVNBD5", ["64", "ddr5", "6000"]),
    "SSD 990 PRO 2TB":      ("B0B9C4DKKG", ["990 pro", "2tb"]),
    "ASUS Z790-A WiFi II":  ("B0CJMR6652", ["z790", "wifi"]),
    "Corsair RM1000x":      ("B0BPSWXKSB", ["rm1000"]),
    "Fractal Meshify 2":    ("B0822ZD9NP", ["meshify 2"]),
    "Noctua NH-D15":        ("B00L7UZMAK", ["nh-d15"]),
    "Noctua NF-A12x25 (x3)":("B07C5VG64V", ["nf-a12x25"]),
    "Windows 11 Pro (key)": ("B09X11M88J", ["windows 11"]),
}

# TLD -> Accept-Language
TLDS = [
    ("it", "it-IT,it;q=0.9"),
    ("de", "de-DE,de;q=0.9"),
    ("es", "es-ES,es;q=0.9"),
    ("fr", "fr-FR,fr;q=0.9"),
    ("nl", "nl-NL,nl;q=0.9"),
    ("pl", "pl-PL,pl;q=0.9"),
]

async def check_page(page, asin, tld, kw):
    url = f"https://www.amazon.{tld}/dp/{asin}"
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(2500)
        info = await page.evaluate("""() => {
            const t = document.querySelector('#productTitle')?.innerText
                   || document.title
                   || document.querySelector('h1')?.innerText || '';
            const body = document.body.innerText.slice(0, 1500).toLowerCase();
            const notFound = /page not found|prodotto non disponibile|articolo non disponibile|non esiste|dieser artikel existiert nicht|cet article n'existe pas|esta pagina no existe|pagina niet gevonden|strona nie istnieje/i.test(document.body.innerText);
            const priceEl = document.querySelector('#newBuyBoxPrice, #price_inside_buybox, .a-price.a-text-price span.a-offscreen, #buybox .a-price span.a-offscreen');
            const price = priceEl ? priceEl.innerText : '';
            return {title: t.trim().slice(0,120), body, notFound, price};
        }""")
        low = (info["title"] + " " + info["body"]).lower()
        matches = all(k in low for k in kw)
        return {
            "asin": asin, "tld": tld,
            "title": info["title"],
            "notFound": info["notFound"],
            "matchesExpected": matches,
            "price": info["price"],
        }
    except Exception as e:
        return {"asin": asin, "tld": tld, "error": str(e)[:100], "matchesExpected": False}

async def main():
    report = []
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page()
        for name, (asin, kw) in COMPONENTS.items():
            for tld, lang in TLDS:
                await pg.set_extra_http_headers({"Accept-Language": lang})
                r = await check_page(pg, asin, tld, kw)
                r["component"] = name
                report.append(r)
                flag = "OK" if (r.get("matchesExpected") and not r.get("notFound")) else "BAD"
                print(f"{flag:4} {name[:22]:22} {tld} -> {r.get('title','')[:60]} | price={r.get('price','')}", flush=True)
        await b.close()
    with open("verify_asins_report.json", "w") as f:
        json.dump(report, f, indent=2)
    bad = [r for r in report if not (r.get("matchesExpected") and not r.get("notFound"))]
    print(f"\n=== RIEPILOGO: {len(bad)}/{len(report)} (componente,tld) NON VALIDI ===")
    for r in bad:
        print(f"  {r['component']} @ {r['tld']}: notFound={r.get('notFound')} matches={r.get('matchesExpected')} title='{r.get('title','')[:70]}'")

asyncio.run(main())
