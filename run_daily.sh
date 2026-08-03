#!/bin/bash
# Pipeline giornaliera: scrape componenti -> deploy Vercel -> notifica Telegram
# Lanciato dal cronjob 2x/giorno (08:00 e 20:00).
set -e

cd /Users/riccardomoricone/telegram-bot-pc-components

# Pulisce eventuali processi phantom di scrape/Playwright rimasti da run precedenti
pkill -9 -f "scraper.py" 2>/dev/null || true
pkill -9 -f "chrome" 2>/dev/null || true
pkill -9 -f "headless" 2>/dev/null || true
sleep 2

PY=/Users/riccardomoricone/ev-bando-bot/.venv/bin/python

echo "== $(date) Avvio scrape componenti =="
$PY scraper.py

echo "== $(date) Scrape PC pre-assemblati (link dinamici) =="
$PY prebuilt_scraper.py

echo "== $(date) Deploy Vercel =="
npx vercel --prod --yes

echo "== $(date) Notifica Telegram =="
$PY bot_notify.py

echo "== $(date) DONE =="
