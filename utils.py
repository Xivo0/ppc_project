import random, config, sysv_ipc
from multiprocessing import shared_memory, resource_tracker

def fix_tracker(shm):
    """Empêche Python de supprimer la mémoire quand le processus s'arrête."""
    try:
        resource_tracker.unregister(shm._name, 'shared_memory')
    except Exception:
        pass

def to_idx(pos):
    return(pos[1] * config.MAP_SIZE) + pos[0]

def nouvelle_pos_aleatoire(pos_actuelle):

    x, y = pos_actuelle

    #deplacement de -1, 0 ou 1 pour x et y
    dx = random.randint(-1,1)
    dy = random.randint(-1,1)

    #max et min évitent qu'on dépasse de la map
    nx = max(0, min(config.MAP_SIZE -1, x + dx))
    ny = max(0, min(config.MAP_SIZE -1, y + dy))

    return (nx,ny)

def update_map(shm, sem, pos_actuelle, nouvelle_pos, mon_type):

    old_idx = to_idx(pos_actuelle)
    new_idx = to_idx(nouvelle_pos)

    with sem:
        if shm.buf[new_idx] >= config.PROIE:
            return pos_actuelle #on bouge pas
        #on quitte l'ancienne case en enlevant 10 ou 20 selon notre type
        shm.buf[old_idx] -= mon_type
        #on occupe nouvelle case
        shm.buf[new_idx] += mon_type

    return nouvelle_pos

def regarder_autour(pos_actuelle, shm, portee, cherche_quoi):   

    x_self, y_self = pos_actuelle

    for dy in range(-portee, portee + 1):
        for dx in range(-portee, portee + 1):
            if dx == 0 and dy == 0: continue #sur place

            nx, ny = x_self + dx, y_self + dy
            #verification en bordure
            if 0 <= nx < config.MAP_SIZE and 0 <= ny < config.MAP_SIZE:
                val = shm.buf[to_idx((nx,ny))]

                if cherche_quoi == config.PROIE and val >= config.PROIE:
                    return(nx,ny)
                elif cherche_quoi == config.HERBE and (val == config.HERBE or val == config.PROIE + config.HERBE):
                    return(nx,ny)
    return None            

def manger(shm, sem, pos_actuelle, pos_cible, mon_type):
    old_idx = to_idx(pos_actuelle)
    target_idx = to_idx(pos_cible)

    with sem:
        #on quitte case
        shm.buf[old_idx] -= mon_type

        #on mange
        if mon_type == config.PREDATEUR:
            shm.buf[target_idx] -= config.PROIE
        else:
            shm.buf[target_idx] -= config.HERBE

        shm.buf[target_idx] += mon_type

    return pos_cible            

def calculer_direction(pos_actuelle, pos_cible):

    x, y = pos_actuelle
    tx, ty = pos_cible

    nx = x + (1 if tx > x else -1 if tx < x else 0)
    ny = y + (1 if ty > y else -1 if ty < y else 0)

    return (nx, ny)

def in_range(pos1,pos2):
    return max(abs(pos1[0] - pos2[0]),abs(pos1[1] - pos2[1])) == 1


def update_counts(lock, type_str, delta):
    """Met à jour les compteurs globaux de manière sécurisée."""
    try:
        # On attache la SHM des stats
        shm_stats = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME)
        fix_tracker(shm_stats)
        
        with lock:
            # On crée la vue
            view = memoryview(shm_stats.buf).cast('i')
            
            if type_str == "PREY":
                view[config.IDX_PROIE] += delta
            elif type_str == "PREDATOR":
                view[config.IDX_PRED] += delta
            
            # CRUCIAL : On libère le pointeur avant de fermer la SHM
            view.release()
            
        shm_stats.close()
    except Exception as e:
        print(f"[UTILS] Erreur update stats: {e}")

def read_counts():
    try:
        shm = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME)
        fix_tracker(shm)
        stats = memoryview(shm.buf).cast('i')
        # Pas besoin de lock strict pour juste lire un entier pour de l'affichage
        nb_p = stats[config.IDX_PROIE]
        nb_l = stats[config.IDX_PRED]
        stats.release()
        shm.close()
        return nb_p, nb_l
    except:
        return 0, 0
