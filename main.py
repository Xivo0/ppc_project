

# 5. Lancement Initial
print(f"[ENV] Lancement initial...")
for _ in range(2): subprocess.Popen([sys.executable, "predator.py"])
for _ in range(4): subprocess.Popen([sys.executable, "prey.py"])
