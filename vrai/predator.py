import socket, sysv_ipc, subprocess, sys, random, time, os, signal, json
from multiprocessing import shared_memory
import config
import utils

def initialisation_processus():
    if len(sys.argv) > 2:
        h, r = float(sys.argv[1]), float(sys.argv[2])
    else:
        h, r = config.DEFAULT_H_PREDATOR, config.DEFAULT_R_PREDATOR

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((config.HOST, config.PORT))
        s.sendall("PREDATOR".encode())
        response = json.loads(s.recv(1024).decode())
        if response.get("status") == "FULL":
            sys.exit(0)
            
    return os.getpid(), h, r

my_id, my_h, my_r = initialisation_processus()

shm = shared_memory.SharedMemory(name=config.SHM_NAME)
utils.fix_tracker(shm)
sem = sysv_ipc.Semaphore(config.SEM_KEY)
view = memoryview(shm.buf).cast('i')

try: mq = sysv_ipc.MessageQueue(config.MQ_KEY)
except: mq = None

energie = config.INITIAL_ENERGY
alive = True
my_index = -1

try:
    # 1. NAISSANCE
    with sem:
        max_idx = config.IDX_PREDATOR_START + (config.MAX_PREDATOR * 2)
        for i in range(config.IDX_PREDATOR_START, max_idx, 2):
            if view[i] == 0:
                view[i] = my_id
                view[i+1] = config.ETAT_ACTIF
                my_index = i
                break
                
    if my_index == -1: sys.exit(0)

    # 2. BOUCLE DE VIE
    while alive:
        energie -= config.COUT_VIE

        if energie <= 0:
            print(f"[{my_id}] Loup mort de faim.")
            break

        # A. CHASSE (Trouver et tuer une proie active)
        if energie < my_h:
            with sem:
                view[my_index+1] = config.ETAT_ACTIF
                
                # Cherche une proie active
                cible_pid = -1
                for i in range(config.IDX_PREY_START, config.IDX_PREDATOR_START, 2):
                    if view[i] != 0 and view[i+1] == config.ETAT_ACTIF:
                        cible_pid = view[i]
                        break # Cible verrouillée !
                        
            # Envoi du coup de grâce (Hors du verrou pour ne pas bloquer)
            if cible_pid != -1:
                try:
                    os.kill(cible_pid, signal.SIGTERM) # <--- LE CHOC IPC
                    energie += config.GAIN_NOURRITURE
                    print(f"[{my_id}] J'ai mangé la proie {cible_pid} !")
                except ProcessLookupError: pass # La proie était déjà morte

        # B. REPRODUCTION
        else:
            with sem: view[my_index+1] = config.ETAT_PASSIF
            if energie >= my_r and mq:
                try:
                    mq.send("ADD_PREDATOR".encode())
                    energie -= config.COUT_REPRODUCTION
                    print(f"[{my_id}] Reproduction !")
                except sysv_ipc.BusyError: pass

        time.sleep(config.VITESSE_SIMU)

finally:
    # 3. NETTOYAGE
    if my_index != -1:
        with sem:
            view[my_index] = 0
            view[my_index+1] = config.ETAT_MORT
            
    view.release()
    shm.close()