import tkinter as tk
from multiprocessing import shared_memory
import sysv_ipc
import config
import utils

class SimulationDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title("Tableau de Bord - Ecosystème IPC")
        self.root.geometry("400x300")
        
        try:
            self.shm = shared_memory.SharedMemory(name=config.SHM_NAME)
            self.view = memoryview(self.shm.buf).cast('i')
        except FileNotFoundError:
            print("Erreur : L'environnement n'est pas lancé.")
            self.root.destroy()
            return

        # Interface
        tk.Label(root, text="SURVEILLANCE DE L'ÉCOSYSTÈME", font=("Arial", 16, "bold"), pady=10).pack()
        
        self.herbe_label = tk.Label(root, text="Herbe : 0", font=("Arial", 14), fg="green")
        self.herbe_label.pack(pady=10)

        self.prey_label = tk.Label(root, text="Proies : 0 (0 Actives)", font=("Arial", 14), fg="blue")
        self.prey_label.pack(pady=10)

        self.predator_label = tk.Label(root, text="Prédateurs : 0", font=("Arial", 14), fg="red")
        self.predator_label.pack(pady=10)

        self.update_view()

    def update_view(self):
        try:
            # 1. Compter l'herbe
            herbe = self.view[config.IDX_HERBE]

            # 2. Compter les proies
            p_total, p_actives = 0, 0
            for i in range(config.IDX_PREY_START, config.IDX_PREDATOR_START, 2):
                if self.view[i] != 0:
                    p_total += 1
                    if self.view[i+1] == config.ETAT_ACTIF: p_actives += 1

            # 3. Compter les prédateurs
            l_total = 0
            max_idx = config.IDX_PREDATOR_START + (config.MAX_PREDATOR * 2)
            for i in range(config.IDX_PREDATOR_START, max_idx, 2):
                if self.view[i] != 0: l_total += 1

            # Mise à jour de l'affichage
            self.herbe_label.config(text=f"Herbe disponible : {herbe}")
            self.prey_label.config(text=f"Proies en vie : {p_total}  (Actives : {p_actives})")
            self.predator_label.config(text=f"Prédateurs en vie : {l_total}")

            self.root.after(200, self.update_view)
        except Exception:
            pass # Si la mémoire est détruite pendant l'affichage

    def __del__(self):
        if hasattr(self, 'view'): self.view.release()
        if hasattr(self, 'shm'): self.shm.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationDisplay(root)
    root.mainloop()