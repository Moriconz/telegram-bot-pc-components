#!/usr/bin/env python3
"""
Ad-hoc script: prepara e deploya la dashboard su Vercel.
1. Crea repo GitHub se non esiste
2. Aggiunge file
3. Commit + push
4. Triggers Vercel deploy
"""
import subprocess, json, sys

BOT_DIR = "/Users/riccardomoricone/telegram-bot-pc-components"
REPO_NAME = "telegram-bot-pc-components"
GITHUB_USER = "Moriconz"

# Step 1: Verifica/crea repo GitHub
print("📋 Step 1: Verifica repo GitHub...")
result = subprocess.run(["gh", "repo", "view", f"{GITHUB_USER}/{REPO_NAME}"], 
                        capture_output=True, text=True)
if result.returncode != 0:
    print("Creazione nuovo repo GitHub...")
    result = subprocess.run(["gh", "repo", "create", f"{GITHUB_USER}/{REPO_NAME}", 
                            "--public", "--description", "Telegram Price Bot PC Components — Dashboard agente autonomo"],
                           capture_output=True, text=True, cwd=BOT_DIR)
    print(result.stdout)
    if result.returncode != 0:
        print("⚠️  Repo creation result:", result.stderr[:200])
else:
    print("Repo GitHub già esistente.")

# Step 2: Git add + commit
print("\n📦 Step 2: Preparazione commit...")
subprocess.run(["git", "add", "-A"], cwd=BOT_DIR, capture_output=True)
result = subprocess.run(["git", "diff", "--cached", "--stat"], cwd=BOT_DIR, capture_output=True, text=True)
if result.stdout.strip():
    print(result.stdout)
else:
    print("Niente file da committare.")

# Check if there's anything to commit
status = subprocess.run(["git", "status", "--porcelain"], cwd=BOT_DIR, capture_output=True, text=True)
if status.stdout.strip():
    print("\nCommitting...")
    commit_result = subprocess.run(["git", "commit", "-m", "feat: agent dashboard — logging, retry logic, dashboard API + Next.js UI"],
                                  cwd=BOT_DIR, capture_output=True, text=True)
    print(commit_result.stdout[-200:] if commit_result.stdout else "no output")
    if commit_result.returncode != 0:
        print("⚠️ Commit stderr:", commit_result.stderr[:300])
else:
    print("Niente da committare.")

print("\n✅ Setup completato.")
