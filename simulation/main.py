import subprocess, sys

print(f"Lancement")
nbr_proies = int(input("Rentrez le nombre de proies voulues:"))
nbr_predateurs = int(input("Rentrez le nombre de prédateurs voulus:"))
for _ in range(nbr_proies): subprocess.Popen([sys.executable, "prey.py"])
for _ in range(nbr_predateurs): subprocess.Popen([sys.executable, "predator.py"])