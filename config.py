import os
from dotenv import load_dotenv

load_dotenv()

# Ajustar para o caminho real do Stockfish na máquina
STOCKFISH_PATH = os.path.expanduser("~/stockfish/stockfish-ubuntu-x86-64-avx2")

# Anthropic API Key via variável de ambiente
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Modelo e limite de tokens usados pelo diagnóstico da IA
ANTHROPIC_MODEL = "claude-opus-4-6"
ANTHROPIC_MAX_TOKENS = 8192

# Profundidade de análise do Stockfish (maior = mais preciso, mais lento)
# 10 é suficiente para detectar erros estratégicos; aumente para 15+ se quiser mais precisão
STOCKFISH_DEPTH = 10

# Limiar de erro: diferença de centipawns para considerar lance ruim
ERROR_THRESHOLD_CP = 50

# Número mínimo de ocorrências para considerar uma fraqueza recorrente
MIN_OCCURRENCES = 3

# Cap de magnitude para estatísticas de perfil. Posições com mate (≈10000 cp)
# distorceriam avg_error_magnitude_cp — tratamos qualquer erro acima deste valor
# como "erro decisivo" para fins estatísticos. O valor bruto ainda é preservado
# no campo error_magnitude do resultado da validação.
MAX_STAT_CP = 500

# Valor de centipawns atribuído a posições de mate pelo python-chess (mate_score).
MATE_SCORE = 10000

# Acima deste valor consideramos a avaliação como tática/decisiva (próxima de mate).
TACTICAL_THRESHOLD_CP = 9000

# Timeout (segundos) para chamadas HTTP à API do Chess.com.
HTTP_TIMEOUT = 15


def validate_stockfish_path() -> None:
    """
    Verifica que o binário do Stockfish existe e é executável.
    Levanta FileNotFoundError com mensagem acionável caso contrário.
    """
    if not os.path.isfile(STOCKFISH_PATH):
        raise FileNotFoundError(
            f"Stockfish não encontrado em '{STOCKFISH_PATH}'. "
            "Ajuste STOCKFISH_PATH em config.py ou instale o binário."
        )
    if not os.access(STOCKFISH_PATH, os.X_OK):
        raise PermissionError(
            f"Stockfish em '{STOCKFISH_PATH}' não é executável. "
            "Rode: chmod +x no binário."
        )
