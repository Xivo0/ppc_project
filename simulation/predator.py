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
        idx = response.get("idx")    
    return os.getpid(), h, r, idx

my_id, my_h, my_r, my_index = initialisation_processus()

shm = shared_memory.SharedMemory(name=config.SHM_NAME)
utils.fix_tracker(shm)
sem = sysv_ipc.Semaphore(config.SEM_KEY)
view = memoryview(shm.buf).cast('i')

try: mq = sysv_ipc.MessageQueue(config.MQ_KEY)
except: mq = None

energie = config.INITIAL_ENERGY_PREDATOR
alive = True

active = False # permet de garder en mémoire si animal actif ou pas
is_registered = False # si jamais processeur meurt/crée erreur avant d'initialiser sa place pour le "finally"

try:
    # naissance
    with sem:
        view[my_index] = my_id
        view[my_index+1] = config.ETAT_PASSIF
        view[config.IDX_COUNT_PREDATOR] += 1
        is_registered = True

    # boucle de vie
    while alive:
        energie -= config.COUT_VIE

        if energie <= 0:
            print(f"[{my_id}] Loup mort de faim.")
            break

        # chasse (tue proie active)
        if energie < my_h:
            with sem:
                if not active:
                    view[config.IDX_COUNT_ACTIVE_PREDATOR] +=1
                    view[my_index+1] = config.ETAT_ACTIF
                    active = True
                
                # cherche proie active
                cible_pid = -1
                for i in range(config.IDX_PREY_START, config.IDX_PREDATOR_START, 2):
                    if view[i] != 0 and view[i+1] == config.ETAT_ACTIF:
                        cible_pid = view[i]
                        view[i+1] = config.ETAT_MORT #éviter race condition où un autre prédateur mange la proie pendant qu'elle se "nettoie"/se supprime
                        break # cible trouvée
                        
            # envoi signal pour tuer, hors du verrou pour ne pas bloquer
            if cible_pid != -1:
                try:
                    os.kill(cible_pid, signal.SIGTERM)
                    energie += config.GAIN_VIANDE
                    print(f"[{my_id}] J'ai mangé la proie {cible_pid} !")
                except ProcessLookupError: pass # la proie était déjà morte

        # reproduction
        else:
            with sem: 
                if active: # permet de ne pas décrémenter le compteur de proies actives si on est déjà passif
                    view[config.IDX_COUNT_ACTIVE_PREDATOR] -=1
                    view[my_index+1] = config.ETAT_PASSIF
                    active = False
            if energie >= my_r and mq:
                r = random.randint(1,2)
                if r == 1:
                    try:
                        mq.send("ADD_PREDATOR".encode(), type = 1)
                        energie -= config.COUT_REPRODUCTION
                        print(f"[{my_id}] Reproduction !")
                    except sysv_ipc.BusyError: 
                        pass
                else:
                    pass    

        time.sleep(config.VITESSE_SIMU)

finally:
    # nettoyage
    if my_index != -1:
        with sem:
            view[my_index] = 0
            if is_registered:
                view[config.IDX_COUNT_PREDATOR] -= 1
                if active:
                    view[config.IDX_COUNT_ACTIVE_PREDATOR] -=1
            view[my_index+1] = config.ETAT_MORT
            
    view.release()
    shm.close()