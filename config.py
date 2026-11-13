import os
from dotenv import load_dotenv

load_dotenv()

# Caminho do binário do Stockfish. No deploy (Docker) vem de STOCKFISH_PATH;
# localmente cai no caminho padrão da máquina de desenvolvimento.
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH") or os.path.expanduser(
    "~/stockfish/stockfish-ubuntu-x86-64-avx2"
)

# Anthropic API Key via variável de ambiente
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Modelo e limite de tokens usados pelo diagnóstico da IA (override via env)
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")
ANTHROPIC_MAX_TOKENS = 8192

# Classificador LLM dos erros que nenhuma regra explica (modules/error_classifier.py).
# Mesmo modelo do diagnóstico, salvo override. O teto limita o gasto por análise: os
# erros de maior perda vão primeiro; o resto fica "sem conceito". Desligue com
# LLM_CLASSIFY_ERRORS=0.
ANTHROPIC_CLASSIFIER_MODEL = os.getenv("ANTHROPIC_CLASSIFIER_MODEL") or ANTHROPIC_MODEL
LLM_CLASSIFY_ERRORS = os.getenv("LLM_CLASSIFY_ERRORS", "1").strip().lower() not in ("0", "false", "no", "off")
LLM_CLASSIFY_MAX_ERRORS = int(os.getenv("LLM_CLASSIFY_MAX_ERRORS", "60"))

# ── Persistência ──────────────────────────────────────────────────────────────
# DATA_DIR: quando definido (ex.: volume montado em /data no deploy), o banco e os
# perfis ficam sob ele — assim sobrevivem a redeploys. Sem ele, mantém o layout
# local de desenvolvimento (./output e modules/../data/profiler.db).
DATA_DIR = os.getenv("DATA_DIR")
if DATA_DIR:
    OUTPUT_DIR = os.path.join(DATA_DIR, "output")
    DB_PATH = os.path.join(DATA_DIR, "profiler.db")
else:
    OUTPUT_DIR = "output"
    DB_PATH = None  # modules/db.py usa seu default relativo ao módulo
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Banco durável dos dados de usuário (contas, sessões de login, análises). Com uma
# URL Postgres (ex.: Neon/Supabase/Render: postgresql://user:pass@host/db?sslmode=require)
# os dados vivem fora do container e sobrevivem a redeploys. Sem ela, usa o SQLite local
# (data/profiler.db ou DATA_DIR/profiler.db). Ver modules/app_store.py.
DATABASE_URL = os.getenv("DATABASE_URL") or None
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "5"))

# ── Login ─────────────────────────────────────────────────────────────────────
# Duração de uma sessão de login (cookie no navegador), em dias.
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))

# Cadastro de novas contas pela interface. ALLOW_SIGNUP=0 fecha o cadastro (contas
# passam a ser criadas só via `python manage.py create-user`).
ALLOW_SIGNUP = os.getenv("ALLOW_SIGNUP", "1").strip().lower() not in ("0", "false", "no", "off")

# Código de convite exigido para criar conta (deploy público: a chave da Anthropic
# custa dinheiro). APP_PASSWORD, a antiga senha compartilhada, vale como fallback.
# Sem nenhum dos dois, o cadastro é aberto (uso local).
SIGNUP_CODE = os.getenv("SIGNUP_CODE") or os.getenv("APP_PASSWORD") or None

# Profundidade de análise do Stockfish (maior = mais preciso, mais lento)
# 10 é suficiente para detectar erros estratégicos; aumente para 15+ se quiser mais precisão
STOCKFISH_DEPTH = 10

# Profundidade da passada de confirmação: erros flagados na triagem (STOCKFISH_DEPTH)
# são re-validados nesta profundidade para eliminar falsos positivos de horizonte.
# Só roda sobre os lances já marcados como erro (~fração pequena das posições).
STOCKFISH_CONFIRM_DEPTH = 16

# Quantos lances (meios-lances) da linha principal do Stockfish guardar por posição.
# A camada tática e os filtros de precisão (modules/attribution.py) olham essa
# distância à frente: ganhos de material ao longo da linha, persistência do efeito.
PV_PLIES = 6

# Ganho mínimo de material (cp) ao longo da linha do engine para um erro ser tático:
# o melhor lance ganhava isso para o jogador (tática perdida) ou o lance jogado
# entrega isso ao adversário (tática permitida). 200 = uma qualidade ou dois peões.
TACTIC_LINE_GAIN_CP = 200

# Validar no Stockfish todas as posições, não só as que têm conceito detectado.
# Sem isso, um erro numa posição em que nenhum detector disparou nunca é visto, e a
# taxa de erro global sai subestimada (o denominador conta todas as posições).
VALIDATE_ALL_POSITIONS = True

# Limiar de erro: diferença de centipawns para considerar lance ruim (piso absoluto)
ERROR_THRESHOLD_CP = 50

# Limiar de erro em probabilidade de vitória: um lance só é erro se reduzir a
# probabilidade de vitória do jogador em mais que este delta (modelo Lichess:
# WinP = 1/(1+e^(-0.00368*cp))). Normaliza o erro pelo contexto da posição —
# perder 60cp em posição igual é grave; perder 60cp já com +4 é irrelevante.
WINP_ERROR_THRESHOLD = 0.10

# Lances iniciais ignorados pela análise (teoria de abertura). Conceitos
# estratégicos disparando em lances de livro são ruído, não fraqueza do jogador.
OPENING_MOVES_TO_SKIP = 6

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
