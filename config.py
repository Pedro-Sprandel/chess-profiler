import os
from dotenv import load_dotenv

load_dotenv()

# Ajustar para o caminho real do Stockfish na máquina
STOCKFISH_PATH = os.path.expanduser("~/stockfish/stockfish-ubuntu-x86-64-avx2")

# Anthropic API Key via variável de ambiente
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Profundidade de análise do Stockfish (maior = mais preciso, mais lento)
STOCKFISH_DEPTH = 15

# Limiar de erro: diferença de centipawns para considerar lance ruim
ERROR_THRESHOLD_CP = 50

# Número mínimo de ocorrências para considerar uma fraqueza recorrente
MIN_OCCURRENCES = 3
