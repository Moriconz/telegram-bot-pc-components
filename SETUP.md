# Setup Bot Telegram - Monitoraggio Componenti PC

## 📦 Installazione Rapida

```bash
# 1. Installa dipendenze
pip3 install requests beautifulsoup4 lxml reportlab

# 2. Crea cartella reports
mkdir -p reports

# 3. Avvia scheduler
python3 scheduler.py
```

## 🚀 Avvio Bot

### Modalità Interattiva (consigliata)
```bash
python3 scheduler.py
```
Invia notizie alle 08:00 e 20:00

### Modalità Manuale
```bash
# Notizie mattutine
python3 bot_tasks.py morning_news

# Notizie serali  
python3 bot_tasks.py evening_news

# Test connessione
python3 simple_bot.py
```

## 📊 Componenti Monitorati

- **CPU**: Intel Core i9-14900K (€500-600)
- **GPU**: NVIDIA RTX 4080 16GB (€1000-1200)
- **RAM**: DDR5 64GB Kit (€300-400)
- **SSD**: 2TB NVMe PCIe 4.0 (€150-200)
- **Motherboard**: Z790 ATX (€250-350)
- **PSU**: 1000W 80+ Gold (€150-200)
- **Case**: Mid Tower (€100-150)

## 📁 File Principali

| File | Descrizione |
|------|-------------|
| `scheduler.py` | Scheduler 2x al giorno |
| `simple_bot.py` | Codice principale bot |
| `bot_tasks.py` | Task separati |
| `generate_pdf.py` | Generazione PDF |
| `compare_builds.py` | Confronto PC assemblato/pre-built |
| `index.html` | Dashboard web |
| `prices.db` | Database prezzi |

## 🤖 Bot Configurato

- **Token**: 8932041955:AAETap342SJ1EmqlK3s_Mo2PLqtJw1QvWJY
- **Chat ID**: 508375146
- **Username**: @ComponentiPCconIA_bot

## 📈 Output Bot

1. **Notizie mattutine (08:00)**:
   - Nuovi prezzi trovati
   - Link ai prodotti
   - Storico prezzi

2. **Notizie serali (20:00)**:
   - Confronto prezzi giorno
   - Consigli acquisto
   - PDF con grafici

## 🔧 Personalizzazione

Modifica `simple_bot.py` per:
- Aggiungere componenti
- Cambiare range di prezzo
- Aggiungere fonti

## 🛠️ Risoluzione Problemi

```bash
# Verifica bot
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Verifica database
sqlite3 prices.db "SELECT COUNT(*) FROM prices"

# Log
tail -f bot.log
```