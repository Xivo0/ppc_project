from multiprocessing import shared_memory, resource_tracker

def fix_tracker(shm):
    """Empêche Python de supprimer la mémoire quand le processus s'arrête."""
    try:
        resource_tracker.unregister(shm._name, 'shared_memory')
    except Exception:
        pass
