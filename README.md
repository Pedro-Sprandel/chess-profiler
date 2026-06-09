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
  → [2] Validação quantitativa    (stockfish_validator.py — centipawns, cache SQLite)
  → [3] Raciocínio causal          (ai_diagnostician.py — Claude classifica PRIMARY/SECONDARY/NOISE)
  → Perfil + Diagnóstico bilíngue (EN/PT) → Interface Streamlit
```

Documentação detalhada da arquitetura, módulos e decisões de design: ver [CLAUDE.md](CLAUDE.md).

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

Os perfis e diagnósticos gerados são salvos em `output/` como
`{user}_profile.json` e `{user}_diagnosis.json`.

## Testes

```bash
pytest                                # suíte completa
pytest tests/test_position_analyzer.py -v
pytest tests/test_pipeline_e2e.py -v  # integração real (requer Stockfish instalado)
```

## Estrutura

| Caminho | Descrição |
|---------|-----------|
| `main.py` | Pipeline CLI |
| `app.py` + `ui/` | Interface Streamlit (página única) |
| `config.py` | Caminhos, chaves e thresholds |
| `modules/` | Detecção, validação, diagnóstico, persistência |
| `data/silman_concepts.json` | Base de conhecimento (17 conceitos) |
| `tests/` | Suíte de testes |

## Licença / contexto acadêmico

Projeto desenvolvido como Trabalho de Conclusão de Curso. Uso educacional.
