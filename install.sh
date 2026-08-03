#!/bin/bash
# Installazione dipendenze per il bot Telegram
set -e

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo "Creating directories..."
mkdir -p reports

echo "Initializing database..."
python3 -c "
import sys
sys.path.insert(0, '.')
from bot_tasks import *
init_db()
print('Database initialized')
"

echo "Testing bot connection..."
python3 bot_tasks.py send_startup_message

echo "Installation complete!"
echo ""
echo "To start the scheduler:"
echo "  python3 scheduler.py"
echo ""
echo "Or run specific tasks manually:"
echo "  python3 bot_tasks.py morning_news"
echo "  python3 bot_tasks.py evening_news"