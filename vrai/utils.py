import random, config, sysv_ipc
from multiprocessing import shared_memory, resource_tracker

def fix_tracker(shm):
    """Empêche Python de supprimer la mémoire quand le processus s'arrête."""
    try:
        resource_tracker.unregister(shm._name, 'shared_memory')
    except Exception:
        pass
            

def update_counts(lock, type_str, delta):
    try:
        # on attache la SHM des stats
        shm_stats = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME)
        fix_tracker(shm_stats)
        
        with lock:
            # on crée la vue
            view = memoryview(shm_stats.buf).cast('i')
            
            if type_str == "PREY":
                view[config.IDX_PROIE] += delta
            elif type_str == "PREDATOR":
                view[config.IDX_PRED] += delta
            
            # on libère le pointeur avant de fermer la SHM
            view.release()
            
        shm_stats.close()
    except Exception as e:
        print(f"[UTILS] Erreur update stats: {e}")

def read_counts():
    try:
        shm = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME)
        fix_tracker(shm)
        stats = memoryview(shm.buf).cast('i')
        # pas besoin de lock pour juste lire un entier pour de l'affichage
        nb_p = stats[config.IDX_PROIE]
        nb_l = stats[config.IDX_PRED]
        stats.release()
        shm.close()
        return nb_p, nb_l
    except:
        return 0, 0
