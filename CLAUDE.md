# CLAUDE.md — Chess Strategic Profiler
## Instruções para Claude Code

Este documento define a implementação completa do sistema de diagnóstico estratégico
personalizado de xadrez, desenvolvido como TCC de Sistemas de Informação (FACCAT).

---

## Visão Geral do Sistema

O sistema analisa partidas de um jogador em formato PGN, detecta padrões de fraqueza
estratégica recorrentes usando regras determinísticas (python-chess + Stockfish), e usa
um LLM para identificar a causa raiz por trás dos sintomas detectados, conectando o
diagnóstico aos conceitos pedagógicos do livro "The Amateur's Mind" de Jeremy Silman.

**Stack:** Python 3.10+, python-chess, Stockfish (binário local), Anthropic API

---

## Estrutura de Diretórios a Criar

```
chess_profiler/
├── CLAUDE.md                  ← este arquivo
├── requirements.txt
├── config.py                  ← caminhos e configurações
├── data/
│   └── silman_concepts.json   ← base de conhecimento do Silman
├── modules/
│   ├── pgn_loader.py          ← carrega e itera partidas PGN
│   ├── position_analyzer.py   ← detecção de conceitos por posição
│   ├── stockfish_validator.py ← valida se houve erro real na posição
│   ├── profile_builder.py     ← acumula perfil de fraquezas do jogador
│   └── ai_diagnostician.py   ← LLM identifica causa raiz
├── main.py                    ← pipeline principal
└── output/
    └── (relatórios gerados)
```

---

## Passo 1 — requirements.txt

```
chess
anthropic
python-dotenv
```

---

## Passo 2 — config.py

```python
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
```

---

## Passo 3 — data/silman_concepts.json

Criar este arquivo com a base de conhecimento extraída manualmente do Silman.
Usar esta estrutura para cada conceito:

```json
{
  "concepts": [
    {
      "id": "weak_square",
      "name": "Casa Fraca",
      "silman_chapter": 3,
      "silman_page": 67,
      "silman_category": "desequilíbrios estáticos",
      "description": "Casa que não pode ser defendida por peões e pode ser ocupada por peças adversárias.",
      "strategic_implications": "Permite infiltração de cavalos e bispos adversários em posições fixas.",
      "detection_key": "weak_square"
    },
    {
      "id": "open_file",
      "name": "Coluna Aberta",
      "silman_chapter": 4,
      "silman_page": 89,
      "silman_category": "desequilíbrios dinâmicos",
      "description": "Coluna sem peões de nenhuma das cores, ideal para torres.",
      "strategic_implications": "Quem controla colunas abertas controla o espaço e penetração.",
      "detection_key": "open_file"
    },
    {
      "id": "isolated_pawn",
      "name": "Peão Isolado",
      "silman_chapter": 5,
      "silman_page": 112,
      "silman_category": "estrutura de peões",
      "description": "Peão sem peões aliados nas colunas adjacentes.",
      "strategic_implications": "Fraqueza permanente que requer defesa passiva. Adversário pressiona essa fraqueza.",
      "detection_key": "isolated_pawn"
    },
    {
      "id": "bishop_pair",
      "name": "Par de Bispos",
      "silman_chapter": 6,
      "silman_page": 134,
      "silman_category": "desequilíbrios de material",
      "description": "Possuir dois bispos enquanto o adversário tem cavalo(s) ou bispo único.",
      "strategic_implications": "Vantagem em posições abertas. Devem ser ativados abrindo o jogo.",
      "detection_key": "bishop_pair"
    },
    {
      "id": "knight_outpost",
      "name": "Cavalo em Posto Avançado",
      "silman_chapter": 3,
      "silman_page": 71,
      "silman_category": "desequilíbrios estáticos",
      "description": "Cavalo em casa fraca no campo adversário, protegido por peão.",
      "strategic_implications": "Cavalo fixo no centro ou campo adversário é uma vantagem posicional duradoura.",
      "detection_key": "knight_outpost"
    },
    {
      "id": "king_safety",
      "name": "Segurança do Rei",
      "silman_chapter": 7,
      "silman_page": 156,
      "silman_category": "dinâmica",
      "description": "Avaliação da exposição do rei baseada em cobertura de peões e atividade adversária.",
      "strategic_implications": "Rei exposto prioriza ataque imediato. Desequilíbrio que supera fatores posicionais.",
      "detection_key": "king_safety"
    },
    {
      "id": "space_advantage",
      "name": "Vantagem de Espaço",
      "silman_chapter": 8,
      "silman_page": 178,
      "silman_category": "desequilíbrios estáticos",
      "description": "Controle de mais casas no tabuleiro, especialmente no centro.",
      "strategic_implications": "Mais espaço = mais opções de manobra e restrição das peças adversárias.",
      "detection_key": "space_advantage"
    }
  ]
}
```

---

## Passo 4 — modules/pgn_loader.py

```python
import chess.pgn
import io

def load_games_from_file(pgn_path: str) -> list:
    """
    Carrega todas as partidas de um arquivo PGN.
    Retorna lista de objetos chess.pgn.Game.
    """
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            games.append(game)
    print(f"[pgn_loader] {len(games)} partidas carregadas de {pgn_path}")
    return games


def load_games_from_string(pgn_string: str) -> list:
    """
    Carrega partidas a partir de uma string PGN.
    Útil para testes sem arquivo.
    """
    games = []
    pgn_io = io.StringIO(pgn_string)
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break
        games.append(game)
    return games


def iterate_positions(game, player_color: bool):
    """
    Itera sobre todas as posições de uma partida onde é a vez do jogador analisado.
    Yields: (board_before, move_played, board_after)
    
    player_color: chess.WHITE ou chess.BLACK
    """
    board = game.board()
    for move in game.mainline_moves():
        if board.turn == player_color:
            board_before = board.copy()
            board.push(move)
            board_after = board.copy()
            yield board_before, move, board_after
        else:
            board.push(move)
```

---

## Passo 5 — modules/position_analyzer.py

```python
import chess

def detect_concepts(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta conceitos estratégicos presentes numa posição.
    Retorna dicionário com conceitos detectados e seus detalhes.
    
    board: posição ANTES do lance do jogador
    player_color: cor do jogador sendo analisado
    """
    results = {}

    results["weak_square"] = detect_weak_squares(board, player_color)
    results["open_file"] = detect_open_files(board, player_color)
    results["isolated_pawn"] = detect_isolated_pawns(board, player_color)
    results["bishop_pair"] = detect_bishop_pair(board, player_color)
    results["knight_outpost"] = detect_knight_outpost(board, player_color)
    results["king_safety"] = detect_king_safety(board, player_color)
    results["space_advantage"] = detect_space_advantage(board, player_color)

    return results


def detect_weak_squares(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta casas fracas no campo do jogador (casas que seus peões não defendem).
    Uma casa fraca é aquela que nenhum peão aliado pode atacar agora ou futuramente.
    """
    weak_squares = []
    opponent_color = not player_color

    for square in chess.SQUARES:
        file = chess.square_file(square)
        rank = chess.square_rank(square)

        # Foca no campo do jogador (metade do tabuleiro)
        if player_color == chess.WHITE and rank < 4:
            continue
        if player_color == chess.BLACK and rank > 3:
            continue

        # Verifica se nenhum peão aliado pode defender essa casa
        can_be_defended = False
        for adj_file in [file - 1, file + 1]:
            if 0 <= adj_file <= 7:
                for r in range(8):
                    sq = chess.square(adj_file, r)
                    piece = board.piece_at(sq)
                    if piece and piece.piece_type == chess.PAWN and piece.color == player_color:
                        can_be_defended = True
                        break

        if not can_be_defended:
            # Verifica se o adversário tem peça que poderia ocupar essa casa
            if board.is_attacked_by(opponent_color, square):
                weak_squares.append(chess.square_name(square))

    return {
        "detected": len(weak_squares) > 0,
        "squares": weak_squares,
        "count": len(weak_squares)
    }


def detect_open_files(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta colunas abertas e semi-abertas.
    Verifica se o jogador tem torres/dama posicionadas para aproveitá-las.
    """
    open_files = []
    semi_open_files = []

    for file_idx in range(8):
        file_name = chess.FILE_NAMES[file_idx]
        white_pawn = False
        black_pawn = False

        for rank_idx in range(8):
            sq = chess.square(file_idx, rank_idx)
            piece = board.piece_at(sq)
            if piece and piece.piece_type == chess.PAWN:
                if piece.color == chess.WHITE:
                    white_pawn = True
                else:
                    black_pawn = True

        if not white_pawn and not black_pawn:
            open_files.append(file_name)
        elif player_color == chess.WHITE and not white_pawn and black_pawn:
            semi_open_files.append(file_name)
        elif player_color == chess.BLACK and not black_pawn and white_pawn:
            semi_open_files.append(file_name)

    # Verifica se o jogador tem torre/dama nessas colunas
    has_rook_on_open = False
    for file_name in open_files + semi_open_files:
        file_idx = chess.FILE_NAMES.index(file_name)
        for rank_idx in range(8):
            sq = chess.square(file_idx, rank_idx)
            piece = board.piece_at(sq)
            if piece and piece.color == player_color and piece.piece_type in [chess.ROOK, chess.QUEEN]:
                has_rook_on_open = True
                break

    return {
        "detected": len(open_files) > 0 or len(semi_open_files) > 0,
        "open_files": open_files,
        "semi_open_files": semi_open_files,
        "player_has_rook_on_open": has_rook_on_open
    }


def detect_isolated_pawns(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta peões isolados do jogador.
    Peão isolado: sem peões aliados nas colunas adjacentes.
    """
    isolated = []

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.piece_type != chess.PAWN or piece.color != player_color:
            continue

        file = chess.square_file(square)
        has_neighbor = False

        for adj_file in [file - 1, file + 1]:
            if 0 <= adj_file <= 7:
                for rank in range(8):
                    sq = chess.square(adj_file, rank)
                    p = board.piece_at(sq)
                    if p and p.piece_type == chess.PAWN and p.color == player_color:
                        has_neighbor = True
                        break

        if not has_neighbor:
            isolated.append(chess.square_name(square))

    return {
        "detected": len(isolated) > 0,
        "squares": isolated,
        "count": len(isolated)
    }


def detect_bishop_pair(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta se o jogador tem par de bispos enquanto o adversário não.
    """
    opponent_color = not player_color

    player_bishops = sum(1 for sq in chess.SQUARES
                        if board.piece_at(sq) and
                        board.piece_at(sq).piece_type == chess.BISHOP and
                        board.piece_at(sq).color == player_color)

    opponent_bishops = sum(1 for sq in chess.SQUARES
                          if board.piece_at(sq) and
                          board.piece_at(sq).piece_type == chess.BISHOP and
                          board.piece_at(sq).color == opponent_color)

    has_pair = player_bishops >= 2
    opponent_has_pair = opponent_bishops >= 2

    return {
        "detected": has_pair and not opponent_has_pair,
        "player_bishops": player_bishops,
        "opponent_bishops": opponent_bishops
    }


def detect_knight_outpost(board: chess.Board, player_color: bool) -> dict:
    """
    Detecta cavalos do jogador em postos avançados (casas fracas no campo adversário).
    """
    opponent_color = not player_color
    outposts = []

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.piece_type != chess.KNIGHT or piece.color != player_color:
            continue

        rank = chess.square_rank(square)

        # Cavalo deve estar no campo adversário
        if player_color == chess.WHITE and rank < 4:
            continue
        if player_color == chess.BLACK and rank > 3:
            continue

        # Casa não pode ser atacada por peões adversários
        attacked_by_opponent_pawn = False
        file = chess.square_file(square)

        pawn_attack_ranks = [rank - 1] if player_color == chess.WHITE else [rank + 1]
        for pr in pawn_attack_ranks:
            if 0 <= pr <= 7:
                for pf in [file - 1, file + 1]:
                    if 0 <= pf <= 7:
                        sq = chess.square(pf, pr)
                        p = board.piece_at(sq)
                        if p and p.piece_type == chess.PAWN and p.color == opponent_color:
                            attacked_by_opponent_pawn = True

        if not attacked_by_opponent_pawn:
            outposts.append(chess.square_name(square))

    return {
        "detected": len(outposts) > 0,
        "squares": outposts
    }


def detect_king_safety(board: chess.Board, player_color: bool) -> dict:
    """
    Avalia a segurança do rei baseada em cobertura de peões.
    """
    king_square = board.king(player_color)
    if king_square is None:
        return {"detected": False, "exposed": False, "shield_pawns": 0}

    king_file = chess.square_file(king_square)
    king_rank = chess.square_rank(king_square)

    shield_pawns = 0
    pawn_ranks = [king_rank + 1] if player_color == chess.WHITE else [king_rank - 1]

    for pf in range(max(0, king_file - 1), min(8, king_file + 2)):
        for pr in pawn_ranks:
            if 0 <= pr <= 7:
                sq = chess.square(pf, pr)
                p = board.piece_at(sq)
                if p and p.piece_type == chess.PAWN and p.color == player_color:
                    shield_pawns += 1

    # Rei está exposto se tiver menos de 2 peões de escudo e ainda não roque
    has_castled = (player_color == chess.WHITE and king_file in [6, 2]) or \
                  (player_color == chess.BLACK and king_file in [6, 2])
    exposed = shield_pawns < 2

    return {
        "detected": exposed,
        "exposed": exposed,
        "shield_pawns": shield_pawns,
        "king_square": chess.square_name(king_square),
        "has_castled_position": has_castled
    }


def detect_space_advantage(board: chess.Board, player_color: bool) -> dict:
    """
    Calcula vantagem de espaço baseada em casas controladas no campo adversário.
    """
    opponent_color = not player_color
    player_space = 0
    opponent_space = 0

    for square in chess.SQUARES:
        rank = chess.square_rank(square)

        # Espaço no campo adversário (ranks 5-7 para brancas, 0-2 para pretas)
        if player_color == chess.WHITE and rank >= 4:
            if board.is_attacked_by(player_color, square):
                player_space += 1
        elif player_color == chess.BLACK and rank <= 3:
            if board.is_attacked_by(player_color, square):
                player_space += 1

        if opponent_color == chess.WHITE and rank >= 4:
            if board.is_attacked_by(opponent_color, square):
                opponent_space += 1
        elif opponent_color == chess.BLACK and rank <= 3:
            if board.is_attacked_by(opponent_color, square):
                opponent_space += 1

    advantage = player_space - opponent_space

    return {
        "detected": advantage > 5,
        "player_space": player_space,
        "opponent_space": opponent_space,
        "advantage": advantage
    }
```

---

## Passo 6 — modules/stockfish_validator.py

```python
import chess
import chess.engine
from config import STOCKFISH_PATH, STOCKFISH_DEPTH, ERROR_THRESHOLD_CP


def validate_move(board_before: chess.Board, move_played: chess.Move) -> dict:
    """
    Usa o Stockfish para validar se o lance jogado foi um erro.
    
    Compara a avaliação ANTES do lance (melhor lance possível) com a avaliação
    DEPOIS do lance jogado. Se a diferença superar ERROR_THRESHOLD_CP, é um erro.
    
    Retorna dicionário com:
    - is_error: bool
    - eval_before: centipawns antes (melhor lance)
    - eval_after: centipawns depois (lance jogado)
    - error_magnitude: diferença em centipawns
    - best_move: melhor lance segundo Stockfish
    """
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    try:
        # Avaliação da posição ANTES — pega o melhor lance
        info_before = engine.analyse(board_before, chess.engine.Limit(depth=STOCKFISH_DEPTH))
        score_before = info_before["score"].white().score(mate_score=10000)
        best_move = info_before["pv"][0] if "pv" in info_before else None

        # Posição DEPOIS do lance jogado
        board_after = board_before.copy()
        board_after.push(move_played)
        info_after = engine.analyse(board_after, chess.engine.Limit(depth=STOCKFISH_DEPTH))
        score_after = info_after["score"].white().score(mate_score=10000)

        # Para o jogador de pretas, a perspectiva é invertida
        if board_before.turn == chess.BLACK:
            error_magnitude = score_after - score_before  # positivo = piorou para pretas
        else:
            error_magnitude = score_before - score_after  # positivo = piorou para brancas

        is_error = error_magnitude > ERROR_THRESHOLD_CP

        return {
            "is_error": is_error,
            "eval_before": score_before,
            "eval_after": score_after,
            "error_magnitude": error_magnitude,
            "best_move": best_move.uci() if best_move else None
        }

    finally:
        engine.quit()


def batch_validate(positions: list) -> list:
    """
    Valida múltiplas posições reutilizando a mesma instância do Stockfish.
    positions: lista de (board_before, move_played)
    Retorna lista de dicts com resultados.
    """
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    results = []

    try:
        for board_before, move_played in positions:
            info_before = engine.analyse(board_before, chess.engine.Limit(depth=STOCKFISH_DEPTH))
            score_before = info_before["score"].white().score(mate_score=10000)
            best_move = info_before["pv"][0] if "pv" in info_before else None

            board_after = board_before.copy()
            board_after.push(move_played)
            info_after = engine.analyse(board_after, chess.engine.Limit(depth=STOCKFISH_DEPTH))
            score_after = info_after["score"].white().score(mate_score=10000)

            if board_before.turn == chess.BLACK:
                error_magnitude = score_after - score_before
            else:
                error_magnitude = score_before - score_after

            results.append({
                "is_error": error_magnitude > ERROR_THRESHOLD_CP,
                "eval_before": score_before,
                "eval_after": score_after,
                "error_magnitude": error_magnitude,
                "best_move": best_move.uci() if best_move else None
            })

    finally:
        engine.quit()

    return results
```

---

## Passo 7 — modules/profile_builder.py

```python
import json
from config import MIN_OCCURRENCES


def build_profile(games_data: list) -> dict:
    """
    Constrói o perfil de fraquezas do jogador a partir dos dados de todas as partidas.
    
    games_data: lista de dicts com:
        - game_id
        - positions: lista de dicts com concepts_detected + stockfish_validation
    
    Retorna perfil com contagens, aproveitamento e padrões.
    """
    concept_stats = {}
    total_positions = 0
    total_errors = 0

    for game in games_data:
        for position in game["positions"]:
            total_positions += 1
            validation = position["stockfish_validation"]
            concepts = position["concepts_detected"]

            if validation["is_error"]:
                total_errors += 1

                # Registra quais conceitos estavam presentes quando houve erro
                for concept_key, concept_data in concepts.items():
                    if concept_data.get("detected", False):
                        if concept_key not in concept_stats:
                            concept_stats[concept_key] = {
                                "total_occurrences": 0,
                                "error_occurrences": 0,
                                "total_error_magnitude": 0,
                                "positions": []
                            }
                        concept_stats[concept_key]["error_occurrences"] += 1
                        concept_stats[concept_key]["total_error_magnitude"] += validation["error_magnitude"]
                        concept_stats[concept_key]["positions"].append({
                            "game_id": game["game_id"],
                            "fen": position.get("fen"),
                            "error_magnitude": validation["error_magnitude"]
                        })
            else:
                # Registra ocorrências sem erro também (para calcular aproveitamento)
                for concept_key, concept_data in concepts.items():
                    if concept_data.get("detected", False):
                        if concept_key not in concept_stats:
                            concept_stats[concept_key] = {
                                "total_occurrences": 0,
                                "error_occurrences": 0,
                                "total_error_magnitude": 0,
                                "positions": []
                            }
                        concept_stats[concept_key]["total_occurrences"] += 1

    # Calcula métricas finais e filtra por relevância
    weaknesses = []
    for concept_key, stats in concept_stats.items():
        total_occ = stats["total_occurrences"] + stats["error_occurrences"]
        error_rate = stats["error_occurrences"] / total_occ if total_occ > 0 else 0
        avg_error = stats["total_error_magnitude"] / stats["error_occurrences"] if stats["error_occurrences"] > 0 else 0

        if stats["error_occurrences"] >= MIN_OCCURRENCES:
            weaknesses.append({
                "concept": concept_key,
                "total_occurrences": total_occ,
                "error_occurrences": stats["error_occurrences"],
                "error_rate": round(error_rate, 3),
                "avg_error_magnitude_cp": round(avg_error, 1),
                "sample_positions": stats["positions"][:3]  # máximo 3 exemplos
            })

    # Ordena por número de erros (mais frequente primeiro)
    weaknesses.sort(key=lambda x: x["error_occurrences"], reverse=True)

    return {
        "total_games": len(games_data),
        "total_positions_analyzed": total_positions,
        "total_errors_detected": total_errors,
        "overall_error_rate": round(total_errors / total_positions, 3) if total_positions > 0 else 0,
        "weaknesses": weaknesses
    }


def save_profile(profile: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"[profile_builder] Perfil salvo em {path}")


def load_profile(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

---

## Passo 8 — modules/ai_diagnostician.py

```python
import json
import anthropic
from config import ANTHROPIC_API_KEY


def load_silman_concepts(path: str = "data/silman_concepts.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["detection_key"]: c for c in data["concepts"]}


def diagnose(player_profile: dict, silman_concepts: dict) -> dict:
    """
    Usa o Claude para identificar a causa raiz das fraquezas recorrentes.
    
    O LLM recebe os dados quantitativos brutos e deve:
    1. Identificar o padrão subjacente (causa raiz)
    2. Classificar as fraquezas detectadas em primárias e secundárias
    3. Determinar quais fraquezas são sintomas de um problema maior
    4. Indicar prioridade de estudo no Silman
    
    Retorna JSON estruturado com o diagnóstico.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Prepara dados das fraquezas com contexto do Silman
    weaknesses_with_context = []
    for weakness in player_profile["weaknesses"]:
        concept_key = weakness["concept"]
        silman_info = silman_concepts.get(concept_key, {})
        weaknesses_with_context.append({
            **weakness,
            "silman_name": silman_info.get("name", concept_key),
            "silman_chapter": silman_info.get("silman_chapter"),
            "silman_category": silman_info.get("silman_category"),
            "silman_implications": silman_info.get("strategic_implications")
        })

    profile_summary = {
        "total_games": player_profile["total_games"],
        "total_positions_analyzed": player_profile["total_positions_analyzed"],
        "overall_error_rate": player_profile["overall_error_rate"],
        "weaknesses": weaknesses_with_context
    }

    prompt = f"""
Você é um analista de xadrez especializado em diagnóstico pedagógico estratégico.

Abaixo estão dados quantitativos brutos do perfil de fraquezas de um jogador,
coletados a partir da análise de {player_profile["total_games"]} partidas reais.

Sua tarefa NÃO é escrever um texto explicativo. É realizar um diagnóstico técnico
identificando padrões causais por trás dos sintomas detectados.

DADOS DO JOGADOR:
{json.dumps(profile_summary, indent=2, ensure_ascii=False)}

INSTRUÇÕES:
1. Analise as fraquezas e identifique se existe um padrão raiz que as conecta
   (ex: "pensamento estático", "ignorar desequilíbrios dinâmicos", "foco excessivo em tática")
2. Classifique cada fraqueza como: PRIMARY (causa principal), SECONDARY (sintoma de outra), NOISE (pouco relevante)
3. Determine a prioridade de estudo no Silman com base na causa raiz
4. Seja específico sobre o que o jogador NÃO está percebendo nas posições

Responda APENAS com JSON válido, sem texto antes ou depois:

{{
  "root_cause": {{
    "id": "identificador_snake_case",
    "name": "Nome do padrão identificado",
    "description": "Descrição técnica precisa do problema cognitivo/estratégico central"
  }},
  "weakness_classification": [
    {{
      "concept": "detection_key do conceito",
      "classification": "PRIMARY|SECONDARY|NOISE",
      "reasoning": "Por que essa classificação"
    }}
  ],
  "study_priority": [
    {{
      "concept": "detection_key",
      "silman_chapter": 0,
      "priority_rank": 1,
      "reason": "Por que estudar isso primeiro"
    }}
  ],
  "cognitive_pattern": "Descrição do padrão de pensamento que o jogador deve mudar",
  "confidence": "HIGH|MEDIUM|LOW"
}}
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Remove markdown code fences se presentes
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    diagnosis = json.loads(raw)

    # Enriquece o resultado com dados do Silman
    for item in diagnosis.get("study_priority", []):
        concept_key = item.get("concept")
        if concept_key in silman_concepts:
            sc = silman_concepts[concept_key]
            item["silman_name"] = sc.get("name")
            item["silman_page"] = sc.get("silman_page")
            item["silman_description"] = sc.get("description")

    return diagnosis
```

---

## Passo 9 — main.py

```python
import chess
import json
import os
from modules.pgn_loader import load_games_from_file, iterate_positions
from modules.position_analyzer import detect_concepts
from modules.stockfish_validator import batch_validate
from modules.profile_builder import build_profile, save_profile
from modules.ai_diagnostician import diagnose, load_silman_concepts

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def analyze_player(pgn_path: str, player_name: str, player_color: bool = chess.WHITE):
    """
    Pipeline completo de análise de um jogador.
    
    pgn_path: caminho para o arquivo PGN com as partidas
    player_name: nome do jogador (para identificação)
    player_color: chess.WHITE ou chess.BLACK
    """
    print(f"\n=== Iniciando análise de {player_name} ===\n")

    # 1. Carrega partidas
    games = load_games_from_file(pgn_path)

    # 2. Para cada partida, coleta posições e dados
    games_data = []
    for i, game in enumerate(games):
        print(f"[main] Processando partida {i + 1}/{len(games)}...")
        game_positions = []
        positions_to_validate = []

        for board_before, move_played, board_after in iterate_positions(game, player_color):
            concepts = detect_concepts(board_before, player_color)
            positions_to_validate.append((board_before.copy(), move_played))
            game_positions.append({
                "fen": board_before.fen(),
                "move_played": move_played.uci(),
                "concepts_detected": concepts,
                "stockfish_validation": None  # preenchido depois
            })

        # Valida todas as posições da partida em batch (1 instância do Stockfish)
        validations = batch_validate(positions_to_validate)
        for j, validation in enumerate(validations):
            game_positions[j]["stockfish_validation"] = validation

        games_data.append({
            "game_id": f"game_{i + 1}",
            "positions": game_positions
        })

    # 3. Constrói perfil de fraquezas
    print("\n[main] Construindo perfil de fraquezas...")
    profile = build_profile(games_data)
    save_profile(profile, f"{OUTPUT_DIR}/{player_name}_profile.json")

    print(f"\n[main] Resumo do perfil:")
    print(f"  Partidas analisadas: {profile['total_games']}")
    print(f"  Posições analisadas: {profile['total_positions_analyzed']}")
    print(f"  Taxa de erro global: {profile['overall_error_rate'] * 100:.1f}%")
    print(f"  Fraquezas recorrentes: {len(profile['weaknesses'])}")
    for w in profile["weaknesses"]:
        print(f"    - {w['concept']}: {w['error_occurrences']} erros ({w['error_rate']*100:.0f}% das ocorrências)")

    # 4. Diagnóstico pela IA
    print("\n[main] Executando diagnóstico por IA...")
    silman_concepts = load_silman_concepts()
    diagnosis = diagnose(profile, silman_concepts)

    diagnosis_path = f"{OUTPUT_DIR}/{player_name}_diagnosis.json"
    with open(diagnosis_path, "w", encoding="utf-8") as f:
        json.dump(diagnosis, f, indent=2, ensure_ascii=False)

    print(f"\n=== DIAGNÓSTICO FINAL ===")
    print(f"Causa raiz: {diagnosis['root_cause']['name']}")
    print(f"Descrição: {diagnosis['root_cause']['description']}")
    print(f"Confiança: {diagnosis['confidence']}")
    print(f"\nPrioridade de estudo (Silman):")
    for item in diagnosis.get("study_priority", []):
        print(f"  #{item['priority_rank']} — {item.get('silman_name', item['concept'])} "
              f"(Capítulo {item.get('silman_chapter', '?')}, p.{item.get('silman_page', '?')})")
        print(f"     Motivo: {item['reason']}")

    print(f"\nArquivos salvos em '{OUTPUT_DIR}/'")
    return profile, diagnosis


if __name__ == "__main__":
    # Exemplo de uso — ajustar pgn_path e player_name
    analyze_player(
        pgn_path="partidas.pgn",
        player_name="sprandel",
        player_color=chess.WHITE
    )
```

---

## Passo 10 — .env (criar na raiz do projeto)

```
ANTHROPIC_API_KEY=sua_chave_aqui
```

---

## Instruções de Execução para Claude Code

1. Criar toda a estrutura de diretórios e arquivos acima
2. Instalar dependências: `pip install chess anthropic python-dotenv`
3. Criar o arquivo `.env` com a chave da API Anthropic
4. Ajustar `STOCKFISH_PATH` em `config.py` para o caminho real
5. Preencher `data/silman_concepts.json` com os conceitos extraídos do livro
6. Colocar um arquivo `partidas.pgn` na raiz (exportar do Lichess ou Chess.com)
7. Executar: `python main.py`

---

## Notas Acadêmicas (para o TCC)

- O sistema implementa uma arquitetura híbrida de três camadas: detecção determinística (python-chess), validação quantitativa (Stockfish) e raciocínio causal (LLM)
- O LLM não gera texto pedagógico — ele atua como componente de raciocínio que classifica e interpreta dados quantitativos brutos
- A base de conhecimento do Silman (`silman_concepts.json`) é extraída manualmente, preservando a fidelidade interpretativa e o contexto pedagógico original
- A validação do sistema usa posições externas (Lichess/Chess.com) não vistas durante o desenvolvimento
