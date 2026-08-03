#!/usr/bin/env python3
"""
Confronto prezzi: PC assemblato vs pre-built
"""

import json
from datetime import datetime

# Componenti target (ispirati al PC gaming originale ma diversi)
COMPONENTS_CONFIG = {
    "cpu": {
        "name": "Intel Core i9-14900K",
        "target_min": 500,
        "target_max": 600,
        "alternatives": [
            {"name": "AMD Ryzen 9 7950X", "price": 599.99, "url": "https://amazon.it/ryzen9-7950x"},
            {"name": "Intel Core i7-14700K", "price": 419.99, "url": "https://amazon.it/i7-14700k"},
        ]
    },
    "gpu": {
        "name": "NVIDIA RTX 4080 16GB",
        "target_min": 1000,
        "target_max": 1200,
        "alternatives": [
            {"name": "NVIDIA RTX 4070 Ti 12GB", "price": 799.99, "url": "https://amazon.it/rtx4070ti"},
            {"name": "AMD Radeon RX 7900 XTX", "price": 999.99, "url": "https://amazon.it/rx7900xtx"},
        ]
    },
    "ram": {
        "name": "DDR5 64GB Kit (2x32GB) 5600MHz",
        "target_min": 300,
        "target_max": 400,
        "alternatives": [
            {"name": "DDR5 32GB Kit (2x16GB) 6000MHz", "price": 179.99, "url": "https://amazon.it/ddr5-32gb"},
            {"name": "DDR5 64GB Kit 6000MHz", "price": 349.99, "url": "https://amazon.it/ddr5-64gb-6000"},
        ]
    },
    "ssd": {
        "name": "SSD 2TB NVMe PCIe 4.0",
        "target_min": 150,
        "target_max": 200,
        "alternatives": [
            {"name": "SSD 2TB Samsung 980 PRO", "price": 189.99, "url": "https://amazon.it/samsung-980pro"},
            {"name": "SSD 2TB WD Black SN850", "price": 179.99, "url": "https://amazon.it/wd-black-sn850"},
        ]
    },
    "motherboard": {
        "name": "Motherboard Z790 ATX",
        "target_min": 250,
        "target_max": 350,
        "alternatives": [
            {"name": "MSI MAG Z790 TOMAHAWK", "price": 299.99, "url": "https://amazon.it/msi-z790"},
            {"name": "ASUS ROG STRIX Z790-E", "price": 349.99, "url": "https://amazon.it/asus-z790-e"},
        ]
    },
    "psu": {
        "name": "Alimentatore 1000W 80+ Gold",
        "target_min": 150,
        "target_max": 200,
        "alternatives": [
            {"name": "Corsair RM1000x 1000W", "price": 179.99, "url": "https://amazon.it/corsair-rm1000x"},
            {"name": "Seasonic Focus GX-1000", "price": 159.99, "url": "https://amazon.it/seasonic-gx"},
        ]
    }
}

# Pre-built PC (ispirati al modello originale)
PREBUILT_PCS = [
    {
        "name": "PC Gaming i9-14900K RTX 4080 32GB 2TB",
        "price": 2899.99,
        "url": "https://example.it/prebuilt1",
        "source": "Vendor A",
        "components": ["i9-14900K", "RTX 4080", "32GB DDR5", "2TB SSD"]
    },
    {
        "name": "PC Gaming Ryzen 9 7950X RTX 4070 Ti 64GB 2TB",
        "price": 2799.99,
        "url": "https://example.it/prebuilt2",
        "source": "Vendor B",
        "components": ["Ryzen 9 7950X", "RTX 4070 Ti", "64GB DDR5", "2TB SSD"]
    },
    {
        "name": "Workstation i9-14900K RTX 4080 64GB 4TB",
        "price": 3499.99,
        "url": "https://example.it/prebuilt3",
        "source": "Vendor C",
        "components": ["i9-14900K", "RTX 4080", "64GB DDR5", "4TB SSD"]
    }
]

def calculate_build_price() -> dict:
    """Calcola prezzo totale componenti"""
    total = 0
    components = {}
    
    # Usa prezzi target medi
    for comp_type, comp_info in COMPONENTS_CONFIG.items():
        price = (comp_info["target_min"] + comp_info["target_max"]) / 2
        components[comp_type] = {
            "name": comp_info["name"],
            "price": price
        }
        total += price
    
    return {"total": total, "components": components}

def compare_with_prebuilt() -> str:
    """Genera confronto"""
    build = calculate_build_price()
    
    report = []
    report.append(f"<b>📊 CONFRONTO: PC Assemblato vs Pre-built</b>")
    report.append(f"<i>{datetime.now().strftime('%d/%m/%Y')}</i>")
    report.append("")
    
    # Totale assemblato
    report.append(f"<b>💻 PC Assemblato (componenti individuali):</b>")
    report.append(f"   <b>Totale: €{build['total']:.2f}</b>")
    report.append("")
    
    # Pre-built
    report.append(f"<b>🖥️ PC Pre-built disponibili:</b>")
    for pc in PREBUILT_PCS:
        savings = pc["price"] - build["total"]
        diff_pct = (savings / build["total"] * 100) if build["total"] > 0 else 0
        
        report.append(f"   {pc['name']}")
        report.append(f"   Prezzo: €{pc['price']:.2f} - <a href='{pc['url']}'>{pc['source']}</a>")
        if savings > 0:
            report.append(f"   <b>✅ Risparmi €{savings:.2f} ({diff_pct:.1f}% meno)</b>")
        else:
            report.append(f"   <b>❌ Costa €{abs(savings):.2f} in più</b>")
        report.append("")
    
    # Consiglio
    report.append("<b>💡 CONSIGLIO:</b>")
    if build["total"] < min(p["price"] for p in PREBUILT_PCS):
        report.append("   Assemblerai tu PC è più conveniente!")
    else:
        cheapest = min(PREBUILT_PCS, key=lambda x: x["price"])
        report.append(f"   Il pre-built più economico è: {cheapest['name']}")
        report.append(f"   Confronta i componenti e verifica affidabilità venditori")
    
    return "\n".join(report)

if __name__ == "__main__":
    print(compare_with_prebuilt())