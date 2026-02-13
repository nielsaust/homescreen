#!/bin/bash

# Set the DISPLAY environment variable
export DISPLAY=:0

# Define log path and today's log file
log_path="/home/niels/homescreen/logs"
log_file_name="$(date +%Y-%m-%d).log"
log_file="${log_path}/${log_file_name}"

# Terminate any running instances of main.py
pkill -f main.py

# Start the application in the background
python3 /home/niels/homescreen/main.py &

# Wait briefly to ensure the app has started
sleep 2

# Tail the log file for today
tail -f "$log_file"