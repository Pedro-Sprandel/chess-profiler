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
Partidas (Chess.com API ou PGN)
        ↓
[1] Detecção determinística — position_analyzer.py
    17 detectores de conceitos Silman por posição (python-chess)
        ↓
[2] Validação quantitativa — stockfish_validator.py
    Confirma se houve erro real via Stockfish UCI (centipawns)
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
│   ├── silman_concepts.json        ← base de conhecimento: 17 conceitos em 5 categorias
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
│   ├── i18n.py                     ← 85 chaves EN/PT-BR, função t(key, **kwargs)
│   ├── components/
│   │   ├── weakness_chart.py       ← gráficos Plotly de erros por conceito (usa i18n)
│   │   └── diagnosis_card.py       ← formata output do diagnóstico
│   └── pages/
│       ├── home.py                 ← seção inicial (render())
│       ├── analyze.py              ← formulário Chess.com/PGN + progress bar
│       ├── profile.py              ← dashboard de métricas + gráficos
│       ├── explorer.py             ← tabuleiro SVG com setas de lance/melhor lance
│       └── diagnosis.py            ← causa raiz, classificação, plano de estudo
├── tests/
│   ├── test_position_analyzer.py   ← 59 testes com FENs conhecidas para os 17 detectores
│   ├── test_stockfish_validator.py ← 11 testes (mock popen_uci + cache)
│   ├── test_profile_builder.py     ← 10 testes
│   ├── test_concept_relevance.py   ← 10 testes
│   ├── test_ai_diagnostician.py    ← 9 testes (mock cliente Anthropic, formato bilíngue)
│   ├── test_chess_com_loader.py    ← 11 testes
│   ├── test_pgn_loader.py          ← 11 testes
│   ├── test_main.py                ← 10 testes (mocks externos)
│   ├── test_app.py                 ← 15 testes AppTest (5 classes, EN/PT, fixture com perfil)
│   ├── test_cli.py                 ← 11 testes CLI (_main com argv)
│   ├── test_pipeline_e2e.py        ← 13 testes integração (Stockfish real, @skip_no_sf)
│   ├── test_diagnosis_card.py      ← 6 testes
│   ├── test_weakness_chart.py      ← 6 testes
│   ├── test_config.py              ← 4 testes
│   └── test_ui_dependencies.py     ← 3 testes
└── output/                         ← perfis e diagnósticos gerados ({user}_profile.json, etc.)
```

---

## Configuração

**`config.py`**
```python
STOCKFISH_PATH = os.path.expanduser("~/stockfish/stockfish-ubuntu-x86-64-avx2")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
STOCKFISH_DEPTH = 10        # profundidade UCI; 10 é suficiente para erros estratégicos
ERROR_THRESHOLD_CP = 50     # diferença mínima em centipawns para classificar como erro
MIN_OCCURRENCES = 3         # mínimo de erros para uma fraqueza entrar no perfil
MAX_STAT_CP = 500           # cap de magnitude para estatísticas (evita distorção por posições de mate)
MATE_SCORE = 10000          # valor de cp atribuído a mate (mate_score do python-chess)
TACTICAL_THRESHOLD_CP = 9000  # acima disso a avaliação é considerada tática/decisiva
HTTP_TIMEOUT = 15           # timeout (s) das chamadas à API do Chess.com
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
pytest                          # 189 testes, todos passando
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
```

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

### `modules/stockfish_validator.py`
```python
open_engine() -> chess.engine.SimpleEngine
# Abre uma instância do Stockfish. Caller responsável por engine.quit().

validate_move(board_before, move_played) -> dict
# Abre/fecha engine internamente. Para uma posição isolada.

batch_validate(positions: list[tuple], engine=None) -> list[dict]
# positions: lista de (board_before, move_played)
# engine: instância existente (None = cria e fecha a própria)
# Resolve posições via cache SQLite antes de abrir o engine.
# Retorna lista de dicts: {is_error, eval_before, eval_after, error_magnitude, best_move}

evaluate_fen(fen: str, depth: int = STOCKFISH_DEPTH, use_cache: bool = True) -> dict
# {score_cp, score_side, is_mate, mate_in, best_move, depth, turn}
```

**Correção de falso positivo:** se `move_played == best_move`, `is_error` é forçado
a `False` independentemente da diferença de avaliação (efeito horizonte em profundidade fixa).

### `modules/concept_relevance.py`
```python
is_instructive(board_before, move_played_uci, best_move_uci, concept_key, player_color) -> bool
```

Três gates em ordem de custo crescente:
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
# Só conta um erro para um conceito se is_instructive() retornar True.
# Fraqueza só entra no perfil se error_occurrences >= MIN_OCCURRENCES (default: 3).
# error_magnitude é capeada em MAX_STAT_CP=500 para avg_error_magnitude_cp.

save_profile(profile: dict, path: str)
load_profile(path: str) -> dict
```

Estrutura de retorno do perfil:
```json
{
  "total_games": int,
  "total_positions_analyzed": int,
  "total_errors_detected": int,
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
          "fen": str, "move_played": str, "best_move": str,
          "error_magnitude": float
        }
      ]
    }
  ]
}
```

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
1. Carrega partidas (PGN ou Chess.com)
2. Abre **uma única instância** do Stockfish para todas as partidas
3. Por jogo: `detect_concepts()` em cada posição → `batch_validate()` apenas nas posições com pelo menos um conceito detectado
4. Persiste tudo no SQLite via `_persist_games_to_db()`
5. `build_profile()` — aplica `is_instructive()` como gate causal
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
# 85 chaves, EN e PT-BR simétricas
# Idioma: st.radio com key="lang" → persiste em session_state
```

---

## Módulo Não Integrado

**`modules/fen_fetcher.py`** — busca posições FEN do Chess.com com filtros ricos
(min/max_rating, ECO, opening_name, move_range, time_class). Usado apenas por
`eval_fen.py` (debug). Não faz parte do pipeline principal, mas a interface é
compatível com `db.py` (`insert_positions_bulk`).

---

## Base de Conhecimento (`data/silman_concepts.json`)

17 conceitos extraídos manualmente de *The Amateur's Mind*. Cada entrada:
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

---

## Testes

```bash
pytest                                  # 189 testes, todos passando
pytest -v --tb=short
pytest tests/test_position_analyzer.py  # 59 testes com FENs conhecidas
pytest tests/test_pipeline_e2e.py -v    # integração real (requer Stockfish)
```

Cobertura por arquivo:

| Arquivo | Testes | Escopo |
|---------|--------|--------|
| `test_position_analyzer.py` | 59 | FENs específicas para cada um dos 17 detectores |
| `test_app.py` | 15 | AppTest: startup, i18n, estado vazio, fixture com perfil |
| `test_pipeline_e2e.py` | 13 | Integração real Stockfish; `@skip_no_sf` se binário ausente |
| `test_stockfish_validator.py` | 11 | Mock `popen_uci`, cache via `_get_db` |
| `test_pgn_loader.py` | 11 | Parsing PGN, iteração de posições |
| `test_cli.py` | 11 | `_main(argv=...)`, roteamento pgn vs username, flags |
| `test_chess_com_loader.py` | 11 | Mock HTTP, detecção de cor, limite n_games |
| `test_profile_builder.py` | 10 | `make_position()` com `best_move=None` bypassa `is_instructive` |
| `test_main.py` | 10 | Mocks de `batch_validate`, `detect_concepts`, `diagnose`, `fetch_recent_games` |
| `test_concept_relevance.py` | 10 | Gates causais, scoring por conceito |
| `test_ai_diagnostician.py` | 9 | Mock cliente Anthropic, formato bilíngue EN/PT |
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

---

## Notas Acadêmicas (TCC)

- Arquitetura híbrida de três camadas: detecção determinística → validação quantitativa → raciocínio causal
- O LLM não gera texto pedagógico — atua como componente de raciocínio que classifica dados quantitativos brutos
- `is_instructive()` estabelece vínculo causal entre erro e conceito (vs. mera co-ocorrência)
- A base de conhecimento do Silman é extraída manualmente para preservar fidelidade interpretativa
- Diagnóstico bilíngue (EN/PT-BR) via uma única chamada à API, retrocompatível com arquivos legacy
- Validação com jogadores reais do Chess.com em faixas de rating 400–1600
