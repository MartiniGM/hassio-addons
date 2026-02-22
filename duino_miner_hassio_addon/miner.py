#!/usr/bin/env python3
import socket
import time
import hashlib
import os
import sys
import multiprocessing

# Fallback for biblioteker
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import json
    HAS_REQUESTS = False

# --- ARGUMENT HÅNDTERING ---
# Forventer: python3 script.py brukernavn mining_key
if len(sys.argv) < 3:
    print("Feil: Mangler argumenter.")
    print("Bruk: python3 script.py <brukernavn> <mining_key>")
    sys.exit(1)

script_name = sys.argv[0]
username = sys.argv[1]
mining_key = sys.argv[2]

# Bruk alle kjerner minus 1 for å spare systemressurser til Hassio
CORES = max(1, multiprocessing.cpu_count() - 1)

def current_time():
    return time.strftime("%H:%M:%S", time.localtime())

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
            time.sleep(15)

def mine_worker(worker_id, user, key):
    """Hashing-prosess for en enkelt CPU-kjerne"""
    while True:
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Hent pool og koble til
            try:
                node_addr, node_port = fetch_pools()
            except:
                node_addr, node_port = "server.duinocoin.com", 2813
            
            soc.connect((str(node_addr), int(node_port)))
            server_version = soc.recv(100).decode().strip()
            
            while True:
                # Be om jobb (bruker "LOW" diff for Hassio/CPU)
                soc.send(bytes(f"JOB,{user},LOW,{key}", encoding="utf8"))
                job_data = soc.recv(1024).decode().rstrip("\n")
                job = job_data.split(",")
                
                if len(job) < 3: continue
                
                expected_hash = job[1]
                difficulty = int(job[2])
                base_hash = hashlib.sha1(str(job[0]).encode("ascii"))
                
                start_time = time.time()
                
                # Selve mining-loopen
                for result in range(100 * difficulty + 1):
                    temp_hash = base_hash.copy()
                    temp_hash.update(str(result).encode("ascii"))
                    ducos1 = temp_hash.hexdigest()

                    if expected_hash == ducos1:
                        end_time = time.time()
                        diff = max(end_time - start_time, 0.0001)
                        hashrate = result / diff

                        # Send resultat med unikt worker-navn
                        soc.send(bytes(f"{result},{hashrate},Hassio-MC-Worker-{worker_id}", encoding="utf8"))
                        feedback = soc.recv(1024).decode().rstrip("\n")
                        
                        if feedback == "GOOD":
                            print(f"{current_time()} [{worker_id}]: Share akseptert | {int(hashrate/1000)} kH/s")
                        break 
        except Exception as e:
            time.sleep(5)
        finally:
            soc.close()

if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    print(f"--- Duino-Coin Multicore Miner ---")
    print(f"Brukernavn: {username}")
    print(f"Kjerner:    {CORES}")
    print(f"----------------------------------")

    processes = []
    for i in range(CORES):
        # Vi sender med username og key til hver prosess
        p = multiprocessing.Process(target=mine_worker, args=(i + 1, username, mining_key))
        p.daemon = True
        p.start()
        processes.append(p)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopper miner...")
