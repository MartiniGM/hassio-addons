#!/usr/bin/with-contenv bashio

# Hent variabler fra menyen
USER=$(bashio::config 'username')
KEY=$(bashio::config 'mining_key')
CORES=$(bashio::config 'cores')
MINER=$(bashio::config 'miner_name')

echo "Starting miner for $USER on $CORES cores..."

# Start python-skriptet
python3 miner.py "$USER" "$KEY" "$CORES" "$MINER"
