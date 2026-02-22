#!/usr/bin/env python3
import socket
import time
import hashlib
import os
import sys
import multiprocessing

# Library fallback: Use requests if available, otherwise use urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import json
    HAS_REQUESTS = False

if len(sys.argv) < 3:
    print("Error: Username and Mining Key are required!")
    sys.exit(1)

username = sys.argv[1]
mining_key = sys.argv[2]
device_name = sys.argv[4]

# Check if cores are provided, otherwise default to 2
if len(sys.argv) >= 4:
    try:
        CORES = int(sys.argv[3])
    except ValueError:
        CORES = 2
else:
    CORES = 2


# Safety check: Don't use more cores than available
CORES = min(CORES, multiprocessing.cpu_count())

if len(sys.argv) >= 5:
   device_name = sys.argv[4].strip().replace(" ", "_")
else:
    device_name = "Hassio-Miner"



def current_time():
    """Returns formatted local time."""
    return time.strftime("%H:%M:%S", time.localtime())

def fetch_pools():
    """Retrieves the best mining node from the Duino-Coin API."""
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
            # Retry after 15 seconds if pool fetching fails
            time.sleep(15)

def mine_worker(worker_id, user, key):
    """Main mining logic for a single CPU core."""
    while True:
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Connect to the selected mining node
            try:
                node_addr, node_port = fetch_pools()
            except:
                node_addr, node_port = "server.duinocoin.com", 2813
            
            soc.connect((str(node_addr), int(node_port)))
            # Server version check (optional)
            server_version = soc.recv(100).decode().strip()
            
            while True:
                # Request a JOB from the server
                soc.send(bytes(f"JOB,{user},LOW,{key}", encoding="utf8"))
                job_data = soc.recv(1024).decode().rstrip("\n")
                job = job_data.split(",")
                
                # Check for malformed job data
                if len(job) < 3:
                    continue
                
                expected_hash = job[1]
                difficulty = int(job[2])
                base_hash = hashlib.sha1(str(job[0]).encode("ascii"))
                
                start_time = time.time()
                
                # Hashing loop: Try numbers until hash matches expected result
                for result in range(100 * difficulty + 1):
                    temp_hash = base_hash.copy()
                    temp_hash.update(str(result).encode("ascii"))
                    ducos1 = temp_hash.hexdigest()

                    if expected_hash == ducos1:
                        end_time = time.time()
                        diff = max(end_time - start_time, 0.0001)
                        hashrate = result / diff

                        # Send result back to server with unique worker ID
                        soc.send(bytes(f"{result},{hashrate},{device_name}-Worker-{worker_id}", encoding="utf8"))
                        feedback = soc.recv(1024).decode().rstrip("\n")
                        
                        if feedback == "GOOD":
                            print(f"{current_time()} [Worker {worker_id}]: Accepted | {int(hashrate/1000)} kH/s | Diff: {difficulty}")
                        break 
        except Exception as e:
            # Wait 5s before reconnecting on network error
            time.sleep(5)
        finally:
            soc.close()

if __name__ == '__main__':
    # Support for multiprocessing in frozen/Docker environments
    multiprocessing.freeze_support()
    
    print(f"--- Duino-Coin Multicore Miner (Hassio) ---")
    print(f"User:      {username}")
    print(f"Threads:   {CORES}")
    print(f"Status:    Mining started...")
    print(f"-------------------------------------------")

    # Start the worker processes
    processes = []
    for i in range(CORES):
        p = multiprocessing.Process(target=mine_worker, args=(i + 1, username, mining_key))
        p.daemon = True
        p.start()
        processes.append(p)

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping miner...")
