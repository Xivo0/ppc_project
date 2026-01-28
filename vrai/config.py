HOST = "localhost"
PORT = 1945

SHM_NAME = "ppc_project_shm"
SEM_KEY = 6742
MQ_KEY = 11111

MAX_PREY = 100
MAX_PREDATOR = 100

# case 0 : quantité d'herbe
# case 1 : nombre de proies
# case 2 : nombre de proies actives
# case 3 : nombre de prédateurs
# case 4 : nombre de prédateurs actifs
# case 5 à 204 : proies (par paire : [PID, ETAT])
# case 205 à 404 : prédateurs (par paire : [PID, ETAT])
IDX_HERBE = 0
IDX_COUNT_PREY = 1
IDX_COUNT_PREDATOR = 2
IDX_COUNT_ACTIVE_PREY = 3
IDX_COUNT_ACTIVE_PREDATOR = 4
IDX_PREY_START = 5
IDX_PREDATOR_START = 5 + (MAX_PREY * 2)

ETAT_MORT = 0
ETAT_ACTIF = 1
ETAT_PASSIF = 2

INITIAL_ENERGY_PREY = 20
INITIAL_ENERGY_PREDATOR = 40

DEFAULT_H_PREY = 25
DEFAULT_R_PREY = 30
DEFAULT_H_PREDATOR = 60
DEFAULT_R_PREDATOR = 80


COUT_VIE = 1
GAIN_HERBE = 15
GAIN_VIANDE = 30
COUT_REPRODUCTION = 15

VITESSE_SIMU = 0.5