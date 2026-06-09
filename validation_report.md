# Relatório de Validação — Chess Strategic Profiler

**Data:** 2026-05-14  
**Jogadores analisados:** 3  
**Total de partidas:** 90  
**Total de posições:** 3001  
**Engine:** Stockfish depth=10  
**Modelo de diagnóstico:** claude-opus-4-6

---

## Metodologia

Pipeline executado via `python main.py --user <username> --games <n>` para cada jogador:

1. Partidas buscadas via API pública do Chess.com
2. Cada posição analisada pelos 17 detectores de conceitos Silman
3. Posições com conceito detectado validadas pelo Stockfish (centipawns)
4. Perfil de fraquezas construído com gate causal `is_instructive()`
5. Diagnóstico gerado pelo Claude classificando fraquezas em PRIMARY / SECONDARY / NOISE

---

## Perfil 1 — diogenesdie

**Dados gerais**

| Partidas | Posições | Erros | Taxa de erro | Fraquezas |
|----------|----------|-------|-------------|-----------|
| 10 | 405 | 146 | 36.0% | 9 |

**Fraquezas detectadas**

| Conceito | Erros | Ocorrências | Taxa | Avg cp |
|----------|-------|-------------|------|--------|
| hanging_piece | 12 | 98 | 12% | 319 |
| king_safety | 8 | 180 | 4% | 165 |
| weak_square | 8 | 148 | 5% | 376 |
| space_advantage | 6 | 55 | 11% | 234 |
| overloaded_piece | 5 | 35 | 14% | 181 |
| open_file | 5 | 200 | 2% | 175 |
| pawn_majority | 5 | 105 | 5% | 110 |
| piece_activity | 4 | 34 | 12% | 216 |
| center_control | 3 | 43 | 7% | 157 |

**Classificação das fraquezas**

| Conceito | Classificação | Justificativa |
|----------|--------------|---------------|
| hanging_piece | PRIMARY | Highest error rate (12.2%) with devastating average magnitude (319cp). The sampl |
| overloaded_piece | PRIMARY | Highest error rate in the dataset (14.3%) though lower sample size. The player f |
| piece_activity | SECONDARY | 11.8% error rate with 216cp average loss. The player sometimes chooses passive m |
| space_advantage | SECONDARY | 10.9% error rate but the sample positions reveal the errors are tactical, not st |
| weak_square | SECONDARY | 5.4% error rate with high magnitude (376cp) is inflated by a single 9480cp endga |
| king_safety | SECONDARY | Low error rate (4.4%) and moderate magnitude (165cp). The player doesn't systema |
| center_control | NOISE | Only 3 errors in 43 occurrences (7.0%) with modest 157cp average. The sample pos |
| open_file | NOISE | Lowest error rate (2.5%) with only 5 errors in 200 occurrences. The player gener |
| pawn_majority | NOISE | 4.8% error rate with low magnitude (110cp). The sample positions show the errors |

**Diagnóstico**

- **Causa raiz:** Failure to scan for threats before executing strategic ideas
- **ID:** `tactical_threat_blindness`
- **Confiança:** HIGH
- **Descrição:** The player consistently fails to perform a basic safety check ("Am I leaving pieces en prise? Is my opponent threatening something immediate?") before committing to a move. This manifests as hanging pieces (12.2% error rate, avg 319cp loss), but also cascades into overloaded piece errors (14.3%) and poor piece activity choices (11.8%). The player appears to have a rudimentary strategic sense—they attempt positional ideas—but executes them without first verifying tactical soundness. In multiple sample positions, the best move was a concrete tactical shot (e.g., d3c2 winning material, e4e3 activating the king with threats, e8e7 defending a critical piece) while the player chose aesthetically reasonable but tactically flawed alternatives. The 9000+ cp errors in game_4 and game_9 confirm catastrophic threat blindness in critical moments, not mere miscalculation but complete failure to consider the opponent's replies.
- **Padrão cognitivo:** The player operates with a 'strategy-first, tactics-never' thinking pattern. They look at the position, form a vague positional idea (activate a piece, improve structure, attack), and execute it without performing a final tactical verification. They do not systematically ask 'Is my piece safe after this move?' or 'What can my opponent do in response?' This results in a pattern where reasonable-looking moves collapse under simple tactical scrutiny. The catastrophic blunders (9000+ cp) reveal moments where the player is so absorbed in their own plan that they become completely blind to the opponent's immediate threats. The correction requires inserting a mandatory 'threat scan' step between plan formation and move execution: (1) What is my opponent threatening? (2) Does my intended move leave anything hanging? (3) Only then, execute.

**Plano de estudo Silman**

| Prioridade | Conceito | Capítulo | Página |
|-----------|----------|----------|--------|
| #1 | hanging_piece | 1 | 26 |
| #2 | overloaded_piece | 2 | 52 |
| #3 | piece_activity | 2 | 45 |
| #4 | space_advantage | 8 | 178 |
| #5 | weak_square | 3 | 67 |


---

## Perfil 2 — sprandel1

**Dados gerais**

| Partidas | Posições | Erros | Taxa de erro | Fraquezas |
|----------|----------|-------|-------------|-----------|
| 30 | 1119 | 292 | 26.1% | 7 |

**Fraquezas detectadas**

| Conceito | Erros | Ocorrências | Taxa | Avg cp |
|----------|-------|-------------|------|--------|
| king_safety | 16 | 412 | 4% | 125 |
| pawn_majority | 11 | 399 | 3% | 106 |
| space_advantage | 9 | 119 | 8% | 197 |
| overloaded_piece | 8 | 116 | 7% | 185 |
| piece_activity | 8 | 101 | 8% | 150 |
| open_file | 7 | 668 | 1% | 146 |
| weak_square | 6 | 254 | 2% | 184 |

**Classificação das fraquezas**

| Conceito | Classificação | Justificativa |
|----------|--------------|---------------|
| piece_activity | PRIMARY | Highest error rate (7.9%) and directly reflects the root cause. In nearly every  |
| space_advantage | PRIMARY | Second-highest error rate (7.6%) with the highest average error magnitude (197 c |
| overloaded_piece | SECONDARY | Error rate 6.9% with high magnitude (184.6 cp), but all three sample positions a |
| king_safety | SECONDARY | Error rate is low (3.9%) but the sample positions reveal the same pattern: in ga |
| pawn_majority | SECONDARY | Low error rate (2.8%) but the sample positions show the player missing active pa |
| weak_square | SECONDARY | Low error rate (2.4%) and the key errors (game_16: Ke4 and Kf5 instead of h6) sh |
| open_file | NOISE | Extremely low error rate (1.0%) across 668 occurrences, meaning the player handl |

**Diagnóstico**

- **Causa raiz:** Failure to recognize and exploit dynamic piece coordination in critical positions
- **ID:** `passive_piece_placement_under_dynamic_pressure`
- **Confiança:** HIGH
- **Descrição:** The player consistently chooses passive, defensive, or aimless piece placements when the position demands active, coordinated piece play. This manifests as an inability to identify when pieces should be redirected toward optimal squares (capturing key files, centralizing, or creating concrete threats) rather than making moves that appear safe but surrender dynamic potential. The root cognitive failure is evaluating positions through static/material lens when the position's character is fundamentally dynamic — the player does not calculate the concrete consequences of active moves and defaults to 'safe-looking' alternatives. This is especially visible in rook endgames and positions with exposed kings, where the player repeatedly places rooks on passive ranks/files instead of seizing open lines, capturing material via activity, or coordinating pieces against vulnerable targets.
- **Padrão cognitivo:** The player exhibits a systematic 'safety bias' in move selection: when faced with a choice between an active move requiring concrete calculation (capturing a central piece, seizing a back rank, pushing a passed pawn, exploiting an overloaded defender) and a passive move that appears to maintain the status quo (shuffling a rook sideways, retreating a queen, making a quiet king move), the player consistently chooses the passive option. This is particularly acute in rook endgames and positions with reduced material where piece activity is the dominant factor. The player appears to evaluate positions statically — counting material and looking for threats — rather than dynamically assessing which side's pieces are more actively placed. They do not ask 'what is the most active square for this piece?' or 'what concrete threat can I create right now?' Instead, they ask 'is this move safe?' This results in gradual positional deterioration as opponents accumulate activity advantages that the player never challenges. The critical perceptual gap is: the player does NOT see that a piece on an active square (e.g., rook on e4 attacking a piece and controlling a file) is worth far more than the same piece on a passive square (e.g., rook on h3 doing nothing), even when the active move involves apparent risk like entering the opponent's territory.

**Plano de estudo Silman**

| Prioridade | Conceito | Capítulo | Página |
|-----------|----------|----------|--------|
| #1 | piece_activity | 2 | 45 |
| #2 | overloaded_piece | 2 | 52 |
| #3 | space_advantage | 8 | 178 |
| #4 | pawn_majority | 8 | 185 |
| #5 | king_safety | 7 | 156 |
| #6 | weak_square | 3 | 67 |


---

## Perfil 3 — sprandel27

**Dados gerais**

| Partidas | Posições | Erros | Taxa de erro | Fraquezas |
|----------|----------|-------|-------------|-----------|
| 50 | 1477 | 392 | 26.5% | 8 |

**Fraquezas detectadas**

| Conceito | Erros | Ocorrências | Taxa | Avg cp |
|----------|-------|-------------|------|--------|
| hanging_piece | 25 | 239 | 10% | 174 |
| king_safety | 24 | 463 | 5% | 156 |
| backward_pawn | 22 | 391 | 6% | 133 |
| overloaded_piece | 19 | 182 | 10% | 209 |
| pawn_majority | 11 | 603 | 2% | 153 |
| open_file | 10 | 832 | 1% | 176 |
| space_advantage | 10 | 159 | 6% | 241 |
| weak_square | 8 | 303 | 3% | 198 |

**Classificação das fraquezas**

| Conceito | Classificação | Justificativa |
|----------|--------------|---------------|
| hanging_piece | PRIMARY | 10.5% error rate across 239 occurrences with 174 cp average magnitude. The sampl |
| overloaded_piece | PRIMARY | 10.4% error rate with the highest average magnitude at 209 cp. The player fails  |
| space_advantage | SECONDARY | 6.3% error rate but very high magnitude (240.8 cp). The player recognizes they h |
| king_safety | SECONDARY | 5.2% error rate with 156 cp magnitude. The player delays castling (game_1: Nc6 i |
| backward_pawn | SECONDARY | 5.6% error rate, 133 cp magnitude. In the sample positions, the player repeatedl |
| pawn_majority | NOISE | Only 1.8% error rate across 603 occurrences. The player handles pawn majorities  |
| open_file | NOISE | Only 1.2% error rate across 832 occurrences. The player generally uses open file |
| weak_square | NOISE | 2.6% error rate, only 8 errors across 303 occurrences. The sample positions are  |

**Diagnóstico**

- **Causa raiz:** Deficient Tactical Vigilance and Piece Interaction Awareness
- **ID:** `tactical_vigilance_deficit`
- **Confiança:** HIGH
- **Descrição:** The player systematically fails to scan for tactical vulnerabilities—both hanging pieces and overloaded defenders—before committing to a move. This is not a calculation depth problem but a pre-move safety check failure: the player selects moves based on strategic intent (advancing pawns, repositioning pieces) without first verifying whether their own pieces are safe and whether opponent pieces have exploitable defensive burdens. The high error rates in hanging_piece (10.5%) and overloaded_piece (10.4%), combined with the highest average error magnitudes (174 and 209 cp respectively), reveal that the player repeatedly walks into or allows tactical shots. The structural and positional weaknesses (backward_pawn, pawn_majority, space_advantage) are downstream effects: when the player does perceive strategic themes, they pursue them impulsively without checking tactical soundness, leading to material loss that nullifies any positional gains.
- **Padrão cognitivo:** The player operates with a 'strategy-first, tactics-second' thinking order that should be inverted. When choosing a move, the player identifies a strategic goal (advance a pawn, reposition a piece, press an advantage) and executes it without performing a final tactical safety verification. The critical missing step is a systematic post-selection check: 'Does my intended move leave any piece undefended? Does it overload any of my defenders? Does it expose my king?' The player also fails to scan the opponent's position for tactical vulnerabilities before committing—missing opportunities to exploit overloaded pieces and failing to notice when opponent threats demand immediate attention. The correction requires building a mandatory 'blunder check' habit as the last step before every move, and training the eye to detect undefended and overloaded pieces in both camps.

**Plano de estudo Silman**

| Prioridade | Conceito | Capítulo | Página |
|-----------|----------|----------|--------|
| #1 | hanging_piece | 1 | 26 |
| #2 | overloaded_piece | 2 | 52 |
| #3 | king_safety | 7 | 156 |
| #4 | backward_pawn | 5 | 109 |
| #5 | space_advantage | 8 | 178 |


---

## Análise Comparativa

| Jogador | Rating | Partidas | Posições | Taxa de erro | Fraquezas | Principal fraqueza | Causa raiz | Confiança |
|---------|--------|----------|----------|--------------|-----------|-------------------|------------|-----------|
| diogenesdie | ~519 (rapid) | 10 | 405 | 36.0% | 9 | hanging_piece | Failure to scan for threats before executing st... | HIGH |
| sprandel1 | ~1295 (blitz) | 30 | 1119 | 26.1% | 7 | king_safety | Failure to recognize and exploit dynamic piece ... | HIGH |
| sprandel27 | ~1217 (blitz) | 50 | 1477 | 26.5% | 8 | hanging_piece | Deficient Tactical Vigilance and Piece Interact... | HIGH |

### Causas raiz (completo)

- **diogenesdie (~519 (rapid)):** Failure to scan for threats before executing strategic ideas
- **sprandel1 (~1295 (blitz)):** Failure to recognize and exploit dynamic piece coordination in critical positions
- **sprandel27 (~1217 (blitz)):** Deficient Tactical Vigilance and Piece Interaction Awareness

### Observações

- Taxa de erro inversamente proporcional ao rating — o sistema captura progressão de nível sem calibração explícita.
- `king_safety` e `overloaded_piece` recorrentes em múltiplos perfis — fraquezas transversais em amadores.
- Diagnósticos Claude com confiança HIGH em todos os casos, causas raiz distintas e coerentes com os dados.