# CLAUDE.md — Chess Strategic Profiler

Sistema de diagnóstico estratégico personalizado de xadrez desenvolvido como TCC de
Sistemas de Informação (FACCAT). Analisa partidas de um jogador, detecta padrões de
fraqueza estratégica recorrentes com regras determinísticas (python-chess + Stockfish),
e usa um LLM para identificar a causa raiz conectando o diagnóstico aos conceitos
pedagógicos de *The Amateur's Mind* (Jeremy Silman).

---

## Arquitetura

Três camadas em sequência:

```
Partidas (Chess.com API ou PGN) — primeiros OPENING_MOVES_TO_SKIP lances ignorados
        ↓
[1] Detecção determinística — position_analyzer.py
    17 detectores de conceitos Silman por posição (python-chess + SEE)
    + conceito tático derivado (missed_tactic) por gate de precedência
        ↓
[2] Validação quantitativa — stockfish_validator.py
    Duas passadas: triagem (STOCKFISH_DEPTH) + confirmação dos erros
    (STOCKFISH_CONFIRM_DEPTH, MultiPV=2). Erro = queda de probabilidade de
    vitória (ΔWinP, modelo Lichess) acima do threshold + piso em centipawns.
    Cache SQLite evita re-análise de posições já vistas
        ↓
[3] Raciocínio causal — ai_diagnostician.py
    Claude classifica fraquezas em PRIMARY/SECONDARY/NOISE
    e identifica a causa raiz por trás dos sintomas
        ↓
Perfil JSON + Diagnóstico JSON (bilíngue EN/PT) → Interface Streamlit
```

**Stack:** Python 3.10+, python-chess, Stockfish (binário local), Anthropic API
(claude-opus-4-6), Streamlit, Plotly, SQLite.

---

## Estrutura de Diretórios

```
v1/
├── app.py                          ← entrada Streamlit (single-page scroll + scroll-spy)
├── main.py                         ← pipeline CLI (_main(argv=None), --user, --games, --pgn, --color)
├── config.py                       ← STOCKFISH_PATH, ANTHROPIC_API_KEY, thresholds
├── eval_fen.py                     ← utilitário CLI para avaliar uma FEN manualmente
├── requirements.txt
├── .env                            ← ANTHROPIC_API_KEY (não versionado)
├── data/
│   ├── silman_concepts.json        ← base de conhecimento: 18 conceitos (17 estratégicos + missed_tactic)
│   └── profiler.db                 ← SQLite: cache Stockfish + posições + resultados
├── modules/
│   ├── pgn_loader.py               ← carrega partidas de arquivo ou string PGN
│   ├── chess_com_loader.py         ← busca N partidas recentes via API Chess.com
│   ├── position_analyzer.py        ← 17 detectores de conceitos (retornam dicts tipados)
│   ├── stockfish_validator.py      ← validação em batch com cache SQLite
│   ├── concept_relevance.py        ← filtra posições instrutivas (3 gates causais)
│   ├── profile_builder.py          ← acumula fraquezas longitudinalmente
│   ├── ai_diagnostician.py         ← prompt Claude + parse JSON bilíngue estruturado
│   ├── db.py                       ← camada SQLite (3 tabelas, WAL mode)
│   └── fen_fetcher.py              ← busca FENs do Chess.com com filtros (não integrado ao pipeline)
├── ui/
│   ├── i18n.py                     ← 107 chaves EN/PT-BR, função t(key, **kwargs)
│   ├── concepts.py                 ← nomes/categorias de conceitos localizados (lê o JSON)
│   ├── components/
│   │   ├── weakness_chart.py       ← barras, radar por categoria e comparação de perfis (Plotly)
│   │   └── diagnosis_card.py       ← formata output do diagnóstico
│   └── pages/
│       ├── home.py                 ← seção inicial (render())
│       ├── analyze.py              ← formulário Chess.com/PGN + progress bar
│       ├── profile.py              ← dashboard de métricas + gráficos
│       ├── explorer.py             ← tabuleiro SVG com setas de lance/melhor lance
│       └── diagnosis.py            ← causa raiz, classificação, plano de estudo
├── tests/                          ← 269 testes (ver tabela na seção Testes)
└── output/                         ← perfis e diagnósticos gerados ({user}_profile.json, etc.)
```

---

## Configuração

**`config.py`**
```python
STOCKFISH_PATH = os.path.expanduser("~/stockfish/stockfish-ubuntu-x86-64-avx2")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
STOCKFISH_DEPTH = 10          # profundidade da triagem (passada 1)
STOCKFISH_CONFIRM_DEPTH = 16  # profundidade da confirmação (passada 2, só nos erros flagados)
ERROR_THRESHOLD_CP = 50       # piso absoluto de centipawns para classificar como erro
WINP_ERROR_THRESHOLD = 0.10   # queda mínima de probabilidade de vitória (modelo Lichess)
OPENING_MOVES_TO_SKIP = 6     # lances completos iniciais ignorados (teoria de abertura)
MIN_OCCURRENCES = 3           # mínimo de erros para uma fraqueza entrar no perfil
MAX_STAT_CP = 500             # cap de magnitude para estatísticas (evita distorção por posições de mate)
MATE_SCORE = 10000            # valor de cp atribuído a mate (mate_score do python-chess)
TACTICAL_THRESHOLD_CP = 9000  # acima disso a avaliação é considerada tática/decisiva
HTTP_TIMEOUT = 15             # timeout (s) das chamadas à API do Chess.com
ANTHROPIC_MODEL = "claude-opus-4-6"
ANTHROPIC_MAX_TOKENS = 8192

# config.validate_stockfish_path() valida existência/execução do binário (chamada por open_engine())
```

**`.env`** (não versionado)
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Execução

```bash
# Interface web
streamlit run app.py
# → http://localhost:8501

# CLI — busca N partidas do Chess.com
python main.py --user sprandel --games 50

# CLI — analisa arquivo PGN local
python main.py --user sprandel --pgn partidas.pgn --color white

# Avalia uma FEN manualmente (debug)
python eval_fen.py "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
python eval_fen.py "<FEN>" --depth 15 --json

# Testes
pytest                          # 244 testes, todos passando
pytest -v --tb=short
pytest tests/test_position_analyzer.py -v
pytest tests/test_pipeline_e2e.py -v   # requer Stockfish instalado
```

---

## Módulos — Interfaces Públicas

### `modules/pgn_loader.py`
```python
load_games_from_file(pgn_path: str) -> list[chess.pgn.Game]
load_games_from_string(pgn_string: str) -> list[chess.pgn.Game]
iterate_positions(game, player_color: bool) -> Iterator[(board_before, move, board_after)]
```

### `modules/chess_com_loader.py`
```python
fetch_recent_games(username: str, n_games: int = 50) -> list[tuple[chess.pgn.Game, bool]]
# Retorna lista de (game, player_color). Itera arquivos mensais do mais recente
# para o mais antigo e para ao atingir n_games partidas válidas.
```

### `modules/position_analyzer.py`
```python
detect_concepts(board: chess.Board, player_color: bool) -> dict
# Retorna dict com 17 chaves — uma por conceito Silman.
# Cada valor é um dict com pelo menos {"detected": bool} + campos específicos.

static_exchange_gain(board, square, color) -> int
# SEE simplificado: ganho material (cp, peão=100) iniciando capturas na casa.
# Usado por hanging_piece, is_missed_tactic/is_converted_tactic. Ignora cravadas.
```

Definições reforçadas dos detectores sensíveis:
- `weak_square`: buraco no PRÓPRIO campo (fileiras 3-4 brancas / 6-5 pretas) que
  nenhum peão aliado ATRÁS da casa pode vir a defender e que uma peça adversária
  ocupa ou pode ocupar (N/B/R/Q atacando a casa vazia).
- `knight_outpost`: cavalo no campo adversário que nenhum peão inimigo pode atacar
  (nem avançando) E apoiado por peão aliado (definição completa do Silman).
- `hanging_piece`: peça cuja captura ganha material via SEE — inclui peça defendida
  atacada por peça mais barata (cavalo defendido atacado por peão).
- `king_safety`: escudo de peões < 2 OU coluna sem peão aliado adjacente ao rei
  OU rei preso no centro (colunas c-f, sem direito de roque, dama adversária viva).
  Continua gateado pela presença de atacantes (não dispara em finais).

Os 17 conceitos detectados:

| detection_key | Categoria Silman |
|---|---|
| `weak_square` | desequilíbrios estáticos |
| `knight_outpost` | desequilíbrios estáticos |
| `space_advantage` | desequilíbrios estáticos |
| `center_control` | desequilíbrios estáticos |
| `open_file` | desequilíbrios dinâmicos |
| `rook_on_7th` | desequilíbrios dinâmicos |
| `piece_activity` | desequilíbrios dinâmicos |
| `isolated_pawn` | estrutura de peões |
| `passed_pawn` | estrutura de peões |
| `doubled_pawn` | estrutura de peões |
| `pawn_majority` | estrutura de peões |
| `backward_pawn` | estrutura de peões |
| `bishop_pair` | desequilíbrios de material |
| `bad_bishop` | desequilíbrios de material |
| `king_safety` | dinâmica |
| `overloaded_piece` | dinâmica |
| `hanging_piece` | dinâmica |

**Conceito tático derivado (não é detector de posição):**

| detection_key | Categoria |
|---|---|
| `missed_tactic` | tática |

`missed_tactic` **não** é detectado por `detect_concepts()` — é atribuído em
`build_profile()` via `is_missed_tactic()` (ver abaixo) quando o melhor lance era uma
captura que ganhava material e o jogador a recusou (ex.: peça adversária pendurada).
Tem **precedência** sobre os conceitos estratégicos: um erro classificado como tático
vai apenas para `missed_tactic` e não "vaza" para conceitos como `weak_square`.

### `modules/stockfish_validator.py`
```python
open_engine() -> chess.engine.SimpleEngine
# Abre uma instância do Stockfish. Caller responsável por engine.quit().

validate_move(board_before, move_played) -> dict
# Abre/fecha engine internamente. Para uma posição isolada (passada única).

batch_validate(positions: list[tuple], engine=None, depth=STOCKFISH_DEPTH,
               confirm_depth=None) -> list[dict]
# positions: lista de (board_before, move_played)
# engine: instância existente (None = cria e fecha a própria; abertura é lazy —
#         se tudo vier do cache, o engine nem abre)
# Duas passadas: triagem em `depth` + confirmação dos erros em `confirm_depth`
# (default STOCKFISH_CONFIRM_DEPTH). A confirmação usa MultiPV=2: se o lance
# jogado era a 2ª melhor opção com gap ≤ 50cp, não é erro (posição difícil).
# Cache SQLite por (fen, depth) consultado em ambas as passadas.
# Retorna: {is_error, eval_before, eval_after, error_magnitude, delta_winp,
#           involves_mate, best_move}

evaluate_fen(fen: str, depth: int = STOCKFISH_DEPTH, use_cache: bool = True) -> dict
# {score_cp, score_side, is_mate, mate_in, best_move, depth, turn}
```

**Critério de erro (`_classify`):** `is_error` exige TODAS as condições:
1. lance jogado ≠ melhor lance (efeito horizonte: melhor lance nunca é erro)
2. `error_magnitude > ERROR_THRESHOLD_CP` (piso absoluto)
3. `delta_winp > WINP_ERROR_THRESHOLD` — queda de probabilidade de vitória do
   jogador (WinP = 1/(1+e^(-0.00368·cp)), modelo Lichess). Substitui o antigo
   guard de "posição já decidida": swings dentro de posição ganha/perdida quase
   não movem a WinP e são descartados naturalmente.
4. o lance jogado não é uma captura que recupera material (`_is_winning_capture`)

### `modules/concept_relevance.py`
```python
is_instructive(board_before, move_played_uci, best_move_uci, concept_key, player_color) -> bool
is_missed_tactic(board_before, move_played_uci, best_move_uci, player_color) -> bool
is_converted_tactic(board_before, move_played_uci, best_move_uci, player_color) -> bool
```

`is_missed_tactic()` — `True` quando o melhor lance era uma **captura que ganha material**
(decidido por SEE em `_is_material_winning_capture`, considerando a sequência completa
de recapturas) recusada pelo jogador. Retorna `False` se faltar `best_move`/`move_played`,
se o jogador jogou o melhor lance, se o melhor lance não é captura, ou em troca igual.
Usada por `build_profile()` como gate de precedência tática antes dos conceitos estratégicos.

`is_converted_tactic()` — contraparte: `True` quando o jogador **jogou** a captura
ganhadora que era o melhor lance. Alimenta o denominador (`total_occurrences`) do
conceito `missed_tactic`, fazendo a taxa de erro significar "táticas perdidas /
oportunidades táticas" em vez de ~100% por construção.

`is_instructive()` — três gates em ordem de custo crescente:
1. O jogador não jogou o melhor lance
2. O melhor lance envolve o tipo de peça relevante para o conceito (ex: torre para `open_file`)
3. O melhor lance melhora o score do conceito em pelo menos o threshold definido

Se `best_move_uci` é `None`, retorna `True` (sem dados = não filtra).

Scoring para os novos conceitos:
- `hanging_piece`: `-count` (salvar a peça = 0; deixar pendurada = negativo)
- `backward_pawn`: `-count`
- `center_control`: `advantage` (ataques do jogador − ataques do adversário nos 4 centros)

### `modules/profile_builder.py`
```python
build_profile(games_data: list) -> dict
# games_data: lista de dicts com game_id, white, black, player_color, positions
# Cada position precisa de concepts_detected e stockfish_validation.
# Precedência tática: se is_missed_tactic() é True, o erro vai SÓ para o conceito
#   missed_tactic e não é avaliado contra os conceitos estratégicos.
# Caso contrário, só conta um erro para um conceito se is_instructive() retornar True.
# Fraqueza só entra no perfil se error_occurrences >= MIN_OCCURRENCES (default: 3).
# error_magnitude é capeada em MAX_STAT_CP=500 para avg_error_magnitude_cp.
# (_record_error() é o helper interno que credita a ocorrência e guarda a posição.)

save_profile(profile: dict, path: str)
load_profile(path: str) -> dict
```

Estrutura de retorno do perfil:
```json
{
  "generated_at": "YYYY-MM-DD HH:MM UTC",
  "metadata": {"player": str, "source": "pgn|chess_com", "depth": int},
  "total_games": int,
  "total_positions_analyzed": int,
  "total_errors_detected": int,
  "total_missed_checkmates": int,
  "total_allowed_checkmates": int,
  "overall_error_rate": float,
  "weaknesses": [
    {
      "concept": "detection_key",
      "total_occurrences": int,
      "error_occurrences": int,
      "error_rate": float,
      "avg_error_magnitude_cp": float,
      "sample_positions": [
        {
          "game_id": str, "white": str, "black": str,
          "player_color": "white"|"black",
          "game_url": str, "date": str, "move_number": int,
          "fen": str, "move_played": str, "best_move": str,
          "eval_before": int, "eval_after": int,
          "error_magnitude": float
        }
      ]
    }
  ]
}
```
(`metadata` é adicionado por `main._build_profile_phase`; os campos novos de
`sample_positions` são opcionais — perfis antigos sem eles continuam funcionando.)

### `modules/ai_diagnostician.py`
```python
load_silman_concepts(path: str = "data/silman_concepts.json") -> dict
# Retorna dict indexado por detection_key.

diagnose(player_profile: dict, silman_concepts: dict) -> dict
```

Modelo e limite de tokens vêm de `config.py` (`ANTHROPIC_MODEL = "claude-opus-4-6"`,
`ANTHROPIC_MAX_TOKENS = 8192`). A chamada à API tem retry com backoff exponencial em
erros transitórios (rate limit / 5xx / conexão) e extração robusta de JSON via
`_extract_json()`. Levanta `RuntimeError` se `ANTHROPIC_API_KEY` não estiver definida.

O diagnóstico é retornado em formato **bilíngue** via uma única chamada à API:

```json
{
  "en": {
    "root_cause": {"id": str, "name": str, "description": str},
    "weakness_classification": [
      {"concept": str, "classification": "PRIMARY|SECONDARY|NOISE", "reasoning": str}
    ],
    "study_priority": [
      {"concept": str, "silman_chapter": int, "priority_rank": int, "reason": str,
       "silman_name": str, "silman_page": int, "silman_description": str}
    ],
    "cognitive_pattern": str,
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "pt": { ... mesma estrutura em português ... }
}
```

A página `diagnosis.py` lê `diagnosis_raw.get(lang, diagnosis_raw.get("en", {}))`,
mantendo compatibilidade com arquivos antigos em formato flat.

### `modules/db.py`
```python
db = Database()                    # default: data/profiler.db (WAL mode)
db = Database("custom/path.db")

# Cache Stockfish
db.cache_eval(fen, depth, score_cp, best_move)
db.get_cached_eval(fen, depth) -> dict | None   # {"score_cp": int, "best_move": str}
db.cache_stats() -> {"cached_evals": int}

# Posições
pos_id = db.insert_position(pos_dict) -> int
db.find_position(fen, move_played, white, black, source) -> int | None
# Dedupe: _persist_games_to_db consulta antes de inserir — re-análises do mesmo
# jogador não duplicam posições nem resultados de análise.
db.query_positions(min_rating, max_rating, eco, opening_name, player_color, source, limit) -> list
db.count_positions() -> int

# Resultados de análise
db.insert_analysis_results_bulk(rows)  # rows: list de (pos_id, concept_key, detected, details, is_error, magnitude)
db.get_analysis_results(position_id) -> list
db.concept_error_summary() -> list    # agrega erros por conceito em todos os resultados

db.close()  # ou use como context manager (with Database() as db:)
```

**Schema SQLite:**
- `fen_cache (fen, depth, score_cp, best_move, analyzed_at)` — PK: (fen, depth)
- `positions (id, fen, move_number, move_played, player_color, white, black, white_rating, black_rating, opening, eco, game_url, source, imported_at)`
- `analysis_results (id, position_id→positions, concept_key, detected, details_json, is_error, error_magnitude, analyzed_at)`

---

## Pipeline Principal (`main.py`)

Duas funções públicas + `_main(argv=None)` com argparse (testável via `_main(["--user", ...])`):

```python
analyze_player(pgn_path, player_name, player_color=chess.WHITE, on_progress=None)
# → (profile_dict, diagnosis_dict)
# Salva output/{player_name}_profile.json e output/{player_name}_diagnosis.json

analyze_player_from_username(username, n_games=50, on_progress=None)
# → (profile_dict, diagnosis_dict)
```

Sequência interna:
1. Carrega partidas (PGN ou Chess.com), extraindo metadados dos headers
   (Link → game_url, UTCDate/Date, ECO, ECOUrl → opening, WhiteElo/BlackElo)
2. Abre **uma única instância** do Stockfish para todas as partidas
3. Por jogo: pula os primeiros `OPENING_MOVES_TO_SKIP` lances completos →
   `detect_concepts()` em cada posição → `batch_validate()` (duas passadas)
   apenas nas posições com pelo menos um conceito detectado
4. Persiste tudo no SQLite via `_persist_games_to_db()` (com dedupe)
5. `build_profile()` — aplica `is_instructive()` como gate causal; adiciona
   `generated_at`; `_build_profile_phase` anexa `metadata` (player/source/depth)
6. `diagnose()` — chama Claude, retorna diagnóstico bilíngue

`on_progress(stage, current, total, message)` — callback opcional para a UI do Streamlit
exibir progresso. Stages: `"fetch"`, `"load"`, `"game"`, `"profile"`, `"ai"`, `"done"`.

---

## Interface Web (`app.py` + `ui/`)

Arquitetura de **página única com scroll contínuo**. `app.py` chama `render()` de cada
módulo em sequência, separados por `st.divider()`.

```
app.py
 ├── sidebar: seletor de idioma + seletor de perfil ativo + nav links
 ├── render_home()     → ui/pages/home.py      #home
 ├── render_analyze()  → ui/pages/analyze.py   #analyze
 ├── render_profile()  → ui/pages/profile.py   #profile-dashboard
 ├── render_explorer() → ui/pages/explorer.py  #game-explorer
 ├── render_diagnosis()→ ui/pages/diagnosis.py #diagnosis-report
 └── scroll-spy JS: detecta âncora ativa e aplica highlight no nav da sidebar
```

**Scroll-spy:** `components.html(height=0)` injeta script no frame pai que registra
listener de scroll em `[data-testid="stMain"]`. Listener idempotente via
`window.parent._spyListener` / `_spyEl`. Aplica `color:#ff4b4b` + `border-left` ao
link ativo da sidebar.

**Perfil ativo** (`st.session_state.active_profile`): string com o nome do arquivo
`{user}_profile.json` em `output/`. Todas as páginas lêem desse estado. O seletor
na sidebar sincroniza automaticamente.

**i18n (`ui/i18n.py`):**
```python
t("chave")                # retorna string no idioma atual (st.session_state.lang)
t("chave", param=valor)   # com interpolação
# 107 chaves, EN e PT-BR simétricas
# Idioma: st.radio com key="lang" → persiste em session_state
```

**Nomes de conceito localizados (`ui/concepts.py`):**
```python
concept_label(key)       # nome do conceito no idioma ativo (name/name_en do JSON)
concept_category(key)    # categoria Silman canônica (PT)
category_label(category) # categoria traduzida (CATEGORY_LABELS, 6 categorias)
```
Toda a UI (tabela, gráficos, explorer) usa `concept_label()` em vez de
`detection_key.title()`.

**Melhorias da UI:**
- Explorer: lances em SAN (`board.san`), número do lance, avaliação antes→depois,
  data e oponente no título do expander, link para a partida no Chess.com
  (`game_url`), cache do "Ask AI" por FEN+idioma.
- Profile Dashboard: caption com `generated_at`/fonte/profundidade, radar Plotly
  de erros por categoria Silman (`build_category_radar`) e comparação de perfis
  lado a lado (`build_comparison_chart`, multiselect de 2+ perfis).
- Analyze: upload de PGN via `tempfile.NamedTemporaryFile` (sem colisão de nomes).

---

## Módulo Não Integrado

**`modules/fen_fetcher.py`** — busca posições FEN do Chess.com com filtros ricos
(min/max_rating, ECO, opening_name, move_range, time_class). Usado apenas por
`eval_fen.py` (debug). Não faz parte do pipeline principal, mas a interface é
compatível com `db.py` (`insert_positions_bulk`).

---

## Base de Conhecimento (`data/silman_concepts.json`)

18 conceitos: 17 estratégicos extraídos manualmente de *The Amateur's Mind* + 1 tático
derivado (`missed_tactic`). Cada entrada:
```json
{
  "id": "weak_square",
  "name": "Casa Fraca",
  "silman_chapter": 3,
  "silman_page": 67,
  "silman_category": "desequilíbrios estáticos",
  "description": "...",
  "strategic_implications": "...",
  "detection_key": "weak_square"
}
```

Os 3 conceitos adicionados após os 14 originais:
- `hanging_piece` — "Peça Pendurada", cap. 1 p. 26, categoria dinâmica
- `backward_pawn` — "Peão Atrasado", cap. 5 p. 109, estrutura de peões
- `center_control` — "Controle do Centro", cap. 2 p. 35, desequilíbrios estáticos

Conceito tático derivado (atribuído por gate de precedência, não por detector de posição):
- `missed_tactic` — "Tática Perdida", cap. 1 p. 26, categoria tática. Captura erros em
  que o jogador deixou passar uma captura que ganhava material (ex.: peça pendurada do
  adversário). Antes, esses erros vazavam para conceitos estratégicos (tipicamente
  `weak_square`) por co-ocorrência. A taxa de erro desse conceito tende a ~100% pois
  ele só é registrado quando há erro (não acumula `total_occurrences` de posições corretas).

---

## Testes

```bash
pytest                                  # 269 testes, todos passando
pytest -v --tb=short
pytest tests/test_position_analyzer.py  # 78 testes com FENs conhecidas
pytest tests/test_pipeline_e2e.py -v    # integração real (requer Stockfish)
```

Cobertura por arquivo:

| Arquivo | Testes | Escopo |
|---------|--------|--------|
| `test_position_analyzer.py` | 78 | FENs específicas para os 17 detectores + `static_exchange_gain` (SEE) |
| `test_profile_builder.py` | 27 | Checkmates; precedência `missed_tactic`; denominador de oportunidades |
| `test_stockfish_validator.py` | 23 | Mock `popen_uci`, cache, guards ΔWinP, passada de confirmação/MultiPV |
| `test_concept_relevance.py` | 20 | Gates causais, scoring, `is_missed_tactic`/`is_converted_tactic` via SEE |
| `test_chess_com_loader.py` | 16 | Mock HTTP, detecção de cor, limite n_games |
| `test_app.py` | 15 | AppTest: startup, i18n, estado vazio, fixture com perfil |
| `test_ai_diagnostician.py` | 14 | Mock cliente Anthropic, formato bilíngue EN/PT |
| `test_pipeline_e2e.py` | 13 | Integração real Stockfish; `@skip_no_sf` se binário ausente |
| `test_db.py` | 12 | Cache, posições, `find_position`, resultados de análise |
| `test_pgn_loader.py` | 11 | Parsing PGN, iteração de posições |
| `test_cli.py` | 11 | `_main(argv=...)`, roteamento pgn vs username, flags |
| `test_main.py` | 10 | Mocks de `batch_validate`, `detect_concepts`, `diagnose`, `fetch_recent_games` |
| `test_diagnosis_card.py` | 6 | `format_root_cause`, `format_weakness_table`, `format_study_priority` |
| `test_weakness_chart.py` | 6 | Figuras Plotly, ordenação, lista vazia |
| `test_config.py` | 4 | Valores e tipos dos thresholds |
| `test_ui_dependencies.py` | 3 | Importabilidade dos módulos UI |

---

## Validação com Dados Reais

Três jogadores processados pelo pipeline (2026-05-13):

| Jogador | Rating (blitz) | Partidas | Posições | Taxa de erro | Fraquezas |
|---------|---------------|----------|----------|-------------|-----------|
| diogenesdie | ~519 rapid | 30 | 985 | 32,8% | 10 |
| sprandel1 | ~1295 blitz | 30 | 1.119 | 26,1% | 7 |
| Sprandel27 | ~1555 rapid | 20 | 527 | 21,8% | 3 |

Observações:
- Taxa de erro inversamente proporcional ao rating (32,8% → 26,1% → 21,8%)
- `hanging_piece` domina o perfil mais baixo (29 erros); ausente nos dois mais altos
- `king_safety` e `overloaded_piece` recorrentes nos 3 perfis
- Diagnósticos Claude com confiança HIGH nos 3 casos; causas raiz distintas e coerentes

**Re-validação após o endurecimento das regras (2026-07-02, diogenesdie, 20 partidas):**

| Métrica | Regras antigas | Regras novas |
|---------|---------------|--------------|
| Taxa de erro global | 35,5% | 13,4% |
| Fraquezas recorrentes | 8 | 5 |
| Conceito dominante | hanging_piece 18 / open_file 10 / weak_square 8 | missed_tactic 8 (12% das oportunidades) / hanging_piece 6 / weak_square 5 |

A queda na taxa de erro vem de três fontes: skip de abertura (menos posições, menos
ruído), ΔWinP (swings em posições decididas descartados) e passada de confirmação
(falsos positivos de horizonte eliminados em depth 16). O perfil resultante é mais
enxuto e o sinal tático (missed_tactic/hanging_piece) fica corretamente no topo para
um jogador ~500.

---

## Notas Acadêmicas (TCC)

- Arquitetura híbrida de três camadas: detecção determinística → validação quantitativa → raciocínio causal
- O LLM não gera texto pedagógico — atua como componente de raciocínio que classifica dados quantitativos brutos
- Erro definido por queda de **probabilidade de vitória** (ΔWinP, modelo do Lichess),
  não por centipawns brutos — normaliza o significado do erro pelo contexto da posição
  e substitui heurísticas ad-hoc ("posição já decidida") por um critério único citável
- Validação em **duas passadas** (triagem rasa + confirmação profunda com MultiPV=2):
  compromisso custo/precisão que elimina falsos positivos de efeito horizonte
- Detectores usam **SEE** (static exchange evaluation) para raciocínio material
  (peça pendurada, tática perdida/convertida) em vez de heurísticas de 1 lance
- `is_instructive()` estabelece vínculo causal entre erro e conceito (vs. mera co-ocorrência)
- Precedência tática (`is_missed_tactic()`): erros táticos (captura ganhadora recusada) são
  separados dos estratégicos via conceito `missed_tactic`, evitando que vazem para conceitos
  como `weak_square` por co-ocorrência estrutural — distingue falha de visão tática de
  incompreensão estratégica
- A base de conhecimento do Silman é extraída manualmente para preservar fidelidade interpretativa
- Diagnóstico bilíngue (EN/PT-BR) via uma única chamada à API, retrocompatível com arquivos legacy
- Validação com jogadores reais do Chess.com em faixas de rating 400–1600
