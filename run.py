#!/usr/bin/env python3
"""
Script di avvio rapido per il bot Telegram
"""

import os
import sys
import subprocess
import time
import signal

BOT_DIR = "/Users/riccardomoricone/telegram-bot-pc-components"
PID_FILE = f"{BOT_DIR}/scheduler.pid"

def start_scheduler():
    """Avvia lo scheduler in background"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            print(f"Scheduler già in esecuzione (PID: {pid})")
            return
        except OSError:
            os.remove(PID_FILE)
    
    pid = os.fork()
    if pid == 0:
        # Child process
        os.setsid()
        os.chdir(BOT_DIR)
        os.system(f"python3 {BOT_DIR}/scheduler.py")
    else:
        # Parent process
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
        print(f"Scheduler avviato (PID: {pid})")
        print("Controlla i log in: bot.log")

def stop_scheduler():
    """Ferma lo scheduler"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            os.remove(PID_FILE)
            print(f"Scheduler fermato (PID: {pid})")
        except OSError:
            print("Scheduler non in esecuzione")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
    else:
        print("Nessun scheduler in esecuzione")

def status():
    """Mostra stato del bot"""
    print("\n=== Stato Bot Telegram ===\n")
    
    # Database
    if os.path.exists(f"{BOT_DIR}/prices.db"):
        import sqlite3
        conn = sqlite3.connect(f"{BOT_DIR}/prices.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM prices")
        count = c.fetchone()[0]
        conn.close()
        print(f"📊 Prezzi salvati: {count}")
    
    # Reports
    reports_dir = f"{BOT_DIR}/reports"
    if os.path.exists(reports_dir):
        files = os.listdir(reports_dir)
        print(f"📄 PDF generati: {len(files)}")
    
    # Process
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = f.read().strip()
        print(f"🚀 Scheduler attivo: PID {pid}")
    else:
        print("⏹️ Scheduler fermo")
    
    print()

def send_test():
    """Invia messaggio di test"""
    from simple_bot import send_message
    send_message("<b>🧪 Test Bot</b>\nIl bot funziona correttamente!")
    print("Messaggio di test inviato")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 run.py [start|stop|status|test]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "start":
        start_scheduler()
    elif cmd == "stop":
        stop_scheduler()
    elif cmd == "status":
        status()
    elif cmd == "test":
        send_test()
    else:
        print(f"Comando sconosciuto: {cmd}")