import socket, sysv_ipc, subprocess, sys, random, time
from multiprocessing import shared_memory
import config
import utils

my_id, my_shm_name, my_h, my__r, response = initialisation_processus()

shm = shared_memory.SharedMemory(name=my_shm_name)
sem = sysv_ipc.Semaphore(config.SEM_KEY)

self_pos = (response["start_x"], response["start_y"])
energie = config.INITIAL_ENERGY
alive = True



while alive:

    energie -= config.COUT_VIE

    if energie <= 0:
        print(f"[{my_id}] est mort de faim")
        with sem:
            shm.buf[utils.to_idx(self_pos)] = config.VIDE
        break
        
    with sem:
        index_actuel = (self_pos[1]*config.MAP_SIZE) + self_pos[0]
        valeur_case = shm.buf[index_actuel]

        if valeur_case >= config.PREDATEUR:
            print(f"[{my_id}] s'est fait manger")
            alive = False
            break

    if energie < my_h:

        with sem:
            cible = utils.regarder_autour(self_pos, shm, portee=2)
            if cible == None:
                nouvelle_pos = utils.nouvelle_pos_aleatoire(self_pos) #genère nouvelle position aléatoire par rapport à là où est process
                self_pos = utils.update_map(shm, self_pos,nouvelle_pos)
            else:
                if utils.in_range(self_pos,cible):
                    self_pos = utils.manger(shm,self_pos,cible_pos, mon_type)
                    energie += config.GAIN_NOURRITURE
                else:
                    nouvelle_pos = utils.calculer_direction(self_pos, cible)
                    self_pos = utils.update_map(shm, self_pos,nouvelle_pos)   
