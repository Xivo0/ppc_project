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

            s.sendall("PROIE".encode('utf-8'))

            data = s.recv(1024).decode('utf-8')
            response = json.loads(data)

            if response["start_x"] == -1:
                print(f"['PROIE'] Serveur plein, impossible de naître.")
                sys.exit(0)
    except Exception as e:
        print(f"Erreur de connexion à l'environnement : {e}")
        sys.exit(1)

    my_id = os.getpid()
    shm_name = config.SHM_NAME

    return my_id, shm_name, h, r, response



my_id, my_shm_name, my_h, my__r, response = initialisation_processus()

shm = shared_memory.SharedMemory(name=my_shm_name)
utils.fix_tracker(shm)
sem = sysv_ipc.Semaphore(config.SEM_KEY)

self_pos = (response["start_x"], response["start_y"])
energie = config.INITIAL_ENERGY
alive = True


try:
    while alive:

        energie -= config.COUT_VIE

        if energie <= 0:
            print(f"[{my_id}] est mort de faim")
            break

        with sem:
            index_actuel = (self_pos[1]*config.MAP_SIZE) + self_pos[0]
            valeur_case = shm.buf[index_actuel]

            if valeur_case >= config.PREDATEUR:
                print(f"[{my_id}] s'est fait manger")
                alive = False
                break

        if energie < my_h:

                cible = utils.regarder_autour(self_pos, shm, 1, config.HERBE) #donne position de la cible si elle est dans la range
                if cible == None:
                    nouvelle_pos = utils.nouvelle_pos_aleatoire(self_pos) #genère nouvelle position aléatoire par rapport à là où est process
                    self_pos = utils.update_map(shm, sem, self_pos,nouvelle_pos, config.PROIE)
                    print(f"[{my_id}] Bouge vers {self_pos} | Energie: {energie}")
                else:
                    if utils.in_range(self_pos,cible):
                        self_pos = utils.manger(shm, sem, self_pos, cible, config.PROIE)
                        energie += config.GAIN_NOURRITURE
                    else:
                        nouvelle_pos = utils.calculer_direction(self_pos, cible)
                        self_pos = utils.update_map(shm, sem, self_pos,nouvelle_pos, config.PROIE)   
                        print(f"[{my_id}] Bouge vers {self_pos} | Energie: {energie}")
        time.sleep(config.VITESSE_SIMU if hasattr(config, 'VITESSE_SIMU') else 0.5)                                    
finally:
    utils.update_counts(sem, "PREY", -1)

    try:
        with sem:
            idx = utils.to_idx(self_pos)
            # Vérification stricte pour ne pas effacer un loup qui nous a mangé
            if config.PROIE <= shm.buf[idx] < config.PREDATEUR:
                shm.buf[idx] -= config.PROIE
    except:
        pass # Sécurité pour ne pas planter le nettoyage

    # 3. Fermeture propre
    shm.close()
    print(f"[{my_id}] Mort validée. Ressources libérées.")