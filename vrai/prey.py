import socket, sysv_ipc, subprocess, sys, random, time, os, signal, json
from multiprocessing import shared_memory
import config
import utils


def eaten_handler(signum, frame):
    global alive
    print(f"[{os.getpid()}] ARGH ! Je me suis fait manger par un loup !")
    alive = False

def initialisation_processus():
    if len(sys.argv) > 2:
        h, r = float(sys.argv[1]), float(sys.argv[2])
    else:
        h, r = config.DEFAULT_H_PREY, config.DEFAULT_R_PREY

    # onn demande la permission de naître à l'environnement
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((config.HOST, config.PORT))
        s.sendall("PROIE".encode())
        response = json.loads(s.recv(1024).decode())
        if response.get("status") == "FULL":
            sys.exit(0)
            
    return os.getpid(), h, r

signal.signal(signal.SIGTERM, eaten_handler) # écoute du signal de mort
my_id, my_h, my_r = initialisation_processus()

shm = shared_memory.SharedMemory(name=config.SHM_NAME)
utils.fix_tracker(shm)
sem = sysv_ipc.Semaphore(config.SEM_KEY)
view = memoryview(shm.buf).cast('i')

try:
    mq = sysv_ipc.MessageQueue(config.MQ_KEY)
except: mq = None

energie = config.INITIAL_ENERGY
alive = True
my_index = -1

try:
    # inscription dans mémoire partagée
    with sem:
        for i in range(config.IDX_PREY_START, config.IDX_PREDATOR_START, 2):
            if view[i] == 0: # place libre trouvée
                view[i] = my_id
                view[i+1] = config.ETAT_ACTIF
                my_index = i
                break
                
    if my_index == -1: sys.exit(0) # plus de place

    
    with sem:
        view[my_index] = my_id
        view[config.IDX_COUNT_PREY] += 1

    
    # boucle de vie
    while alive:
        energie -= config.COUT_VIE

        if energie <= 0:
            print(f"[{my_id}] Mort de faim.")
            break

        # manger l'herbe (partagée)
        if energie < my_h:
            with sem:
                view[my_index+1] = config.ETAT_ACTIF
                if view[config.IDX_HERBE] > 0:
                    view[config.IDX_HERBE] -= 1
                    energie += config.GAIN_NOURRITURE
                    print(f"[{my_id}] Miam ! Herbe restante : {view[config.IDX_HERBE]}")

        # mode passif et reproduction
        else:
            with sem:
                view[my_index+1] = config.ETAT_PASSIF
                
            if energie >= my_r and mq:
                try:
                    mq.send("ADD_PROIE".encode())
                    energie -= config.COUT_REPRODUCTION
                    print(f"[{my_id}] Reproduction !")
                except sysv_ipc.BusyError: pass

        time.sleep(config.VITESSE_SIMU)

finally:
    # nettoyage: on se retire de la liste
    if my_index != -1:
        with sem:
            view[my_index] = 0 # libère le PID
            view[config.IDX_COUNT_PREY] -= 1
            view[my_index+1] = config.ETAT_MORT
            
    view.release()
    shm.close()