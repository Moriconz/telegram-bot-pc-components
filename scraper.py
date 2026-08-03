#!/usr/bin/env python3
"""
Scraper reale prezzi componenti PC — TUTTA EUROPA.
Usa Playwright per leggere i prezzi vivi da Amazon IT/DE/ES/FR/NL/PL.
Salva data.json (usato dal sito web). Prezzi veri, link veri.
"""

import asyncio
import json
import os
import statistics
import time
from datetime import datetime
from playwright.async_api import async_playwright
try:
    from agent_log import log_event
except Exception:
    def log_event(*a, **k):
        pass

DATA_PATH = "/Users/riccardomoricone/telegram-bot-pc-components/data.json"

# Marketplace Europa: tld -> nome leggibile
EU_TLDS = [
    ("it", "Amazon.it"),
    ("de", "Amazon.de"),
    ("es", "Amazon.es"),
    ("fr", "Amazon.fr"),
    ("nl", "Amazon.nl"),
    ("pl", "Amazon.pl"),
]

# Tasso di cambio approssimativo PLN->EUR (da aggiornare se serve). Usato solo per .pl.
PLN_TO_EUR = 0.233  # 1 PLN ≈ 0.233 EUR

# Componenti con ASIN veri (globali: stesso ASIN funziona su tutti i TLD EU)
COMPONENTS = {
    "Ryzen 7 7800X3D":           {"asin": "B0BTZB7F88", "cat": "CPU"},
    "Ryzen 9 7950X3D":           {"asin": "B0BTRH9MNS", "cat": "CPU"},
    "RTX 5080 16GB":            {"asin": "B0BSLJK16Z", "cat": "GPU"},
    "RX 7900 XTX":              {"asin": "B0BNLSW23M", "cat": "GPU"},
    "DDR5 64GB 6000MHz":        {"asin": "B0DSQVNBD5", "cat": "RAM"},
    "SSD 990 PRO 2TB":          {"asin": "B0B9C4DKKG", "cat": "SSD"},
    "ASUS Z790-A WiFi II":      {"asin": "B0CJMR6652", "cat": "MB"},
    "Corsair RM1000x":          {"asin": "B0BPSWXKSB", "cat": "PSU"},
    "Fractal Meshify 2":        {"asin": "B0822ZD9NP", "cat": "Case"},
    "Noctua NH-D15":            {"asin": "B00L7UZMAK",  "cat": "Cooler"},
    "Noctua NF-A12x25 (x3)":        {"asin": "B07C5VG64V", "cat": "Fans", "qty": 3},
    "Windows 11 Pro (key)":     {"asin": "B09X11M88J",  "cat": "OS"},
}

LANG_HEADERS = {
    "it": "it-IT,it;q=0.9", "de": "de-DE,de;q=0.9", "es": "es-ES,es;q=0.9",
    "fr": "fr-FR,fr;q=0.9", "nl": "nl-NL,nl;q=0.9", "pl": "pl-PL,pl;q=0.9",
}

# .pl quotato in PLN, tutti gli altri in EUR
TLD_CURRENCY = {"it": "EUR", "de": "EUR", "es": "EUR", "fr": "EUR", "nl": "EUR", "pl": "PLN"}

async def scrape_price(page, asin, tld, label):
    url = f"https://www.amazon.{tld}/dp/{asin}"
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(2500)
        # Prendi il prezzo dal blocco "Acquista nuovo" (buybox), non il primo sparso.
        # Cerca prima il prezzo del buybox, poi il prezzo generico piu' visibile.
        price = await page.evaluate('''() => {
            const parse = (t) => {
                if (!t) return null;
                const cleaned = t.replace(/[^0-9.,]/g, '');
                if (!cleaned) return null;
                // Europa: separatore decimale e' virgola in IT/ES/FR/NL/PL, punto in DE
                const hasComma = cleaned.includes(',');
                const normalized = hasComma ? cleaned.replace(/\\./g, '').replace(',', '.')
                                              : cleaned.replace(/,(?=\\d{3})/g, '');
                const v = parseFloat(normalized);
                return isNaN(v) ? null : v;
            };
            // Stato disponibilita' reale: controllato su TUTTI i TLD EU (IT/DE/ES/FR/NL/PL).
            // Regex multilingua: copre ogni frase "non disponibile/out of stock" per ogni lingua Amazon EU.
            const availEl = document.querySelector('#availability, #availabilityInsideBuyBox, #availabilityInsideBuybox_feature_div, #availability_feature_div, #outOfStock, #deliveryMessageMirId');
            const availTxt = (availEl ? availEl.innerText : '') + ' '
                           + (document.querySelector('#buybox')?.innerText || '').slice(0, 600) + ' '
                           + document.body.innerText.slice(0, 3000);
            const UNAVAIL = /non disponibile|attualmente non disponibile|non piu disponibile|esaurito|non in stock|indisponible|rupture de stock|epuise|est plus disponible|niet beschikbaar|niet verkrijgbaar|er niet meer|tijdelijk uitverkocht|nicht verfugbar|momentan nicht|nicht lieferbar|ausverkauft|no disponible|agotado|sin stock|temporalmente agotado|niedostepny|brak w magazynie|wyprzedany|chwilowo niedostepny|currently unavailable|out of stock|temporarily out of stock|we don'?t know when/i;
            const unavailable = UNAVAIL.test(availTxt);
            // 1) prezzo buybox / "acquista nuovo"
            const buy = document.querySelector('#newBuyBoxPrice, #price_inside_buybox, .a-price.a-text-price span.a-offscreen, #buybox .a-price span.a-offscreen');
            const b = buy ? parse(buy.textContent) : null;
            if (b && !unavailable) return { price: b, available: true };
            // 2) primo prezzo visibile nella pagina (solo se disponibile)
            const els = document.querySelectorAll('[class*="a-price"] span[class*="a-price-whole"]');
            for (const el of els) {
                const v = parse(el.textContent);
                if (v && v > 1 && !unavailable) return { price: v, available: true };
            }
            // Articolo non disponibile: ritorna prezzo (se presente) ma available=False
            const anyPrice = b || (els[0] ? parse(els[0].textContent) : null);
            return { price: anyPrice, available: false };
        }''')
        if not isinstance(price, dict):
            return {"price": price, "currency": TLD_CURRENCY[tld], "url": url,
                    "available": price is not None}
        return {"price": price.get("price"),
                "currency": TLD_CURRENCY[tld],
                "url": url,
                "available": price.get("available", False)}
    except Exception as e:
        return {"price": None, "url": url, "available": False, "error": str(e)[:120]}

async def scrape_combo(page, query, tld, label, require_ram_64=False):
    """Cerca un bundle su Amazon e ritorna SOLO risultati il cui TITOLO reale
    contiene i componenti richiesti. Verifica il titolo (non si fida del primo
    risultato) e ne estrae i componenti effettivamente inclusi.
    Gli ASIN dei bundle scadono: per questo li cerchiamo a runtime."""
    url = f"https://www.amazon.{tld}/s?k={query.replace(' ', '+')}"
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)
        res = await page.evaluate('''(requireRam64) => {
            const cards = [...document.querySelectorAll('[data-component-type="s-search-result"]')];
            const parseP = (txt) => {
                const cleaned = (txt||'').replace(/[^0-9.,]/g, '');
                if (!cleaned) return null;
                const hasComma = cleaned.includes(',');
                const v = parseFloat(hasComma ? cleaned.replace(/\\./g, '').replace(',', '.')
                                               : cleaned.replace(/,(?=\\d{3})/g, ''));
                return (v && v > 50) ? v : null;
            };
            for (const c of cards) {
                const asin = c.getAttribute("data-asin") || "";
                if (!asin) continue;
                const titleEl = c.querySelector("h2 a span, h2 span, .a-size-medium.a-color-base.a-text-normal");
                const title = (titleEl ? titleEl.innerText : (c.querySelector('[aria-label]')?.getAttribute('aria-label')||''));
                const low = title.toLowerCase();
                // Deve contenere il CPU target
                if (!/7800x3d/.test(low)) continue;
                // Se richiesta RAM 64GB, il titolo deve dichiararla esplicitamente
                if (requireRam64 && !/64\s?gb/.test(low)) continue;
                const pe = c.querySelector(".a-price .a-offscreen") || c.querySelector(".a-price");
                const priceTxt = pe ? pe.innerText : "";
                const v = parseP(priceTxt);
                if (!v) continue;
                // Estrai componenti reali dal titolo
                const has = {
                    cpu: /7800x3d/.test(low),
                    ram64: /64\s?gb/.test(low),
                    mb: /mainboard|motherboard|x\d{3}|b\d{3}|z\d{3}|b650|z790|z870|x870|x670/i.test(low),
                };
                const href = "/dp/" + asin;
                return {asin, price: v, url: "https://www.amazon." + location.host.split(".")[1] + href,
                        title: title.slice(0,200), has};
            }
            return null;
        }''', require_ram_64)
        if not res:
            return None
        return {"price": res["price"], "currency": TLD_CURRENCY[tld],
                "url": f"https://www.amazon.{tld}/dp/{res['asin']}", "asin": res["asin"],
                "title": res.get("title", ""), "has": res.get("has", {})}
    except Exception as e:
        return {"error": str(e)[:120]}


# Combo candidate: keyword -> componenti del fai-da-te che sostituiscono.
# Usate solo se prezzo_bundle < somma dei singoli migliori prezzi.
# require_ram_64: il bundle deve dichiarare esplicitamente 64GB nel titolo.
COMBOS = [
    {"id": "CPU+MB", "query": "7800X3D Mainboard Bundle", "replaces": ["Ryzen 7 7800X3D", "MSI PRO B650-S WiFi"],
     "require_ram_64": False},
    {"id": "CPU+MB+RAM", "query": "7800X3D 64GB DDR5 Mainboard Bundle", "replaces": ["Ryzen 7 7800X3D", "ASUS Z790-A WiFi II", "DDR5 64GB 6000MHz"],
     "require_ram_64": True},
]

async def main():
    collected = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        log_event("scraper", status="start", n_components=len(COMPONENTS), n_tlds=len(EU_TLDS))
        for name, info in COMPONENTS.items():
            prices = {}
            for tld, label in EU_TLDS:
                t_start = time.time()
                log_event("scraper", status="scrape_start", tld=tld, component=name, asin=info["asin"])
                # --- Retry logic con rotazione UA ---
                from task_planner import should_retry, get_ua_pool, MAX_RETRIES
                ua_pool = get_ua_pool()
                r = None
                for attempt in range(MAX_RETRIES):
                    retry_ok, ua_idx = should_retry(tld, name, attempt)
                    if not retry_ok:
                        log_event("scraper", status="error", tld=tld, component=name,
                                  error="max_retries_exceeded", attempt=attempt)
                        break
                    ua = ua_pool[ua_idx] if ua_idx < len(ua_pool) else ua_pool[0]
                    try:
                        await page.set_extra_http_headers({
                            "Accept-Language": LANG_HEADERS[tld],
                            "User-Agent": ua,
                        })
                        r = await scrape_price(page, info["asin"], tld, label)
                        if r.get("available"):
                            dur = int((time.time() - t_start) * 1000)
                            log_event("scraper", status="ok", tld=tld, component=name,
                                      price=r["price"], currency=r["currency"], latency_ms=dur, attempt=attempt)
                            break
                        else:
                            dur = int((time.time() - t_start) * 1000)
                            log_event("scraper", status="warn", tld=tld, component=name,
                                      error=r.get("error", "no_price"), latency_ms=dur, attempt=attempt)
                    except Exception as e:
                        dur = int((time.time() - t_start) * 1000)
                        log_event("scraper", status="error", tld=tld, component=name,
                                  error=str(e)[:120], latency_ms=dur, attempt=attempt)
                        r = {"price": None,
                             "url": f"https://www.amazon.{tld}/dp/{info['asin']}",
                             "available": False, "error": str(e)[:120]}
                # Se fallisce tutto, logga l'esito definitivo
                if r and not r.get("available"):
                    prices[label] = r
                else:
                    prices[label] = r or {"price": None,
                        "url": f"https://www.amazon.{tld}/dp/{info['asin']}",
                        "available": False, "error": "unknown"}
            # Converte PLN -> EUR
            for label, pp in prices.items():
                if pp.get("price") is not None and pp.get("currency") == "PLN":
                    pp["price_eur"] = round(pp["price"] * PLN_TO_EUR, 2)
                else:
                    pp["price_eur"] = pp.get("price")
            collected.append((name, info["cat"], prices))
            n_ok = sum(1 for v in prices.values() if v.get("price_eur") is not None)
            print(f">>> {name}: {n_ok} prezzi EUR OK", flush=True)

        # --- Ricerca combo/bundle su Amazon (ASIN trovati a runtime, non fissi) ---
        combos_out = []
        # Usa il TLD DE per le combo (prezzi EUR, bundle frequenti)
        combo_tld = "de"
        combo_label = "Amazon.de"
        await page.set_extra_http_headers({"Accept-Language": LANG_HEADERS[combo_tld]})
        for c in COMBOS:
            try:
                r = await scrape_combo(page, c["query"], combo_tld, combo_label, c.get("require_ram_64", False))
                if r and r.get("price") is not None:
                    entry = {"id": c["id"], "query": c["query"],
                             "replaces": c["replaces"], "price": r["price"],
                             "currency": r["currency"], "url": r["url"], "asin": r.get("asin"),
                             "title": r.get("title", ""), "has": r.get("has", {})}
                    if r.get("currency") == "PLN":
                        entry["price_eur"] = round(r["price"] * PLN_TO_EUR, 2)
                    else:
                        entry["price_eur"] = r["price"]
                    combos_out.append(entry)
                    print(f">>> COMBO {c['id']}: €{entry['price_eur']} @ {r.get('asin')} | {r.get('title','')[:80]}", flush=True)
                else:
                    print(f">>> COMBO {c['id']}: nessun risultato valido (titolo non combaciante)", flush=True)
            except Exception as e:
                print(f">>> COMBO {c['id']} errore: {str(e)[:100]}", flush=True)
        await browser.close()

    # Costruisce il dict finale
    components = {}
    for name, cat, prices in collected:
        components[name] = {"category": cat, "prices": prices}
    # Preserva i pre-assemblati gia' presenti (li aggiorna prebuilt_scraper.py dopo)
    prev = {}
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH) as f:
                prev = json.load(f)
        except Exception:
            prev = {}
    result = {"updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              "sources": [l for _, l in EU_TLDS],
              "components": components, "combos": combos_out,
              "prebuilt": prev.get("prebuilt", []),
              "prebuilt_updated_at": prev.get("prebuilt_updated_at")}

    # Pulizia outlier: scarta prezzi che deviano >2.5x o <0.4x dalla mediana EUR
    for name, comp in result["components"].items():
        eur_vals = [v["price_eur"] for v in comp["prices"].values()
                    if v.get("price_eur") is not None]
        if len(eur_vals) >= 3:
            med = statistics.median(eur_vals)
            for v in comp["prices"].values():
                pe = v.get("price_eur")
                if pe is not None and (pe > med * 2.5 or pe < med * 0.4):
                    v["price_eur"] = None
                    v["outlier"] = True

    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(result, f, indent=2)
    os.replace(tmp, DATA_PATH)
    print(f"Salvato data.json con {len(result['components'])} componenti", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
