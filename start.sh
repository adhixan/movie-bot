#!/bin/bash
echo "🚀 Starting Telegram Movie Bot..."
gunicorn -w 1 -b 0.0.0.0:$PORT main:flask_app &
python main.py