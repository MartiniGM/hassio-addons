#!/usr/bin/env bash
set -e

# Fetching options from Home Assistant config
USER=$(bashio::config 'username')
KEY=$(bashio::config 'mining_key')
CORES=$(bashio::config 'cores')

echo "Starting Duino-Coin miner for $USER with $CORES threads..."

# This line sends the arguments to miner.py
python3 /app/miner.py "$USER" "$KEY" "$CORES"
