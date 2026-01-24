import tkinter as tk
import sysv_ipc
import config
import utils
import json

class SimulationDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title("Tableau de Bord - Ecosystème IPC")
        self.root.geometry("400x300")

        # Interface
        tk.Label(root, text="SURVEILLANCE DE L'ÉCOSYSTÈME", font=("Arial", 16, "bold"), pady=10).pack()
        
        self.herbe_label = tk.Label(root, text="Herbe : 0", font=("Arial", 14), fg="green")
        self.herbe_label.pack(pady=10)

        self.prey_label = tk.Label(root, text="Proies : 0 (0 Actives)", font=("Arial", 14), fg="blue")
        self.prey_label.pack(pady=10)

        self.predator_label = tk.Label(root, text="Prédateurs : 0", font=("Arial", 14), fg="red")
        self.predator_label.pack(pady=10)

        self.is_drought = False
        self.btn_drought = tk.Button(root, text="Activer Sécheresse", 
                                     bg="orange", fg="black",
                                     command=self.toggle_drought)
        self.btn_drought.pack(pady=20)
        # Connexion à la Message Queue pour envoyer les ordres
        try:
            self.mq = sysv_ipc.MessageQueue(config.MQ_KEY)
        except sysv_ipc.ExistentialError:
            print("Erreur: Message Queue introuvable. Lancez env.py d'abord.")
            self.mq = None
            self.root.destroy()
            return

        self.update_view()

    def update_view(self):
        try:
            message, mtype = self.mq.receive(block=False, type=2)
            stats = json.loads(message.decode())
            print(json.dumps(stats))

            # Mise à jour de l'affichage
            self.herbe_label.config(text=f"Herbe disponible : {stats['nbr_herbe']}")
            self.prey_label.config(text=f"Proies en vie : {stats['nbr_prey']}  (Actives : {stats['nbr_active_prey']})")
            self.predator_label.config(text=f"Prédateurs en vie : {stats['nbr_predator']} (Actives : {stats['nbr_active_predator']})")

        except Exception:
            print("haha")
            pass
        self.root.after(200, self.update_view)

    def __del__(self):
        if hasattr(self, 'view'): self.view.release()
        if hasattr(self, 'shm'): self.shm.close()
    
    def toggle_drought(self):
        if self.mq:
            try:
                self.mq.send("seche".encode())

                self.is_drought = not self.is_drought
                if self.is_drought:
                    self.btn_drought.config(text="Désactiver Sécheresse", bg="red", fg="white")
                else:
                    self.btn_drought.config(text="Activer Sécheresse", bg="orange", fg="black")

            except sysv_ipc.Error as e:
                print(f"Erreur d'envoi : {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationDisplay(root)
    root.mainloop()