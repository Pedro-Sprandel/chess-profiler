# Chess Strategic Profiler

Sistema de diagnóstico estratégico personalizado de xadrez (TCC — Sistemas de
Informação, FACCAT). Analisa partidas de um jogador, detecta padrões de fraqueza
estratégica recorrentes com regras determinísticas (python-chess + Stockfish) e usa
um LLM para identificar a causa raiz, conectando o diagnóstico aos conceitos
pedagógicos de *The Amateur's Mind* (Jeremy Silman).

## Arquitetura

Pipeline de três camadas em sequência:

```
Partidas (Chess.com API ou PGN)
  → [1] Detecção determinística   (position_analyzer.py — 17 conceitos Silman)
  → [2] Validação quantitativa    (stockfish_validator.py — ΔWinP, linhas do engine, cache SQLite)
  → Atribuição erro → conceito     (attribution.py — tática primeiro, um conceito por erro;
                                    error_classifier.py — IA só para o que as regras não explicam)
  → [3] Raciocínio causal          (ai_diagnostician.py — Claude classifica PRIMARY/SECONDARY/NOISE)
  → Perfil + Diagnóstico bilíngue (EN/PT) → Interface Streamlit
```

Documentação detalhada da arquitetura, módulos e decisões de design: ver [CLAUDE.md](CLAUDE.md).
Precisão da atribuição erro → conceito (medição antes/depois e ablação):
[docs/precisao_atribuicao.md](docs/precisao_atribuicao.md).

## Requisitos

- Python 3.10+
- [Stockfish](https://stockfishchess.org/) (binário local) — caminho configurado em `config.py` (`STOCKFISH_PATH`)
- Chave da API da Anthropic

## Instalação

```bash
pip install -r requirements.txt

# Configure as credenciais
cp .env.example .env
# edite .env e preencha ANTHROPIC_API_KEY=sk-ant-...
# (opcional) DATABASE_URL=postgresql://... para guardar contas e análises no Postgres

# Ajuste STOCKFISH_PATH em config.py para o caminho do seu binário
```

## Uso

```bash
# Interface web (recomendada)
streamlit run app.py            # → http://localhost:8501

# CLI — busca N partidas recentes do Chess.com
python main.py --user sprandel --games 50

# CLI — analisa um arquivo PGN local
python main.py --user sprandel --pgn partidas.pgn --color white

# Avalia uma FEN manualmente (debug)
python eval_fen.py "<FEN>" --depth 15 --json
```

### Login e persistência

A interface exige login: cada pessoa cria uma conta (usuário + senha) e vê só as
próprias análises. O login fica lembrado no navegador (cookie, 30 dias por padrão).
A primeira conta criada vira administradora e recebe as análises salvas antes do login.

Contas, sessões e análises (perfil + diagnóstico) ficam no banco definido por
`DATABASE_URL` (PostgreSQL — dados persistentes de verdade, fora do servidor) ou, sem
ela, no SQLite local `data/profiler.db`. Para o deploy, ver [DEPLOY.md](DEPLOY.md).

```bash
python manage.py create-user ana          # cria conta pela linha de comando
python manage.py set-password ana         # redefine senha
python manage.py import-sqlite data/profiler.db --owner ana   # SQLite → Postgres
```

A CLI (`main.py`) também grava a análise no banco (`--owner ana` atribui a uma conta) e
exporta `output/{user}_profile.json` e `output/{user}_diagnosis.json`; arquivos antigos
em `output/` são importados automaticamente pela interface.

## Testes

```bash
pytest                                # suíte completa
pytest tests/test_position_analyzer.py -v
pytest tests/test_pipeline_e2e.py -v  # integração real (requer Stockfish instalado)

# Precisão da atribuição no conjunto de referência (requer Stockfish)
python scripts/evaluate_precision.py --baseline data/gold_baseline.json --details
```

## Estrutura

| Caminho | Descrição |
|---------|-----------|
| `main.py` | Pipeline CLI |
| `app.py` + `ui/` | Interface Streamlit (página única) |
| `config.py` | Caminhos, chaves, banco, login e thresholds |
| `manage.py` | Administração de contas e migração SQLite → Postgres |
| `modules/` | Detecção, validação, diagnóstico, persistência |
| `data/silman_concepts.json` | Base de conhecimento (17 conceitos) |
| `tests/` | Suíte de testes |

## Licença / contexto acadêmico

Projeto desenvolvido como Trabalho de Conclusão de Curso. Uso educacional.
