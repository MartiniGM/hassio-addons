#!/usr/bin/env python3
import socket
import time
import hashlib
import os
import sys
import multiprocessing

from sys import argv

# Prøver å importere requests, bruker urllib som fallback for maksimal kompatibilitet
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import json
    HAS_REQUESTS = False

# --- KONFIGURASJON ---
script, username, mining_key = argv

# Bruker alle tilgjengelige kjerner minus 1 (for å ikke låse hele systemet)
CORES = max(1, multiprocessing.cpu_count() - 1) 

def fetch_pools():
    url = "https://server.duinocoin.com/getPool"
    while True:
        try:
            if HAS_REQUESTS:
                resp = requests.get(url, timeout=10).json()
                return resp["ip"], resp["port"]
            else:
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    return data["ip"], data["port"]
        except Exception:
            print(f"{current_time()}: Kunne ikke hente pool, prøver igjen om 15s...")
            time.sleep(15)

def current_time():
    return time.strftime("%H:%M:%S", time.localtime())

def mine_worker(worker_id, user, key, devicename):
    """Denne funksjonen kjører på en egen CPU-kjerne"""
    print(f"[{worker_id}] Kjerne startet.")
    
    while True:
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Finn beste server
            node_addr, node_port = fetch_pools()
            soc.connect((str(node_addr), int(node_port)))
            server_version = soc.recv(100).decode().strip()
            
            while True:
                # Be om jobb
                soc.send(bytes(f"JOB,{user},LOW,{key}", encoding="utf8"))
                job_data = soc.recv(1024).decode().rstrip("\n")
                job = job_data.split(",")
                
                if len(job) < 3:
                    continue
                
                expected_hash = job[1]
                difficulty = int(job[2])
                base_hash = hashlib.sha1(str(job[0]).encode("ascii"))
                
                start_time = time.time()
                
                # Hashing-loop
                for result in range(100 * difficulty + 1):
                    temp_hash = base_hash.copy()
                    temp_hash.update(str(result).encode("ascii"))
                    ducos1 = temp_hash.hexdigest()

                    if expected_hash == ducos1:
                        end_time = time.time()
                        diff = end_time - start_time
                        hashrate = result / max(diff, 0.0001)

                        # Send resultat
                        soc.send(bytes(f"{result},{hashrate},Hassio-MC-Worker-{worker_id}", encoding="utf8"))
                        feedback = soc.recv(1024).decode().rstrip("\n")
                        
                        if feedback == "GOOD":
                            print(f"{current_time()} [{worker_id}]: Godkjent share | {int(hashrate/1000)} kH/s | Diff: {difficulty}")
                        elif feedback == "BAD":
                            print(f"{current_time()} [{worker_id}]: Avvist share (BAD)")
                        
                        break # Gå til neste jobb
        except Exception as e:
            print(f"{current_time()} [{worker_id}]: Feil oppsto: {e}. Starter på nytt om 5s...")
            time.sleep(5)
        finally:
            soc.close()

if __name__ == '__main__':
    # Fix for Windows/Docker miljöer
    multiprocessing.freeze_support()
    
    # Sjekk om brukernavn er satt
    if USERNAME == "ditt_brukernavn":
        print("FEIL: Vennligst endre USERNAME i koden!")
        sys.exit()

    print(f"--- Duino-Coin Multicore Miner for Hassio ---")
    print(f"Kjerner i bruk: {CORES}")
    print(f"Brukernavn: {USERNAME}")
    print(f"----------------------------------------------")

    processes = []
    for i in range(CORES):
        p = multiprocessing.Process(
            target=mine_worker, 
            args=(i + 1, USERNAME, MINING_KEY, DEVICE_NAME)
        )
        p.daemon = True
        p.start()
        processes.append(p)

    try:
        # Holder hovedprogrammet i gang
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Miner stopper...")
