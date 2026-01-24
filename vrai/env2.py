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
global_lock = None 
mq = None
children_processes = []
drought_flag = Value('b', False)
view = None



def cleanup(signum, frame):
    current_pid = os.getpid()

    if current_pid == PARENT_PID:
        print(f"\n[ENV] Arrêt du serveur (Principal)...")
    else:
        sys.exit(0)

    # Terminer les enfants
    for p in children_processes:
        if isinstance(p, subprocess.Popen) or isinstance(p, Process):
            p.terminate()
    global view, shm
    if view is not None:
        view.release()
        view = None

    # Nettoyage SHM
    global shm
    if shm:
        shm.close()
        try: 
            shm.unlink()
            print("[ENV] Mémoire partagée supprimée.")
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

# thread d'accueil des animaux
def f(client_socket, address):
    with client_socket:
        try:
            msg = client_socket.recv(1024).decode('utf-8')
        except: return 

        # Le serveur accepte tout le monde, l'animal vérifiera lui-même s'il y a de la place dans la SHM
        response = {"status": "OK"}
        client_socket.sendall(json.dumps(response).encode('utf-8'))

# processus manager (météo et reproductions)
def environment_manager(drought_val):
    try:
        mgr_shm = shared_memory.SharedMemory(name=config.SHM_NAME)
        mgr_view = memoryview(mgr_shm.buf).cast('i')
        mgr_lock = sysv_ipc.Semaphore(config.SEM_KEY)
        mgr_mq = sysv_ipc.MessageQueue(config.MQ_KEY)
    except Exception as e:
        print(f"[MANAGER] Erreur lancement : {e}")
        return

    print("[MANAGER] Prêt à gérer l'écosystème.")
    last_growth = time.time()
    
    while True:

        stats = {"nbr_prey" : mgr_view[config.IDX_COUNT_PREY],
                 "nbr_predator" : mgr_view[config.IDX_COUNT_PREY],
                 "nbr_herbe" : mgr_view[config.IDX_HERBE]
                 }    

        mgr_mq.send(json.dumps(stats).encode(), type = 2)
        time.sleep(0.5)

        # gestion ressources via message queue
        try:
            message, t = mgr_mq.receive(block=False)
            msg = message.decode()
            if msg == "STOP":
                os.kill(os.getppid(), signal.SIGINT)
                break
            elif msg == "seche":
                with drought_val.get_lock():
                    drought_val.value = not drought_val.value
                    etat = "ACTIVÉE" if drought_val.value else "DÉSACTIVÉE"
            '''elif msg == "ADD_PROIE":
                subprocess.Popen([sys.executable, "prey.py"])
            elif msg == "ADD_PREDATOR":
                subprocess.Popen([sys.executable, "predator.py"])
            '''
        except sysv_ipc.BusyError:
            pass

        # gestion herbe
        if not drought_val.value and (time.time() - last_growth > 2.0):
            with mgr_lock:
                # on ajoute 10 unités d'herbe
                mgr_view[config.IDX_HERBE] += 10
            last_growth = time.time()
        
        time.sleep(0.1)
    mgr_view.release()
    mgr_shm.close()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    
    # calcul de la taille de la mémoire (1 case pour l'herbe, 2 pour chaque proie/prédateur)
    NB_ENTIERS = 1 + (config.MAX_PREY * 2) + (config.MAX_PREDATOR * 2)
    SIZE_IN_BYTES = NB_ENTIERS * 4 # 4 octets par entier

    # création mémoire et IPC
    try:
        global_lock = sysv_ipc.Semaphore(config.SEM_KEY, flags=sysv_ipc.IPC_CREX, initial_value=1)
    except sysv_ipc.ExistentialError:
        s = sysv_ipc.Semaphore(config.SEM_KEY)
        s.remove()
        global_lock = sysv_ipc.Semaphore(config.SEM_KEY, flags=sysv_ipc.IPC_CREX, initial_value=1)

    try:
        shm = shared_memory.SharedMemory(name=config.SHM_NAME, create=True, size=SIZE_IN_BYTES)
    except FileExistsError:
        t = shared_memory.SharedMemory(name=config.SHM_NAME)
        t.unlink()
        shm = shared_memory.SharedMemory(name=config.SHM_NAME, create=True, size=SIZE_IN_BYTES)

    # initialisation de la mémoire à 0
    view = memoryview(shm.buf).cast('i')
    for i in range(NB_ENTIERS):
        view[i] = 0

    try:
        mq = sysv_ipc.MessageQueue(config.MQ_KEY, flags=sysv_ipc.IPC_CREX)
    except sysv_ipc.ExistentialError:
        q = sysv_ipc.MessageQueue(config.MQ_KEY)
        q.remove()
        mq = sysv_ipc.MessageQueue(config.MQ_KEY, flags=sysv_ipc.IPC_CREX)

    # lancement des sous-processus
    p_manager = Process(target=environment_manager, args=(drought_flag,))
    p_manager.start()
    children_processes.append(p_manager)

    print(f"[ENV] Serveur écoute sur {config.PORT}...")
    print(f"[ENV] Taille Mémoire: {SIZE_IN_BYTES} octets ({NB_ENTIERS} emplacements)")
    
    # serveur sockets
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
        except KeyboardInterrupt:
            cleanup(None, None)