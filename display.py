import tkinter as tk
from multiprocessing import shared_memory
import sysv_ipc
import config
import utils

class SimulationDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulation Proie-Prédateur")
        
        # 1. Connexion aux mémoires partagées
        try:
            self.shm = shared_memory.SharedMemory(name=config.SHM_NAME)
            self.shm_stats = shared_memory.SharedMemory(name=config.SHM_COUNTERS_NAME)
        except FileNotFoundError:
            print("Erreur : L'environnement n'est pas lancé (SHM introuvable).")
            self.root.destroy()
            return

        # 2. Configuration de l'interface
        self.cell_size = 30
        self.canvas_size = config.MAP_SIZE * self.cell_size
        
        # Panel de statistiques
        self.stats_label = tk.Label(root, text="Proies: 0 | Prédateurs: 0", font=("Arial", 14), pady=10)
        self.stats_label.pack()

        # Canevas pour la grille
        self.canvas = tk.Canvas(root, width=self.canvas_size, height=self.canvas_size, bg="white")
        self.canvas.pack()

        # Création des rectangles (on les crée une fois, on changera leur couleur ensuite)
        self.rects = []
        for y in range(config.MAP_SIZE):
            row = []
            for x in range(config.MAP_SIZE):
                x1, y1 = x * self.cell_size, y * self.cell_size
                x2, y2 = x1 + self.cell_size, y1 + self.cell_size
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="gray90")
                row.append(rect)
            self.rects.append(row)

        # 3. Lancement de la boucle de rafraîchissement
        self.update_view()

    def update_view(self):
        # Lecture des statistiques via utils
        nb_p, nb_l = utils.read_counts()
        self.stats_label.config(text=f"Proies: {nb_p} | Prédateurs: {nb_l}")

        # Mise à jour de la grille
        for y in range(config.MAP_SIZE):
            for x in range(config.MAP_SIZE):
                val = self.shm.buf[utils.to_idx((x, y))]
                color = self.get_color(val)
                self.canvas.itemconfig(self.rects[y][x], fill=color)

        # Rappel de la fonction toutes les 100ms
        self.root.after(100, self.update_view)

    def get_color(self, val):
        # Logique de décodage des valeurs composites
        if val >= config.PREDATEUR:
            return "#FF5555" # Rouge (Prédateur)
        elif val >= config.PROIE:
            return "#5555FF" # Bleu (Proie)
        elif val == config.HERBE:
            return "#A2D149" # Vert (Herbe)
        return "white"      # Vide

    def __del__(self):
        # Fermeture propre lors de la fermeture de la fenêtre
        if hasattr(self, 'shm'):
            self.shm.close()
        if hasattr(self, 'shm_stats'):
            self.shm_stats.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationDisplay(root)
    root.mainloop()