import tkinter as tk
import sysv_ipc
import config
import json
import os, signal

class SimulationDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title("Tableau de Bord - Ecosystème IPC")
        self.root.geometry("400x300")
        self.env_pid = None

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

        self.btn_stop = tk.Button(root,text="STOP", bg="red", command= self.stop)
        self.btn_stop.pack(pady=20)
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
        last_message = None
        try:
            while True:
                message, mtype = self.mq.receive(block=False, type=2)
                last_message = message
        except sysv_ipc.BusyError:
            pass        
        if last_message:
            stats = json.loads(last_message.decode())
            self.env_pid = stats['env_pid']
            # Mise à jour de l'affichage    
            self.herbe_label.config(text=f"Herbe disponible : {stats['nbr_herbe']}")
            self.prey_label.config(text=f"Proies en vie : {stats['nbr_prey']}  (Actives : {stats['nbr_active_prey']})")
            self.predator_label.config(text=f"Prédateurs en vie : {stats['nbr_predator']} (Actives : {stats['nbr_active_predator']})")

        self.root.after(200, self.update_view)

    def toggle_drought(self):
        try:
            os.kill(self.env_pid, signal.SIGUSR1)

            self.is_drought = not self.is_drought
            if self.is_drought:
                self.btn_drought.config(text="Désactiver Sécheresse", bg="red", fg="white")
            else:
                self.btn_drought.config(text="Activer Sécheresse", bg="orange", fg="black")

        except Exception as e:
            print(f"Erreur lors de l'envoi du signal : {e}")

    def stop(self):
        self.mq.send("STOP".encode(), type = 1)        

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationDisplay(root)
    root.mainloop()