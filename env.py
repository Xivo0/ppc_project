from multiprocessing import Process, shared_memory, Value
import socket
import sysv_ipc
import signal
import sys
import random
import time
import json
import subprocess
import os
from threading import Thread

import config
import utils

PARENT_PID = os.getpid()
shm = None
global_lock = None # semaphore utiliser comme un lock plutard
mq = None
children_processes = []
drought_flag = Value('b', False)


def cleanup(signum, frame):
    current_pid = os.getpid()

    if current_pid == PARENT_PID:
        print(f"\n[ENV] Arrêt du serveur (Principal)...")
    else:
        sys.exit(0)

    global stats_view
    if 'stats_view' in globals():
        try:
            stats_view.release()
        except: pass

    # Terminer les enfants
    for p in children_processes:
        if isinstance(p, subprocess.Popen) or isinstance(p, Process):
            p.terminate()

    # Nettoyage SHM
    global shm
    if shm:
        shm.close()
        try: 
            shm.unlink()
            print("[ENV] Mémoire partagée supprimée.")
        except: pass
    # Nettoyage de la SHM des stats
    try:
        s_stats = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME)
        s_stats.close()
        s_stats.unlink()
    except: pass

    # Nettoyage Lock
    global global_lock
    if global_lock:
        try: global_lock.remove()
        except: pass

    # Nettoyage MQ
    global mq
    if mq:
        try: mq.remove()
        except: pass

    sys.exit(0)


def f(client_socket, address):
    current_shm = None
    try:
        current_shm = shared_memory.SharedMemory(name=config.SHM_NAME)
        # On utilise le Lock Système
        current_lock = sysv_ipc.Semaphore(config.SEM_KEY)
    

        with client_socket:
            # 1. ÉTAPE DE RÉCEPTION DU TYPE
            # On attend que le client dise "Je suis un PREDATOR" ou "Je suis une PREY"
            try:
                msg = client_socket.recv(1024).decode('utf-8')
            except:
                return # Erreur de lecture

            # Détermination de la valeur numérique à écrire
            if "PREDATOR" in msg:
                val_type = config.PREDATEUR
            else:
                val_type = config.PROIE

            rx, ry = -1, -1 # Par défaut -1 si pas de place trouvée
            
            # 2. SECTION CRITIQUE (Recherche + Écriture)
            with current_lock:
                for _ in range(100): # 100 tentatives
                    tx = random.randint(0, config.MAP_SIZE - 1)
                    ty = random.randint(0, config.MAP_SIZE - 1)
                    idx = utils.to_idx((tx, ty))
                    
                    # Si la case est vide (0) ou herbe (1), on peut s'y installer
                    # Attention : on suppose que PROIE(10) et PREDATEUR(20) sont > HERBE(1)
                    if current_shm.buf[idx] <= config.HERBE:
                        rx, ry = tx, ty
                        
                        # C'EST ICI LA CLÉ : On inscrit l'animal tout de suite !
                        # On fait += pour garder l'herbe s'il y en a (ex: 1 + 10 = 11 -> Proie sur herbe)
                        current_shm.buf[idx] += val_type
                        break

            if rx != -1:
                # On détermine le type en string pour utils
                type_str = "PREDATOR" if val_type == config.PREDATEUR else "PREY"
                # ON AJOUTE +1
                utils.update_counts(current_lock, type_str, 1)
                
                # 3. RÉPONSE
                response = {
                    "start_x": rx,
                    "start_y": ry,
                    "map_size": config.MAP_SIZE
                }
                client_socket.sendall(json.dumps(response).encode('utf-8'))

    finally:
        if current_shm:
            current_shm.close()


def environment_manager(drought_val):
    try:
        mgr_shm = shared_memory.SharedMemory(name=config.SHM_NAME)
        mgr_lock = sysv_ipc.Semaphore(config.SEM_KEY)
        mgr_mq = sysv_ipc.MessageQueue(config.MQ_KEY)
    except:
        return

    print("[MANAGER] Prêt à recevoir des commandes.")
    last_growth = time.time()
    
    while True:
        # A. GESTION DES COMMANDES (ADD_PROIE, STOP, etc.)
        try:
            message, t = mgr_mq.receive(block=False)
            msg = message.decode()
            print(f"[MANAGER] Commande reçue : {msg}")

            if msg == "STOP":
                os.kill(os.getppid(), signal.SIGINT)
                break
            
            elif msg == "ADD_PROIE":
                # On lance une nouvelle proie indépendante
                subprocess.Popen([sys.executable, "prey.py"])
            
            elif msg == "ADD_PREDATOR":
                # On lance un nouveau prédateur indépendant
                subprocess.Popen([sys.executable, "predator.py"])

        except sysv_ipc.BusyError:
            pass # Pas de message

        # B. GESTION DE LA NATURE
        if not drought_val.value and (time.time() - last_growth > 2.0):
            # [LOCK] On verrouille pendant que l'herbe pousse
            with mgr_lock:
                for _ in range(5):
                    idx = random.randint(0, (config.MAP_SIZE**2) - 1)
                    if mgr_shm.buf[idx] == config.VIDE:
                        mgr_shm.buf[idx] = config.HERBE
            last_growth = time.time()
        
        time.sleep(0.1)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    
    # 1. Création Lock (Semaphore binaire)
    try:
        global_lock = sysv_ipc.Semaphore(config.SEM_KEY, flags=sysv_ipc.IPC_CREX, initial_value=1)
    except sysv_ipc.ExistentialError:
        s = sysv_ipc.Semaphore(config.SEM_KEY)
        s.remove()
        global_lock = sysv_ipc.Semaphore(config.SEM_KEY, flags=sysv_ipc.IPC_CREX, initial_value=1)

    # 2. Création SHM
    try:
        shm = shared_memory.SharedMemory(name=config.SHM_NAME, create=True, size=config.MAP_SIZE**2)
    except FileExistsError:
        t = shared_memory.SharedMemory(name=config.SHM_NAME)
        t.unlink()
        shm = shared_memory.SharedMemory(name=config.SHM_NAME, create=True, size=config.MAP_SIZE**2)

    for i in range(config.MAP_SIZE**2):
        shm.buf[i] = config.HERBE if random.random() < 0.5 else config.VIDE

    try:
        # 8 octets = 2 entiers de 4 octets
        shm_stats = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME, create=True, size=8)
    except FileExistsError:
        t = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME)
        t.unlink()
        shm_stats = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME, create=True, size=8)
    
    # On met tout à 0 au début
    stats_view = memoryview(shm_stats.buf).cast('i')
    stats_view[0] = 0
    stats_view[1] = 0

    # 3. Création MQ
    try:
        mq = sysv_ipc.MessageQueue(config.MQ_KEY, flags=sysv_ipc.IPC_CREX)
    except sysv_ipc.ExistentialError:
        q = sysv_ipc.MessageQueue(config.MQ_KEY)
        q.remove()
        mq = sysv_ipc.MessageQueue(config.MQ_KEY, flags=sysv_ipc.IPC_CREX)

    # 4. Lancement Manager
    p_manager = Process(target=environment_manager, args=(drought_flag,))
    p_manager.start()
    children_processes.append(p_manager)

    # 6. Boucle Serveur
    print(f"[ENV] Serveur écoute sur {config.PORT}...")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((config.HOST, config.PORT))
        server_socket.listen(10)
        
        try:
            while True:
                client_socket, address = server_socket.accept()
                t = Thread(target=f, args=(client_socket, address))
                t.daemon = True
                t.start()
                print(f"coucou connexion")
        except KeyboardInterrupt:
            cleanup(None, None)
