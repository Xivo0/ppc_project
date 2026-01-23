import socket, sysv_ipc, subprocess, sys, random, time
from multiprocessing import shared_memory
import config
import utils
import json
import os

def initialisation_processus():

    #pour la reproduction, si on veut faire des h et r différents
    if len(sys.argv) >2:
        h = float(sys.argv[1])
        r = float(sys.argv[2])
    else:
        h = config.DEFAULT_H_PREDATOR if "predator" in sys.argv[0] else config.DEFAULT_H_PREY
        r = config.DEFAULT_R_PREDATOR if "predator" in sys.argv[0] else config.DEFAULT_R_PREY

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((config.HOST, config.PORT))

            s.sendall("PREDATOR".encode('utf-8'))

            data = s.recv(1024).decode('utf-8')
            response = json.loads(data)

            if response["start_x"] == -1:
                print(f"['PREDATOR'] Serveur plein, impossible de naître.")
                sys.exit(0)
    except Exception as e:
        print(f"Erreur de connexion à l'environnement : {e}")
        sys.exit(1)

    my_id = os.getpid()
    shm_name = config.SHM_NAME

    return my_id, shm_name, h, r, response


my_id, my_shm_name, my_h, my_r, response = initialisation_processus()

shm = shared_memory.SharedMemory(name=my_shm_name)
utils.fix_tracker(shm)
sem = sysv_ipc.Semaphore(config.SEM_KEY)

self_pos = (response["start_x"], response["start_y"])
energie = config.INITIAL_ENERGY_PREDATOR
alive = True

try:
    while alive:

        energie -= config.COUT_VIE

        if energie <= 0:
            print(f"[{my_id}] est mort de faim")
            break

        if energie <= my_h: # L'animal a faim, il cherche à manger

                cible = utils.regarder_autour(self_pos, shm, 2, config.PROIE)
                if cible == None:
                    nouvelle_pos = utils.nouvelle_pos_aleatoire(self_pos) #genère nouvelle position aléatoire par rapport à là où est process
                    self_pos = utils.update_map(shm, sem, self_pos,nouvelle_pos, config.PREDATEUR)
                else:
                    if utils.in_range(self_pos,cible):
                        self_pos = utils.manger(shm, sem, self_pos, cible, config.PREDATEUR)
                        energie += config.GAIN_NOURRITURE
                    else:
                        nouvelle_pos = utils.calculer_direction(self_pos, cible)
                        self_pos = utils.update_map(shm, sem, self_pos,nouvelle_pos, config.PREDATEUR)   

        if energie >= my_r: # L'animal est passif, il peut se reproduire
                
                choice = random.randint(0,2)
                if choice == 0:
                    child_h = my_h + random.randint(-10,10)
                    child_r = my_h + random.randint(-10,10)    
                    subprocess.Popen([sys.executable, "predator.py", str(child_h),str(child_r)]) #voir si on peut faire une position à côté de l'animal qui se reproduit
                    energie -= config.COUT_REPRODUCTION
                if choice == 1:
                    nouvelle_pos = utils.nouvelle_pos_aleatoire(self_pos)
                    self_pos = utils.update_map(shm, sem, self_pos,nouvelle_pos, config.PREDATEUR)    
                else:
                    continue #on laisse comme 3ème choix la possibilité de ne rien faire

        time.sleep(config.VITESSE_SIMU if hasattr(config, 'VITESSE_SIMU') else 0.5)                
finally:
    utils.update_counts(sem, "PREDATOR", -1)

    try:
        with sem:
            idx = utils.to_idx(self_pos)
            # Un loup a une valeur >= 20. 
            if shm.buf[idx] >= config.PREDATEUR:
                shm.buf[idx] -= config.PREDATEUR
    except:
        pass

    shm.close()
    print(f"[{my_id}] Loup mort")