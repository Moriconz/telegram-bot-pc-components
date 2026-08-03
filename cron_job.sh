#!/bin/bash
# Cron wrapper con task planner + retry logic
# Aggiungi a crontab con: crontab -e
# */10 8-23 * * * /Users/riccardomoricone/telegram-bot-pc-components/cron_job.sh

BOT_DIR="/Users/riccardomoricone/telegram-bot-pc-components"
PYTHON="/usr/bin/python3"
H=$(date +\%H)

# Step 1: Log tick start + chiedi al planner cosa fare
TASK=$(HOUR_OVERRIDE=$H $PYTHON -c "
import sys; sys.path.insert(0, '$BOT_DIR')
from task_planner import decide_next_task
task, ctx = decide_next_task()
if task:
    print(task)
else:
    print('idle')
" 2>/dev/null)

if [ "$TASK" = "idle" ]; then
    # Niente task da eseguire in questo momento
    exit 0
fi

# Log tick start
$PYTHON -c "
import sys; sys.path.insert(0, '$BOT_DIR')
from agent_log import log_event
log_event('cron', status='start', event='tick_start', hour=int('$H'), task='$TASK')
"

# Step 2: Esegui il task deciso dal planner
if [ "$TASK" = "bot_notify_morning" ] || [ "$TASK" = "morning_news" ]; then
    $PYTHON $BOT_DIR/bot_tasks.py morning_news
elif [ "$TASK" = "bot_notify_evening" ] || [ "$TASK" = "evening_news" ]; then
    $PYTHON $BOT_DIR/bot_tasks.py evening_news
elif [ "$TASK" = "scraper_eu" ]; then
    $PYTHON $BOT_DIR/scraper.py
elif [ "$TASK" = "scraper" ]; then
    $PYTHON $BOT_DIR/scraper.py
fi

EXIT_CODE=$?

# Step 3: Log tick end
$PYTHON -c "
import sys; sys.path.insert(0, '$BOT_DIR')
from agent_log import log_event
log_event('cron', status='end', event='tick_end', hour=int('$H'), task='$TASK', exit_code=$EXIT_CODE)
"

exit $EXIT_CODE