#!/usr/bin/env python3
"""Genera PDF di esempio per il bot"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import mm
import io

def create_component_page(component_name: str, prices: list, output_path: str):
    """Crea pagina PDF per un componente"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Titolo
    title = Paragraph(f"<b>📊 Report: {component_name}</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 10))
    
    # Data
    from datetime import datetime
    date_p = Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
    story.append(date_p)
    story.append(Spacer(1, 20))
    
    # Tabella prezzi
    if prices:
        data = [['Fonte', 'Prezzo', 'Data', 'Link']]
        for p in prices:
            link = f'<a href="{p["url"]}">{p["source"]}</a>'
            data.append([p['source'], f"€{p['price']:.2f}", p['date'], link])
        
        table = Table(data, colWidths=[80*mm, 40*mm, 40*mm, 80*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
    
    story.append(PageBreak())
    
    # Grafico storico
    chart_title = Paragraph("<b>📈 Grafico Storico Prezzi</b>", styles['Heading2'])
    story.append(chart_title)
    story.append(Spacer(1, 10))
    
    if len(prices) >= 2:
        # Crea grafico semplice SVG inline
        dates = [p['date'] for p in prices[-10:]]
        vals = [p['price'] for p in prices[-10:]]
        
        min_p, max_p = min(vals), max(vals)
        r = max_p - min_p if max_p != min_p else 1
        
        points = []
        for i, v in enumerate(vals):
            x = 30 + (i / (len(vals)-1)) * 340
            y = 170 - ((v-min_p)/r) * 140
            points.append(f"{x},{y}")
        
        svg = f'''
        <div style="background:#1a1a2e;color:#eee;padding:15px;border-radius:10px;margin:10px 0;text-align:center;">
            <svg width="400" height="200" style="background:#111;">
                <polyline points="{' L '.join(points)}" fill="none" stroke="#00d4ff" stroke-width="2" stroke-linejoin="round"/>
                <circle cx="30" cy="170" r="4" fill="#ff6b6b"/>
                <circle cx="390" cy="30" r="4" fill="#4ecdc4"/>
            </svg>
            <div style="font-size:12px;color:#888;margin-top:5px;">
                Min: €{min_p:.2f} | Max: €{max_p:.2f} | Variazione: {((vals[-1]-vals[0])/vals[0]*100) if vals[0] else 0:.1f}%
            </div>
        </div>
        '''
        story.append(Paragraph(svg, styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    with open(output_path, 'wb') as f:
        f.write(buffer.getvalue())
    
    return output_path

def create_full_report(prices_by_component: dict):
    """Crea PDF completo con tutti i componenti"""
    os.makedirs('/Users/riccardomoricone/telegram-bot-pc-components/reports', exist_ok=True)
    
    all_prices = []
    
    for comp_name, prices in prices_by_component.items():
        output_path = f'/Users/riccardomoricone/telegram-bot-pc-components/reports/{comp_name.replace(" ", "_")}.pdf'
        create_component_page(comp_name, prices, output_path)
        all_prices.append(output_path)
    
    return all_prices

if __name__ == "__main__":
    # Dati di esempio
    sample_data = {
        "Intel Core i9-14900K": [
            {"source": "Amazon.it", "price": 549.99, "url": "https://amazon.it/i9-14900k", "date": "2026-07-31"},
            {"source": "EPrice.it", "price": 539.90, "url": "https://eprice.it/i9-14900k", "date": "2026-07-30"},
            {"source": "Amazon.it", "price": 559.90, "url": "https://amazon.it/i9-14900k", "date": "2026-07-29"},
        ],
        "NVIDIA RTX 4080 16GB": [
            {"source": "Amazon.it", "price": 1099.00, "url": "https://amazon.it/rtx4080", "date": "2026-07-31"},
            {"source": "EPrice.it", "price": 1079.90, "url": "https://eprice.it/rtx4080", "date": "2026-07-30"},
        ]
    }
    
    paths = create_full_report(sample_data)
    print(f"PDF creati: {paths}")