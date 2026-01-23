import subprocess, sys

print(f"Lancement")
for _ in range(2): subprocess.Popen([sys.executable, "predator.py"])
for _ in range(4): subprocess.Popen([sys.executable, "prey.py"])
