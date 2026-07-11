"""
Gera o dataset de validação qualitativa do pipeline.

Por perfil, roda o pipeline completo em N partidas (default 10) e emite um documento
markdown com os lances-erro AGRUPADOS POR CONCEITO, cada um cruzado com o conceito
original de *The Amateur's Mind* (Silman), além do diagnóstico de causa raiz e do
plano de estudo gerados. Cada exemplo traz um campo de avaliação para a análise
qualitativa manual (coerência / sucesso / falha do pipeline).

Não persiste no banco (mantém data/profiler.db limpo) e grava os perfis/diagnósticos
frescos em output/qualitative/ para não sobrescrever os artefatos da etapa de validação.

Uso:
    python generate_qualitative_dataset.py
    python generate_qualitative_dataset.py --users sprandel1 Sprandel27 --games 10
    python generate_qualitative_dataset.py --out docs/qualitative_dataset.md
"""
import argparse
import json
import os
from datetime import date

from modules.chess_com_loader import fetch_recent_games
from modules.ai_diagnostician import diagnose, load_silman_concepts
from modules.profile_builder import build_profile, save_profile
from main import _process_games
from config import STOCKFISH_DEPTH

DEFAULT_USERS = ["diogenesdie", "sprandel1", "Sprandel27"]
DEFAULT_GAMES = 10
DEFAULT_OUT = "docs/qualitative_dataset.md"
PROFILE_DIR = "output/qualitative"


def run_profile(username: str, n_games: int, depth: int = STOCKFISH_DEPTH) -> tuple[dict, dict]:
    """Roda o pipeline fresco para um username e retorna (profile, diagnosis_pt-aware)."""
    print(f"\n=== {username}: buscando {n_games} partidas (Stockfish depth={depth}) ===")
    pairs = fetch_recent_games(username, n_games)
    print(f"[{username}] {len(pairs)} partidas. Analisando posições com Stockfish...")
    games_data = _process_games(pairs, depth=depth)
    profile = build_profile(games_data)

    os.makedirs(PROFILE_DIR, exist_ok=True)
    save_profile(profile, f"{PROFILE_DIR}/{username}_profile.json")

    print(f"[{username}] Rodando diagnóstico (1 chamada à API)...")
    silman = load_silman_concepts()
    diagnosis = diagnose(profile, silman)
    with open(f"{PROFILE_DIR}/{username}_diagnosis.json", "w", encoding="utf-8") as f:
        json.dump(diagnosis, f, indent=2, ensure_ascii=False)

    return profile, diagnosis


def lichess_link(fen: str) -> str:
    return f"https://lichess.org/analysis/{fen.replace(' ', '_')}"


def fmt_examples(positions: list) -> str:
    """Lista os lances-erro de um conceito, cada um com campo de avaliação manual."""
    lines = []
    for i, p in enumerate(positions, 1):
        lines += [
            f"**Exemplo {i}** — partida `{p['game_id']}` "
            f"({p['white']} vs {p['black']}, jogador de {p['player_color']})",
            "",
            f"- Lance jogado: `{p['move_played']}`  |  melhor lance: `{p['best_move']}`  "
            f"|  perda: **{p['error_magnitude']:.0f} cp**",
            f"- FEN: `{p['fen']}`",
            f"- Tabuleiro: [abrir no Lichess]({lichess_link(p['fen'])})",
            "- **Avaliação qualitativa:** _( ) detecção coerente com Silman   "
            "( ) falso positivo   — justificativa:_",
            "",
        ]
    return "\n".join(lines)


def build_concept_section(concept_key: str, weakness: dict, silman: dict) -> str:
    s = silman.get(concept_key, {})
    n = len(weakness["sample_positions"])
    lines = [
        f"### {s.get('name', concept_key)}  (`{concept_key}`)",
        "",
        f"- **Referência Silman:** cap. {s.get('silman_chapter', '?')}, "
        f"p. {s.get('silman_page', '?')} — categoria *{s.get('silman_category', '—')}*",
        f"- **Conceito:** {s.get('description', '—')}",
        f"- **Implicação estratégica:** {s.get('strategic_implications', '—')}",
        f"- **Detecções no perfil:** {weakness['error_occurrences']} erros em "
        f"{weakness['total_occurrences']} ocorrências "
        f"({weakness['error_rate']*100:.0f}%), magnitude média {weakness['avg_error_magnitude_cp']:.0f} cp",
        "",
        f"_Lances-erro detectados ({n}):_",
        "",
        fmt_examples(weakness["sample_positions"]),
    ]
    return "\n".join(lines)


def build_diagnosis_section(diagnosis: dict) -> str:
    d = diagnosis.get("pt", diagnosis.get("en", diagnosis))
    rc = d.get("root_cause", {})
    lines = [
        "#### Diagnóstico de causa raiz",
        "",
        f"- **Causa raiz:** {rc.get('name', '—')} (`{rc.get('id', '—')}`)",
        f"- **Descrição:** {rc.get('description', '—')}",
        f"- **Padrão cognitivo:** {d.get('cognitive_pattern', '—')}",
        f"- **Confiança:** {d.get('confidence', '—')}",
        "- **Avaliação qualitativa do diagnóstico:** "
        "_( ) coerente com os dados   ( ) discordo — justificativa:_",
        "",
        "**Classificação das fraquezas**",
        "",
        "| Conceito | Classificação | Justificativa (resumo) |",
        "|----------|---------------|------------------------|",
    ]
    for c in d.get("weakness_classification", []):
        reason = c.get("reasoning", "")[:90].replace("|", "/")
        lines.append(f"| {c['concept']} | {c['classification']} | {reason} |")
    lines += [
        "",
        "**Plano de estudo (prioridade)**",
        "",
        "| # | Conceito | Capítulo | Página | Motivo (resumo) |",
        "|---|----------|----------|--------|-----------------|",
    ]
    for sp in sorted(d.get("study_priority", []), key=lambda x: x.get("priority_rank", 99)):
        reason = sp.get("reason", "")[:80].replace("|", "/")
        lines.append(
            f"| {sp.get('priority_rank', '?')} | {sp['concept']} "
            f"| {sp.get('silman_chapter', '?')} | {sp.get('silman_page', '?')} | {reason} |"
        )
    lines += [
        "",
        "- **Avaliação qualitativa das recomendações:** "
        "_( ) relevantes e acionáveis   ( ) parcialmente   — justificativa:_",
        "",
    ]
    return "\n".join(lines)


def build_profile_section(idx: int, username: str, profile: dict, diagnosis: dict, silman: dict) -> str:
    p = profile
    lines = [
        f"## Perfil {idx} — {username}",
        "",
        "**Dados gerais**",
        "",
        "| Partidas | Posições | Erros | Taxa de erro | Fraquezas recorrentes |",
        "|----------|----------|-------|--------------|-----------------------|",
        f"| {p['total_games']} | {p['total_positions_analyzed']} | {p['total_errors_detected']} "
        f"| {p['overall_error_rate']*100:.1f}% | {len(p['weaknesses'])} |",
        "",
        build_diagnosis_section(diagnosis),
        "#### Detecções por conceito (lances-erro para análise qualitativa)",
        "",
    ]
    if not p["weaknesses"]:
        lines.append("_Nenhuma fraqueza recorrente (>= 3 erros) detectada nesta amostra._\n")
    for w in p["weaknesses"]:
        lines.append(build_concept_section(w["concept"], w, silman))
    return "\n".join(lines)


def build_header(users: list, n_games: int, depth: int) -> str:
    return "\n".join([
        "# Dataset de Validação Qualitativa — Chess Strategic Profiler",
        "",
        f"**Data:** {date.today().isoformat()}  ",
        f"**Perfis:** {len(users)} ({', '.join(users)})  ",
        f"**Partidas processadas por perfil:** {n_games}  ",
        f"**Engine:** Stockfish depth={depth}  |  **Diagnóstico:** Claude (claude-opus-4-6)",
        "",
        "---",
        "",
        "## Metodologia",
        "",
        "Para cada perfil, o pipeline processou as partidas mais recentes do Chess.com. "
        "Os lances classificados como erro pelo Stockfish e causalmente vinculados a um "
        "conceito (`is_instructive`) são listados abaixo, **agrupados pelo conceito de "
        "Silman** que o sistema atribuiu. Cada exemplo traz o lance jogado, o melhor lance, "
        "a perda em centipawns, a FEN e um link para inspeção visual.",
        "",
        "A análise qualitativa avalia, para uma amostra representativa por conceito:",
        "",
        "1. **Coerência das detecções** — o conceito atribuído corresponde de fato ao "
        "conceito original de Silman naquela posição? (sucesso vs. falso positivo)",
        "2. **Diagnóstico de causa raiz** — a causa raiz inferida é coerente com o padrão de erros?",
        "3. **Recomendações de estudo** — o plano de estudo é relevante e acionável?",
        "",
        "Os campos `( )` em cada exemplo são preenchidos manualmente durante a avaliação.",
        "",
        "> **Limitação declarada:** esta validação avalia a *precisão* das detecções "
        "realizadas (falsos positivos), não a *cobertura* (falsos negativos), já que "
        "lances sem detecção não entram na amostra.",
        "",
        "---",
        "",
    ])


def generate(users: list, n_games: int, depth: int, out_path: str):
    silman = load_silman_concepts()
    sections = [build_header(users, n_games, depth)]
    for i, user in enumerate(users, 1):
        profile, diagnosis = run_profile(user, n_games, depth)
        sections.append(build_profile_section(i, user, profile, diagnosis, silman))
        sections.append("\n---\n")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))
    print(f"\nDocumento gerado: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera dataset de validação qualitativa")
    parser.add_argument("--users", nargs="+", default=DEFAULT_USERS, help="Usernames do Chess.com")
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES, help="Partidas por perfil (default: 10)")
    parser.add_argument("--depth", type=int, default=STOCKFISH_DEPTH, help=f"Profundidade Stockfish (default: {STOCKFISH_DEPTH})")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"Saída markdown (default: {DEFAULT_OUT})")
    args = parser.parse_args()
    generate(args.users, args.games, args.depth, args.out)
