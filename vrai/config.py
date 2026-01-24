HOST = "localhost"
PORT = 1945

SHM_NAME = "ppc_project_shm"
SEM_KEY = 6742
MQ_KEY = 11111

MAX_PREY = 100
MAX_PREDATOR = 100

# case 0 : quantité d'herbe
# case 1 : nombre de proies
# case 2 : nombre de prédateurs
# case 3 à 202 : proies (par paire : [PID, ETAT])
# case 203 à 402 : prédateurs (par paire : [PID, ETAT])
IDX_HERBE = 0
IDX_COUNT_PREY = 1
IDX_COUNT_PREDATOR = 2
IDX_PREY_START = 3
IDX_PREDATOR_START = 3 + (MAX_PREY * 2)

ETAT_MORT = 0
ETAT_ACTIF = 1
ETAT_PASSIF = 2

DEFAULT_H_PREY = 10
DEFAULT_R_PREY = 15
DEFAULT_H_PREDATOR = 30
DEFAULT_R_PREDATOR = 50

INITIAL_ENERGY = 10
COUT_VIE = 1
GAIN_NOURRITURE = 5
COUT_REPRODUCTION = 5

VITESSE_SIMU = 0.5