# Dataset de Validação Qualitativa — Chess Strategic Profiler

**Data:** 2026-06-22  
**Perfis:** 3 (diogenesdie, sprandel1, Sprandel27)  
**Partidas processadas por perfil:** 30  
**Engine:** Stockfish depth=15  |  **Diagnóstico:** Claude (claude-opus-4-6)

---

## Metodologia

Para cada perfil, o pipeline processou as partidas mais recentes do Chess.com. Os lances classificados como erro pelo Stockfish e causalmente vinculados a um conceito (`is_instructive`) são listados abaixo, **agrupados pelo conceito de Silman** que o sistema atribuiu. Cada exemplo traz o lance jogado, o melhor lance, a perda em centipawns, a FEN e um link para inspeção visual.

A análise qualitativa avalia, para uma amostra representativa por conceito:

1. **Coerência das detecções** — o conceito atribuído corresponde de fato ao conceito original de Silman naquela posição? (sucesso vs. falso positivo)
2. **Diagnóstico de causa raiz** — a causa raiz inferida é coerente com o padrão de erros?
3. **Recomendações de estudo** — o plano de estudo é relevante e acionável?

Os campos `( )` em cada exemplo são preenchidos manualmente durante a avaliação.

> **Limitação declarada:** esta validação avalia a *precisão* das detecções realizadas (falsos positivos), não a *cobertura* (falsos negativos), já que lances sem detecção não entram na amostra.

---

## Perfil 1 — diogenesdie

**Dados gerais**

| Partidas | Posições | Erros | Taxa de erro | Fraquezas recorrentes |
|----------|----------|-------|--------------|-----------------------|
| 30 | 981 | 244 | 24.9% | 9 |

#### Diagnóstico de causa raiz

- **Causa raiz:** Falha sistemática na varredura de capturas, ameaças e lances forçantes (`threat_blindness_and_capture_scan_failure`)
- **Descrição:** O jogador consistentemente falha em realizar uma varredura completa de capturas, xeques e ameaças táticas antes de selecionar um lance. Isso se manifesta como um déficit duplo: (1) não ver peças adversárias que estão indefesas ou taticamente vulneráveis (tática perdida, peça pendurada), e (2) não perceber ameaças ao próprio rei e peças, levando a roques atrasados e material desprotegido. A falha cognitiva raiz é a ausência de um checklist disciplinado pré-lance que avalie todos os lances forçantes (xeques, capturas, ameaças) para ambos os lados. Essa única falha se propaga em aparentes fraquezas estratégicas — colunas abertas são ignoradas porque o jogador não avalia ameaças de penetração de torres, peões atrasados são mal manejados porque o jogador não vê as consequências táticas dos avanços de peões, e vantagens de espaço/maioria de peões são desperdiçadas porque o jogador escolhe lances não-forçantes quando soluções táticas concretas existem.
- **Padrão cognitivo:** O jogador opera com um processo de pensamento 'posicional primeiro': seleciona lances baseados em ideias gerais (desenvolver uma peça, avançar um peão, atacar algo) sem primeiro varrer exaustivamente lances forçantes — xeques, capturas e ameaças — para ambos os lados. Isso cria um ponto cego sistemático onde oportunidades táticas concretas ficam invisíveis. O jogador frequentemente faz lances estratégicos de aparência razoável (Be7, d5, O-O, Td2) quando lances táticos devastadores existem (Dxg5, Cxe4, Dh5+, Cxf7). A correção requer inverter a ordem de pensamento: PRIMEIRO verificar todos os lances forçantes (xeques, capturas, ameaças) para você e seu oponente, DEPOIS avaliar considerações posicionais. Adicionalmente, o jogador carece de uma 'verificação de segurança' final antes de executar um lance — não pergunta 'tem algo pendurado depois que eu fizer esse lance?' Isso explica os 15 erros de peça pendurada. A correção em dois passos é: (1) varrer por táticas primeiro, (2) verificar blunders por último.
- **Confiança:** HIGH
- **Avaliação qualitativa do diagnóstico:** _( ) coerente com os dados   ( ) discordo — justificativa:_

**Classificação das fraquezas**

| Conceito | Classificação | Justificativa (resumo) |
|----------|---------------|------------------------|
| missed_tactic | PRIMARY | Taxa de erro de 100% com alta magnitude média (262.6 cp). Toda oportunidade tática foi per |
| hanging_piece | PRIMARY | Alta magnitude (264.5 cp) com 15 ocorrências em muitos jogos. A análise das posições de am |
| king_safety | SECONDARY | Os 12 erros se agrupam em dois sub-problemas específicos: (a) atrasar o roque quando era u |
| open_file | SECONDARY | 9 erros, mas a maioria são na verdade falhas táticas disfarçadas de estratégicas. No jogo_ |
| backward_pawn | NOISE | Baixa taxa de erro (3.7%) e magnitude moderada (175.4 cp). A maioria dos erros aqui são na |
| pawn_majority | NOISE | Apenas 5 erros em 330 ocorrências (1.5%). Três das cinco posições de amostra (jogo_30) env |
| space_advantage | NOISE | Apenas 5 erros em 131 ocorrências (3.8%). As posições de amostra novamente mostram erros t |
| weak_square | NOISE | Apenas 4 erros em 365 ocorrências (1.1%). Duas das quatro posições se sobrepõem com outras |
| piece_activity | SECONDARY | Apenas 3 ocorrências mas magnitude média extremamente alta (318 cp). A posição de final do |

**Plano de estudo (prioridade)**

| # | Conceito | Capítulo | Página | Motivo (resumo) |
|---|----------|----------|--------|-----------------|
| 1 | missed_tactic | 1 | 26 | Taxa de erro de 100% é catastrófica. O jogador deve construir o hábito de verifi |
| 2 | hanging_piece | 1 | 26 | 264.5 cp de perda média por erro. Após buscar lances forçantes (prioridade 1), o |
| 3 | king_safety | 7 | 156 | O jogador repetidamente atrasa o roque por 2-4 lances quando a posição exige. Um |
| 4 | open_file | 4 | 89 | Uma vez que a visão tática melhore, o jogador precisa aprender a identificar col |
| 5 | piece_activity | 2 | 45 | Após as fundações táticas e de segurança serem construídas, o jogador deve estud |
| 6 | backward_pawn | 5 | 109 | Baixa prioridade. Conhecimento estrutural de peões se desenvolverá naturalmente  |
| 7 | pawn_majority | 8 | 185 | Taxa de erro muito baixa. A maioria dos erros flagrados foram erros táticos, não |
| 8 | space_advantage | 8 | 178 | Déficit real mínimo. Os erros do jogador em posições relacionadas a espaço foram |
| 9 | weak_square | 3 | 67 | Taxa de erro estatisticamente negligenciável (1.1%). Nenhuma evidência de ceguei |

- **Avaliação qualitativa das recomendações:** _( ) relevantes e acionáveis   ( ) parcialmente   — justificativa:_

#### Detecções por conceito (lances-erro para análise qualitativa)

### Tática Perdida  (`missed_tactic`)

- **Referência Silman:** cap. 1, p. 26 — categoria *tática*
- **Conceito:** Oportunidade tática concreta deixada passar — tipicamente uma peça adversária pendurada que o jogador não capturou, ou uma troca que ganhava material.
- **Implicação estratégica:** Indica falha de visão tática/atenção, não de compreensão estratégica. Treina-se com exercícios de tática e checagem sistemática de capturas e ameaças antes de cada lance.
- **Detecções no perfil:** 16 erros em 16 ocorrências (100%), magnitude média 263 cp

_Lances-erro detectados (16):_

**Exemplo 1** — partida `game_3` (ILoveHeiHei vs diogenesdie, jogador de black)

- Lance jogado: `d7d5`  |  melhor lance: `f6e4`  |  perda: **148 cp**
- FEN: `r1bqkb1r/pppp1p1p/2n2np1/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 3 5`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqkb1r/pppp1p1p/2n2np1/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR_b_KQkq_-_3_5)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_3` (ILoveHeiHei vs diogenesdie, jogador de black)

- Lance jogado: `f8e7`  |  melhor lance: `d5g5`  |  perda: **313 cp**
- FEN: `r1b1kb1r/ppp2p1p/2n3p1/3q2N1/4p3/8/PPPP1PPP/RNBQK2R b KQkq - 1 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1kb1r/ppp2p1p/2n3p1/3q2N1/4p3/8/PPPP1PPP/RNBQK2R_b_KQkq_-_1_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_4` (diogenesdie vs vektor93, jogador de white)

- Lance jogado: `d1d5`  |  melhor lance: `e5f7`  |  perda: **114 cp**
- FEN: `r2k1bnr/5ppp/p3p3/1p1bN3/8/8/PPP1BPPP/R1BR2K1 w - - 0 15`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2k1bnr/5ppp/p3p3/1p1bN3/8/8/PPP1BPPP/R1BR2K1_w_-_-_0_15)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_7` (sonoglicine vs diogenesdie, jogador de black)

- Lance jogado: `f5h3`  |  melhor lance: `f8a8`  |  perda: **315 cp**
- FEN: `B4rk1/2p2ppp/p2b4/1p2qb2/8/4P1P1/PPP2P1P/R1BQ1RK1 b - - 0 14`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/B4rk1/2p2ppp/p2b4/1p2qb2/8/4P1P1/PPP2P1P/R1BQ1RK1_b_-_-_0_14)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `d4d2`  |  melhor lance: `e2b2`  |  perda: **413 cp**
- FEN: `2rk3r/pp3pp1/1p2b2p/2bp4/3R3P/2P2R2/Pn2QP2/4K3 w - - 18 32`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2rk3r/pp3pp1/1p2b2p/2bp4/3R3P/2P2R2/Pn2QP2/4K3_w_-_-_18_32)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `f4b8`  |  melhor lance: `f4a4`  |  perda: **498 cp**
- FEN: `2rk2r1/1R3pp1/p3b2p/1nbp4/p4Q1P/2P2R2/4KP2/8 w - - 1 41`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2rk2r1/1R3pp1/p3b2p/1nbp4/p4Q1P/2P2R2/4KP2/8_w_-_-_1_41)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_10` (diogenesdie vs princemarkyg, jogador de white)

- Lance jogado: `f3d4`  |  melhor lance: `f3e5`  |  perda: **117 cp**
- FEN: `r1bqkbnr/pppp1ppp/8/4p3/3nP3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqkbnr/pppp1ppp/8/4p3/3nP3/2N2N2/PPPP1PPP/R1BQKB1R_w_KQkq_-_4_4)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_11` (williamkulpa vs diogenesdie, jogador de black)

- Lance jogado: `e7f6`  |  melhor lance: `c6b4`  |  perda: **60 cp**
- FEN: `r1bqk1nr/ppp1bppp/2np4/4p3/1P1PP3/2N2N2/P1P2PPP/R1BQKB1R b KQkq - 0 5`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqk1nr/ppp1bppp/2np4/4p3/1P1PP3/2N2N2/P1P2PPP/R1BQKB1R_b_KQkq_-_0_5)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_11` (williamkulpa vs diogenesdie, jogador de black)

- Lance jogado: `d6d5`  |  melhor lance: `e4f2`  |  perda: **349 cp**
- FEN: `r3k1r1/p4pBp/2ppb3/8/3Rn3/8/P1P2PPP/2K2B1R b q - 2 16`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k1r1/p4pBp/2ppb3/8/3Rn3/8/P1P2PPP/2K2B1R_b_q_-_2_16)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 10** — partida `game_11` (williamkulpa vs diogenesdie, jogador de black)

- Lance jogado: `g8g5`  |  melhor lance: `e4f2`  |  perda: **52 cp**
- FEN: `r3k1r1/p4p1p/2p1b3/3pB3/3Rn3/8/P1P2PPP/2K2B1R b q - 1 17`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k1r1/p4p1p/2p1b3/3pB3/3Rn3/8/P1P2PPP/2K2B1R_b_q_-_1_17)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 11** — partida `game_15` (diogenesdie vs Axi7, jogador de white)

- Lance jogado: `d4f6`  |  melhor lance: `g4f6`  |  perda: **389 cp**
- FEN: `r3kbr1/ppp4p/3p1p2/3P3q/NP1QPpNP/5Pp1/P1P3P1/3RR1K1 w q - 2 20`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kbr1/ppp4p/3p1p2/3P3q/NP1QPpNP/5Pp1/P1P3P1/3RR1K1_w_q_-_2_20)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 12** — partida `game_19` (diogenesdie vs books_musiclover, jogador de white)

- Lance jogado: `g5e7`  |  melhor lance: `d1h5`  |  perda: **118 cp**
- FEN: `r1bqk2r/ppp1bp1p/2n1p3/6Bn/3pPP2/3P4/PPP3PP/R2QKBNR w KQkq - 0 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqk2r/ppp1bp1p/2n1p3/6Bn/3pPP2/3P4/PPP3PP/R2QKBNR_w_KQkq_-_0_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 13** — partida `game_19` (diogenesdie vs books_musiclover, jogador de white)

- Lance jogado: `f4f5`  |  melhor lance: `d1h5`  |  perda: **446 cp**
- FEN: `r1b1k2r/ppp1qp1p/2n1p3/7n/3pPP2/3P4/PPP3PP/R2QKBNR w KQkq - 0 10`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1k2r/ppp1qp1p/2n1p3/7n/3pPP2/3P4/PPP3PP/R2QKBNR_w_KQkq_-_0_10)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 14** — partida `game_23` (kapodth vs diogenesdie, jogador de black)

- Lance jogado: `c7d6`  |  melhor lance: `d8d6`  |  perda: **643 cp**
- FEN: `r2qk2r/p1b2ppp/1pPBpn2/n2p4/Q2P4/1NP1PN2/P1b2PPP/R3KB1R b KQkq - 4 12`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/p1b2ppp/1pPBpn2/n2p4/Q2P4/1NP1PN2/P1b2PPP/R3KB1R_b_KQkq_-_4_12)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 15** — partida `game_24` (diogenesdie vs sandeepch123, jogador de white)

- Lance jogado: `g1e1`  |  melhor lance: `g5f3`  |  perda: **152 cp**
- FEN: `r3k3/pp2r1pp/2pR4/2n1p1N1/2P1P3/nP3b2/P6P/2K3R1 w - - 5 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k3/pp2r1pp/2pR4/2n1p1N1/2P1P3/nP3b2/P6P/2K3R1_w_-_-_5_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 16** — partida `game_28` (diogenesdie vs 2026newaccount, jogador de white)

- Lance jogado: `f6g7`  |  melhor lance: `d1f3`  |  perda: **218 cp**
- FEN: `r1bqkb1r/ppp2ppp/2n2P2/8/8/2N2p2/PPP2PPP/R1BQKB1R w KQkq - 0 7`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqkb1r/ppp2ppp/2n2P2/8/8/2N2p2/PPP2PPP/R1BQKB1R_w_KQkq_-_0_7)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Peça Pendurada  (`hanging_piece`)

- **Referência Silman:** cap. 1, p. 26 — categoria *dinâmica*
- **Conceito:** Peça do jogador atacada pelo adversário e sem qualquer defesa aliada — pode ser capturada gratuitamente.
- **Implicação estratégica:** Peça pendurada é o erro mais custoso no xadrez amador: perde material sem contrapartida. O jogador deve verificar a segurança de todas as suas peças após cada lance do adversário, antes de escolher seu próprio lance.
- **Detecções no perfil:** 15 erros em 230 ocorrências (6%), magnitude média 264 cp

_Lances-erro detectados (15):_

**Exemplo 1** — partida `game_1` (Naveendeepu12 vs diogenesdie, jogador de black)

- Lance jogado: `f5d7`  |  melhor lance: `f6d7`  |  perda: **287 cp**
- FEN: `r2qk2r/p1p2ppp/1b3n2/nQ2pb2/2Pp3P/4P1P1/PP1P1PB1/RNB1K1NR b KQkq - 1 10`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/p1p2ppp/1b3n2/nQ2pb2/2Pp3P/4P1P1/PP1P1PB1/RNB1K1NR_b_KQkq_-_1_10)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_1` (Naveendeepu12 vs diogenesdie, jogador de black)

- Lance jogado: `d4d3`  |  melhor lance: `e6d7`  |  perda: **557 cp**
- FEN: `r2qk2r/p1p2ppp/1bn1bn2/1Q6/2Pp3P/4P1P1/PP1P1P2/RNB1K1NR b KQkq - 1 13`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/p1p2ppp/1bn1bn2/1Q6/2Pp3P/4P1P1/PP1P1P2/RNB1K1NR_b_KQkq_-_1_13)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_8` (eungminkhand vs diogenesdie, jogador de black)

- Lance jogado: `e7g5`  |  melhor lance: `f2e3`  |  perda: **136 cp**
- FEN: `1k1r3r/p1p1bpp1/3p3p/3Pp3/8/5NP1/PPPR1q1P/2K1N2R b - - 1 19`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1k1r3r/p1p1bpp1/3p3p/3Pp3/8/5NP1/PPPR1q1P/2K1N2R_b_-_-_1_19)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_8` (eungminkhand vs diogenesdie, jogador de black)

- Lance jogado: `f2e3`  |  melhor lance: `f2f5`  |  perda: **103 cp**
- FEN: `1k1r3r/p1p2pp1/3p3p/3Pp1N1/8/6P1/PPPR1q1P/2K1N2R b - - 0 20`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1k1r3r/p1p2pp1/3p3p/3Pp1N1/8/6P1/PPPR1q1P/2K1N2R_b_-_-_0_20)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `h1f1`  |  melhor lance: `e1d2`  |  perda: **205 cp**
- FEN: `rn2kb1r/ppp2ppp/3p4/8/2BN2b1/3QB3/PPP2PqP/R3K2R w KQkq - 0 10`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn2kb1r/ppp2ppp/3p4/8/2BN2b1/3QB3/PPP2PqP/R3K2R_w_KQkq_-_0_10)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `c4d5`  |  melhor lance: `e1c1`  |  perda: **707 cp**
- FEN: `rn2kb1r/ppp2ppp/3p4/8/2BN4/3QB2b/PPP2PqP/R3KR2 w Qkq - 2 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn2kb1r/ppp2ppp/3p4/8/2BN4/3QB2b/PPP2PqP/R3KR2_w_Qkq_-_2_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `d4e6`  |  melhor lance: `d3e4`  |  perda: **270 cp**
- FEN: `rn2kb1r/ppp2ppp/1q1p4/8/3N4/2PQB2b/PP3P1P/R3K1R1 w Qkq - 1 14`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn2kb1r/ppp2ppp/1q1p4/8/3N4/2PQB2b/PP3P1P/R3K1R1_w_Qkq_-_1_14)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_11` (williamkulpa vs diogenesdie, jogador de black)

- Lance jogado: `f2d3`  |  melhor lance: `f2g4`  |  perda: **456 cp**
- FEN: `1r2k3/p4p1B/4b3/2pp4/5R2/2P5/P4nPP/2K5 b - - 1 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1r2k3/p4p1B/4b3/2pp4/5R2/2P5/P4nPP/2K5_b_-_-_1_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_14` (diogenesdie vs G4m3Ov3rDragon, jogador de white)

- Lance jogado: `e1g1`  |  melhor lance: `e4f6`  |  perda: **155 cp**
- FEN: `rnbq1rk1/ppp3pp/1b1p1n2/3Pp1B1/2B1N3/5N2/PPP2PPP/R2QK2R w KQ - 1 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnbq1rk1/ppp3pp/1b1p1n2/3Pp1B1/2B1N3/5N2/PPP2PPP/R2QK2R_w_KQ_-_1_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 10** — partida `game_14` (diogenesdie vs G4m3Ov3rDragon, jogador de white)

- Lance jogado: `g5e3`  |  melhor lance: `e4f6`  |  perda: **580 cp**
- FEN: `rnbq1rk1/ppp3p1/1b1p1n1p/3Pp1B1/2B1N3/5N2/PPP2PPP/R2Q1RK1 w - - 0 10`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnbq1rk1/ppp3p1/1b1p1n1p/3Pp1B1/2B1N3/5N2/PPP2PPP/R2Q1RK1_w_-_-_0_10)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 11** — partida `game_15` (diogenesdie vs Axi7, jogador de white)

- Lance jogado: `d3h3`  |  melhor lance: `e2g2`  |  perda: **65 cp**
- FEN: `3k2r1/p7/1p1p3p/1PpP1P2/N1P1PbP1/3R4/P3R3/6K1 w - - 0 38`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3k2r1/p7/1p1p3p/1PpP1P2/N1P1PbP1/3R4/P3R3/6K1_w_-_-_0_38)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 12** — partida `game_16` (ok7look vs diogenesdie, jogador de black)

- Lance jogado: `a2c4`  |  melhor lance: `a2d5`  |  perda: **629 cp**
- FEN: `2krr3/B1p2p2/2p4p/4p3/4N1np/8/bP2K3/2R2R2 b - - 1 28`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2krr3/B1p2p2/2p4p/4p3/4N1np/8/bP2K3/2R2R2_b_-_-_1_28)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 13** — partida `game_19` (diogenesdie vs books_musiclover, jogador de white)

- Lance jogado: `e1c1`  |  melhor lance: `e1d2`  |  perda: **149 cp**
- FEN: `r1b1k2r/ppp1qp1p/8/5p1Q/1n1pP3/3P4/PPP3PP/R3KBNR w KQkq - 1 12`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1k2r/ppp1qp1p/8/5p1Q/1n1pP3/3P4/PPP3PP/R3KBNR_w_KQkq_-_1_12)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 14** — partida `game_24` (diogenesdie vs sandeepch123, jogador de white)

- Lance jogado: `d1d3`  |  melhor lance: `c4e2`  |  perda: **86 cp**
- FEN: `r1bk3r/pp1n2pp/2p2p2/4p3/2B1P3/2P1n2N/PP4PP/2KR3R w - - 0 16`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bk3r/pp1n2pp/2p2p2/4p3/2B1P3/2P1n2N/PP4PP/2KR3R_w_-_-_0_16)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 15** — partida `game_25` (leomarianxavier vs diogenesdie, jogador de black)

- Lance jogado: `c5e3`  |  melhor lance: `c5e7`  |  perda: **56 cp**
- FEN: `r4k1r/p1p3pp/b1p1qp2/2b1p3/2P5/3PBN2/PP2QPPP/R3R1K1 b - - 2 13`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r4k1r/p1p3pp/b1p1qp2/2b1p3/2P5/3PBN2/PP2QPPP/R3R1K1_b_-_-_2_13)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Segurança do Rei  (`king_safety`)

- **Referência Silman:** cap. 7, p. 156 — categoria *dinâmica*
- **Conceito:** Avaliação da exposição do rei baseada em cobertura de peões de escudo e atividade adversária.
- **Implicação estratégica:** Rei exposto transforma o jogo em dinâmico: o adversário deve atacar imediatamente. Este desequilíbrio supera fatores posicionais estáticos quando a posição é aguda.
- **Detecções no perfil:** 12 erros em 418 ocorrências (3%), magnitude média 184 cp

_Lances-erro detectados (12):_

**Exemplo 1** — partida `game_1` (Naveendeepu12 vs diogenesdie, jogador de black)

- Lance jogado: `d7e6`  |  melhor lance: `e8f8`  |  perda: **68 cp**
- FEN: `r2qk2r/p1pb1ppp/1b3n2/n3Q3/2Pp3P/4P1P1/PP1P1PB1/RNB1K1NR b KQkq - 0 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/p1pb1ppp/1b3n2/n3Q3/2Pp3P/4P1P1/PP1P1PB1/RNB1K1NR_b_KQkq_-_0_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `c4d5`  |  melhor lance: `e1c1`  |  perda: **707 cp**
- FEN: `rn2kb1r/ppp2ppp/3p4/8/2BN4/3QB2b/PPP2PqP/R3KR2 w Qkq - 2 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn2kb1r/ppp2ppp/3p4/8/2BN4/3QB2b/PPP2PqP/R3KR2_w_Qkq_-_2_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_17` (diogenesdie vs htostamnevidomuy, jogador de white)

- Lance jogado: `d4d5`  |  melhor lance: `e1g1`  |  perda: **176 cp**
- FEN: `rnb1k1nr/pp1p1ppp/1b3q2/8/2BPP3/4B3/PP3PPP/RN1QK2R w KQkq - 1 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnb1k1nr/pp1p1ppp/1b3q2/8/2BPP3/4B3/PP3PPP/RN1QK2R_w_KQkq_-_1_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_18` (moelze26 vs diogenesdie, jogador de black)

- Lance jogado: `a7a5`  |  melhor lance: `c3c2`  |  perda: **94 cp**
- FEN: `k7/p7/7p/4n3/1p2PN2/2rP4/P3KPPP/4R3 b - - 1 34`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/k7/p7/7p/4n3/1p2PN2/2rP4/P3KPPP/4R3_b_-_-_1_34)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_22` (jaden153 vs diogenesdie, jogador de black)

- Lance jogado: `d5d4`  |  melhor lance: `e8g8`  |  perda: **118 cp**
- FEN: `r3k2r/ppp1q1pp/2n2n2/2bpp3/8/2NP1N2/PPP2PPP/R1BQR1K1 b kq - 1 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k2r/ppp1q1pp/2n2n2/2bpp3/8/2NP1N2/PPP2PPP/R1BQR1K1_b_kq_-_1_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_23` (kapodth vs diogenesdie, jogador de black)

- Lance jogado: `d6c7`  |  melhor lance: `e8g8`  |  perda: **60 cp**
- FEN: `r2qk2r/p4ppp/1pPbpn2/n2p1b2/Q2P4/1NP1PN2/P4PPP/R1B1KB1R b KQkq - 0 10`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/p4ppp/1pPbpn2/n2p1b2/Q2P4/1NP1PN2/P4PPP/R1B1KB1R_b_KQkq_-_0_10)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_24` (diogenesdie vs sandeepch123, jogador de white)

- Lance jogado: `g2g4`  |  melhor lance: `c1b2`  |  perda: **124 cp**
- FEN: `r1bk4/pp1nr1pp/2p2p2/4p3/2P1P3/nP1R3N/P5PP/2KR4 w - - 3 20`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bk4/pp1nr1pp/2p2p2/4p3/2P1P3/nP1R3N/P5PP/2KR4_w_-_-_3_20)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_25` (leomarianxavier vs diogenesdie, jogador de black)

- Lance jogado: `c8a6`  |  melhor lance: `e8g8`  |  perda: **194 cp**
- FEN: `r1b1k2r/p1p2ppp/2p5/2bqp3/8/3P1N2/PPP2PPP/R1BQ1RK1 b kq - 1 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1k2r/p1p2ppp/2p5/2bqp3/8/3P1N2/PPP2PPP/R1BQ1RK1_b_kq_-_1_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_25` (leomarianxavier vs diogenesdie, jogador de black)

- Lance jogado: `f7g6`  |  melhor lance: `b4b7`  |  perda: **657 cp**
- FEN: `b6r/R4kpp/2p1qp2/4p3/PrP5/3PQN2/5PPP/4R1K1 b - - 2 23`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/b6r/R4kpp/2p1qp2/4p3/PrP5/3PQN2/5PPP/4R1K1_b_-_-_2_23)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 10** — partida `game_27` (diogenesdie vs b0nerchamp0, jogador de white)

- Lance jogado: `h1f1`  |  melhor lance: `e1g1`  |  perda: **67 cp**
- FEN: `rn1q3r/ppk2Bpp/1bp1Q3/4p3/1P1p4/2nP1b1N/P6P/R1B1K2R w KQ - 3 17`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn1q3r/ppk2Bpp/1bp1Q3/4p3/1P1p4/2nP1b1N/P6P/R1B1K2R_w_KQ_-_3_17)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 11** — partida `game_27` (diogenesdie vs b0nerchamp0, jogador de white)

- Lance jogado: `d2e1`  |  melhor lance: `f1f2`  |  perda: **112 cp**
- FEN: `r7/pp1k4/1b4B1/2p1p3/n2p4/3P1R2/3K3r/5R2 w - - 0 34`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r7/pp1k4/1b4B1/2p1p3/n2p4/3P1R2/3K3r/5R2_w_-_-_0_34)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 12** — partida `game_30` (diogenesdie vs tejas_pardeshi, jogador de white)

- Lance jogado: `f2f3`  |  melhor lance: `c4f7`  |  perda: **192 cp**
- FEN: `rnb1k2r/ppppqppp/3b1n2/4N3/2BPP3/2P5/PP3PPP/RNBQK2R w KQkq - 3 7`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnb1k2r/ppppqppp/3b1n2/4N3/2BPP3/2P5/PP3PPP/RNBQK2R_w_KQkq_-_3_7)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Coluna Aberta  (`open_file`)

- **Referência Silman:** cap. 4, p. 89 — categoria *desequilíbrios dinâmicos*
- **Conceito:** Coluna sem peões de nenhuma das cores, ideal para torres. Semi-aberta: coluna sem peão do jogador mas com peão adversário.
- **Implicação estratégica:** Quem controla colunas abertas controla penetração e pode dobrar torres. Ignorar colunas abertas desperdiça a principal força das torres.
- **Detecções no perfil:** 9 erros em 549 ocorrências (2%), magnitude média 211 cp

_Lances-erro detectados (9):_

**Exemplo 1** — partida `game_4` (diogenesdie vs vektor93, jogador de white)

- Lance jogado: `h6g5`  |  melhor lance: `b1c1`  |  perda: **157 cp**
- FEN: `8/4k3/p6B/1p6/P3p3/1Pb5/2r2PPP/1R3K2 w - - 0 28`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/4k3/p6B/1p6/P3p3/1Pb5/2r2PPP/1R3K2_w_-_-_0_28)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_8` (eungminkhand vs diogenesdie, jogador de black)

- Lance jogado: `b8b7`  |  melhor lance: `d8f8`  |  perda: **162 cp**
- FEN: `1k1r3r/p1p2Np1/3p3p/3Pp3/8/4q1P1/PPPR3P/2K1N2R b - - 0 21`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1k1r3r/p1p2Np1/3p3p/3Pp3/8/4q1P1/PPPR3P/2K1N2R_b_-_-_0_21)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_18` (moelze26 vs diogenesdie, jogador de black)

- Lance jogado: `e6g4`  |  melhor lance: `d8g8`  |  perda: **754 cp**
- FEN: `2kr3r/pppq1p2/3pbp1p/2b1p3/2PnP3/2NP2QN/PP1RBPPP/2K4R b - - 7 12`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2kr3r/pppq1p2/3pbp1p/2b1p3/2PnP3/2NP2QN/PP1RBPPP/2K4R_b_-_-_7_12)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_18` (moelze26 vs diogenesdie, jogador de black)

- Lance jogado: `b4c3`  |  melhor lance: `f8g8`  |  perda: **168 cp**
- FEN: `2k2r1r/ppp3Q1/3p1p1p/4p3/1bPnP3/2NP3N/PP1R1PPP/2K4R b - - 2 17`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2k2r1r/ppp3Q1/3p1p1p/4p3/1bPnP3/2NP3N/PP1R1PPP/2K4R_b_-_-_2_17)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_19` (diogenesdie vs books_musiclover, jogador de white)

- Lance jogado: `f3e5`  |  melhor lance: `d1e1`  |  perda: **272 cp**
- FEN: `r1b1k2r/ppp1qp1p/8/4nP1Q/3p4/3P1N2/1PP3PP/1K1R1B1R w kq - 3 16`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1k2r/ppp1qp1p/8/4nP1Q/3p4/3P1N2/1PP3PP/1K1R1B1R_w_kq_-_3_16)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_19` (diogenesdie vs books_musiclover, jogador de white)

- Lance jogado: `g4f5`  |  melhor lance: `h1f1`  |  perda: **64 cp**
- FEN: `r3k2r/ppp2p1p/8/1q3b1Q/3p2B1/3P4/1PP3PP/1K1R3R w kq - 2 19`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k2r/ppp2p1p/8/1q3b1Q/3p2B1/3P4/1PP3PP/1K1R3R_w_kq_-_2_19)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_22` (jaden153 vs diogenesdie, jogador de black)

- Lance jogado: `e8e6`  |  melhor lance: `g6f6`  |  perda: **173 cp**
- FEN: `3kr3/ppp3pp/2n3q1/2b1p3/3pR3/3P1N2/PPP1QPPP/R5K1 b - - 5 18`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3kr3/ppp3pp/2n3q1/2b1p3/3pR3/3P1N2/PPP1QPPP/R5K1_b_-_-_5_18)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_28` (diogenesdie vs 2026newaccount, jogador de white)

- Lance jogado: `d1f3`  |  melhor lance: `d1d8`  |  perda: **53 cp**
- FEN: `r1bqk2r/ppp2pbp/2n5/8/8/2N2p2/PPP2PPP/R1BQKB1R w KQkq - 0 8`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqk2r/ppp2pbp/2n5/8/8/2N2p2/PPP2PPP/R1BQKB1R_w_KQkq_-_0_8)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_28` (diogenesdie vs 2026newaccount, jogador de white)

- Lance jogado: `c3e4`  |  melhor lance: `f3e3`  |  perda: **349 cp**
- FEN: `r1b1k2r/ppp1qpbp/2n5/8/8/2N2Q2/PPP2PPP/R1B1KB1R w KQkq - 1 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1k2r/ppp1qpbp/2n5/8/8/2N2Q2/PPP2PPP/R1B1KB1R_w_KQkq_-_1_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Peão Atrasado  (`backward_pawn`)

- **Referência Silman:** cap. 5, p. 109 — categoria *estrutura de peões*
- **Conceito:** Peão que não pode avançar com segurança porque a casa à sua frente é controlada por um peão adversário, e não tem apoio de peões aliados por trás nas colunas adjacentes.
- **Implicação estratégica:** Peão atrasado é fraqueza estrutural permanente: preso na coluna semi-aberta, torna-se alvo de pressão de torres. O adversário deve dobrar torres nessa coluna; o jogador deve buscar avançar o peão quando possível ou trocá-lo para eliminar a fraqueza.
- **Detecções no perfil:** 8 erros em 214 ocorrências (4%), magnitude média 175 cp

_Lances-erro detectados (8):_

**Exemplo 1** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `d1c1`  |  melhor lance: `d1d5`  |  perda: **313 cp**
- FEN: `2r1kb1r/pp3pp1/1p2b2p/3p1n2/1P5P/2P5/P3QP2/3RK2R w k - 3 22`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r1kb1r/pp3pp1/1p2b2p/3p1n2/1P5P/2P5/P3QP2/3RK2R_w_k_-_3_22)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `e5f4`  |  melhor lance: `d1d5`  |  perda: **94 cp**
- FEN: `2rk2r1/pp3pp1/1p2b2p/2bpQ3/2n4P/2P2R2/P3KP2/3R4 w - - 26 36`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2rk2r1/pp3pp1/1p2b2p/2bpQ3/2n4P/2P2R2/P3KP2/3R4_w_-_-_26_36)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_15` (diogenesdie vs Axi7, jogador de white)

- Lance jogado: `b4b5`  |  melhor lance: `c4c5`  |  perda: **160 cp**
- FEN: `r4b2/p1pk4/1p1p3p/3P2qN/NPP1P1P1/5P2/P3R3/3R2K1 w - - 1 30`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r4b2/p1pk4/1p1p3p/3P2qN/NPP1P1P1/5P2/P3R3/3R2K1_w_-_-_1_30)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_15` (diogenesdie vs Axi7, jogador de white)

- Lance jogado: `d1d3`  |  melhor lance: `e4e5`  |  perda: **107 cp**
- FEN: `r5q1/p2k4/1p1p3p/1PpP1PbN/N1P1P1P1/8/P5R1/3R2K1 w - - 1 34`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r5q1/p2k4/1p1p3p/1PpP1PbN/N1P1P1P1/8/P5R1/3R2K1_w_-_-_1_34)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_18` (moelze26 vs diogenesdie, jogador de black)

- Lance jogado: `c5b4`  |  melhor lance: `f6f5`  |  perda: **223 cp**
- FEN: `2kr3r/pppq1p2/3p1p1p/2b1p3/2PnP1B1/2NP2QN/PP1R1PPP/2K4R b - - 0 13`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2kr3r/pppq1p2/3p1p1p/2b1p3/2PnP1B1/2NP2QN/PP1R1PPP/2K4R_b_-_-_0_13)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_18` (moelze26 vs diogenesdie, jogador de black)

- Lance jogado: `d4e6`  |  melhor lance: `f6f5`  |  perda: **77 cp**
- FEN: `2k2r1r/ppp3Q1/3p1p1p/4p3/2PnP3/3P3N/PP1K1PPP/4R3 b - - 0 19`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2k2r1r/ppp3Q1/3p1p1p/4p3/2PnP3/3P3N/PP1K1PPP/4R3_b_-_-_0_19)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_25` (leomarianxavier vs diogenesdie, jogador de black)

- Lance jogado: `a6a5`  |  melhor lance: `c6b5`  |  perda: **185 cp**
- FEN: `3r3r/1bp2kpp/p1p1qp2/1P2p3/P1P5/3PQN2/5PPP/1R2R1K1 b - - 1 18`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r3r/1bp2kpp/p1p1qp2/1P2p3/P1P5/3PQN2/5PPP/1R2R1K1_b_-_-_1_18)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_27` (diogenesdie vs b0nerchamp0, jogador de white)

- Lance jogado: `d2d3`  |  melhor lance: `e1f1`  |  perda: **244 cp**
- FEN: `rn1qk2r/pp3ppp/1bp5/4p2b/1PBpn3/2P2P1N/P2P3P/R1BQK2R w KQkq - 0 13`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn1qk2r/pp3ppp/1bp5/4p2b/1PBpn3/2P2P1N/P2P3P/R1BQK2R_w_KQkq_-_0_13)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Maioria de Peões  (`pawn_majority`)

- **Referência Silman:** cap. 8, p. 185 — categoria *estrutura de peões*
- **Conceito:** Superioridade numérica de peões em um flanco — permite criar um peão passado através de avanços.
- **Implicação estratégica:** Maioria saudável de peões deve ser avançada para criar um peão passado. Ignorar a maioria desperdiça uma vantagem estrutural de longo prazo.
- **Detecções no perfil:** 5 erros em 330 ocorrências (2%), magnitude média 293 cp

_Lances-erro detectados (5):_

**Exemplo 1** — partida `game_4` (diogenesdie vs vektor93, jogador de white)

- Lance jogado: `d4d5`  |  melhor lance: `d4c5`  |  perda: **119 cp**
- FEN: `rn2kbnr/pb2pppp/1p6/2p5/3P4/2N2N2/PPP1BPPP/R1B1K2R w KQkq - 0 8`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn2kbnr/pb2pppp/1p6/2p5/3P4/2N2N2/PPP1BPPP/R1B1K2R_w_KQkq_-_0_8)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_15` (diogenesdie vs Axi7, jogador de white)

- Lance jogado: `e2g2`  |  melhor lance: `d5c6`  |  perda: **577 cp**
- FEN: `r4b2/p2k4/1p1p3p/1PpP2qN/N1P1P1P1/5P2/P3R3/3R2K1 w - c6 0 31`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r4b2/p2k4/1p1p3p/1PpP2qN/N1P1P1P1/5P2/P3R3/3R2K1_w_-_c6_0_31)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_30` (diogenesdie vs tejas_pardeshi, jogador de white)

- Lance jogado: `f2f3`  |  melhor lance: `c4f7`  |  perda: **192 cp**
- FEN: `rnb1k2r/ppppqppp/3b1n2/4N3/2BPP3/2P5/PP3PPP/RNBQK2R w KQkq - 3 7`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnb1k2r/ppppqppp/3b1n2/4N3/2BPP3/2P5/PP3PPP/RNBQK2R_w_KQkq_-_3_7)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_30` (diogenesdie vs tejas_pardeshi, jogador de white)

- Lance jogado: `e1g1`  |  melhor lance: `e5f7`  |  perda: **197 cp**
- FEN: `rnb2rk1/ppppqppp/3b1n2/4N3/2BPP3/2P2P2/PP4PP/RNBQK2R w KQ - 1 8`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnb2rk1/ppppqppp/3b1n2/4N3/2BPP3/2P2P2/PP4PP/RNBQK2R_w_KQ_-_1_8)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_30` (diogenesdie vs tejas_pardeshi, jogador de white)

- Lance jogado: `d4d5`  |  melhor lance: `c4f7`  |  perda: **459 cp**
- FEN: `rnb2rk1/pp1pqppp/3b1n2/2p1N3/2BPP3/2P2P2/PP4PP/RNBQ1RK1 w - - 0 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnb2rk1/pp1pqppp/3b1n2/2p1N3/2BPP3/2P2P2/PP4PP/RNBQ1RK1_w_-_-_0_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Vantagem de Espaço  (`space_advantage`)

- **Referência Silman:** cap. 8, p. 178 — categoria *desequilíbrios estáticos*
- **Conceito:** Controle de mais casas no tabuleiro, especialmente no campo adversário.
- **Implicação estratégica:** Mais espaço significa mais opções e restrição das peças adversárias. Deve ser explorado com avanços de peões ou criação de fraquezas no campo do adversário.
- **Detecções no perfil:** 5 erros em 131 ocorrências (4%), magnitude média 251 cp

_Lances-erro detectados (5):_

**Exemplo 1** — partida `game_3` (ILoveHeiHei vs diogenesdie, jogador de black)

- Lance jogado: `e5e4`  |  melhor lance: `d5e4`  |  perda: **220 cp**
- FEN: `r1b1kb1r/ppp2p1p/2n3p1/3qp3/8/5N2/PPPP1PPP/RNBQK2R b KQkq - 1 8`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1kb1r/ppp2p1p/2n3p1/3qp3/8/5N2/PPPP1PPP/RNBQK2R_b_KQkq_-_1_8)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_15` (diogenesdie vs Axi7, jogador de white)

- Lance jogado: `f6f4`  |  melhor lance: `e4e5`  |  perda: **345 cp**
- FEN: `r3kb2/ppp4p/3p1Qr1/3P3q/NP2PpNP/5Pp1/P1P3P1/3RR1K1 w q - 1 21`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kb2/ppp4p/3p1Qr1/3P3q/NP2PpNP/5Pp1/P1P3P1/3RR1K1_w_q_-_1_21)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_16` (ok7look vs diogenesdie, jogador de black)

- Lance jogado: `c5b4`  |  melhor lance: `f6g4`  |  perda: **54 cp**
- FEN: `2kr3r/p1p2ppp/2p2n2/2b1p3/7P/2N4R/PPb1N3/R1B1K3 b Q - 1 15`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2kr3r/p1p2ppp/2p2n2/2b1p3/7P/2N4R/PPb1N3/R1B1K3_b_Q_-_1_15)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_17` (diogenesdie vs htostamnevidomuy, jogador de white)

- Lance jogado: `d4d5`  |  melhor lance: `e1g1`  |  perda: **176 cp**
- FEN: `rnb1k1nr/pp1p1ppp/1b3q2/8/2BPP3/4B3/PP3PPP/RN1QK2R w KQkq - 1 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnb1k1nr/pp1p1ppp/1b3q2/8/2BPP3/4B3/PP3PPP/RN1QK2R_w_KQkq_-_1_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_30` (diogenesdie vs tejas_pardeshi, jogador de white)

- Lance jogado: `d4d5`  |  melhor lance: `c4f7`  |  perda: **459 cp**
- FEN: `rnb2rk1/pp1pqppp/3b1n2/2p1N3/2BPP3/2P2P2/PP4PP/RNBQ1RK1 w - - 0 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnb2rk1/pp1pqppp/3b1n2/2p1N3/2BPP3/2P2P2/PP4PP/RNBQ1RK1_w_-_-_0_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Casa Fraca  (`weak_square`)

- **Referência Silman:** cap. 3, p. 67 — categoria *desequilíbrios estáticos*
- **Conceito:** Casa que não pode ser defendida por peões e pode ser ocupada por peças adversárias.
- **Implicação estratégica:** Permite infiltração de cavalos e bispos adversários em posições fixas. Deve ser bloqueada com peças ou eliminada estruturalmente.
- **Detecções no perfil:** 4 erros em 365 ocorrências (1%), magnitude média 248 cp

_Lances-erro detectados (4):_

**Exemplo 1** — partida `game_4` (diogenesdie vs vektor93, jogador de white)

- Lance jogado: `a4b5`  |  melhor lance: `b1c1`  |  perda: **206 cp**
- FEN: `8/8/p3k3/1p4B1/P3p3/1Pb5/2r2PPP/1R3K2 w - - 2 29`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/8/p3k3/1p4B1/P3p3/1Pb5/2r2PPP/1R3K2_w_-_-_2_29)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `f7f5`  |  melhor lance: `b8c8`  |  perda: **143 cp**
- FEN: `1Rbkr3/5R2/p2b3p/3p1n2/p6P/2P5/5P2/5K2 w - - 3 47`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1Rbkr3/5R2/p2b3p/3p1n2/p6P/2P5/5P2/5K2_w_-_-_3_47)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_11` (williamkulpa vs diogenesdie, jogador de black)

- Lance jogado: `f2d3`  |  melhor lance: `f2g4`  |  perda: **456 cp**
- FEN: `1r2k3/p4p1B/4b3/2pp4/5R2/2P5/P4nPP/2K5 b - - 1 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1r2k3/p4p1B/4b3/2pp4/5R2/2P5/P4nPP/2K5_b_-_-_1_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_25` (leomarianxavier vs diogenesdie, jogador de black)

- Lance jogado: `a6a5`  |  melhor lance: `c6b5`  |  perda: **185 cp**
- FEN: `3r3r/1bp2kpp/p1p1qp2/1P2p3/P1P5/3PQN2/5PPP/1R2R1K1 b - - 1 18`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r3r/1bp2kpp/p1p1qp2/1P2p3/P1P5/3PQN2/5PPP/1R2R1K1_b_-_-_1_18)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Atividade de Peças  (`piece_activity`)

- **Referência Silman:** cap. 2, p. 45 — categoria *desequilíbrios dinâmicos*
- **Conceito:** Comparação entre a mobilidade das peças do jogador e as adversárias — peças ativas controlam mais casas.
- **Implicação estratégica:** Peças ativas são mais valiosas que material passivo. Deve-se sempre procurar melhorar a peça menos ativa antes de qualquer outra ação.
- **Detecções no perfil:** 3 erros em 135 ocorrências (2%), magnitude média 318 cp

_Lances-erro detectados (3):_

**Exemplo 1** — partida `game_4` (diogenesdie vs vektor93, jogador de white)

- Lance jogado: `f2f3`  |  melhor lance: `h3h8`  |  perda: **680 cp**
- FEN: `8/8/8/8/3kp3/7Q/5P2/5K2 w - - 3 45`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/8/8/8/3kp3/7Q/5P2/5K2_w_-_-_3_45)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `e4e2`  |  melhor lance: `d1d5`  |  perda: **141 cp**
- FEN: `r3kb1r/pp3ppp/1pn1b3/3p4/4Q3/2P5/PP3P1P/3RK1R1 w kq - 0 18`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kb1r/pp3ppp/1pn1b3/3p4/4Q3/2P5/PP3P1P/3RK1R1_w_kq_-_0_18)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_9` (diogenesdie vs Pratapnandhini, jogador de white)

- Lance jogado: `d1c1`  |  melhor lance: `d1d5`  |  perda: **313 cp**
- FEN: `2r1kb1r/pp3pp1/1p2b2p/3p1n2/1P5P/2P5/P3QP2/3RK2R w k - 3 22`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r1kb1r/pp3pp1/1p2b2p/3p1n2/1P5P/2P5/P3QP2/3RK2R_w_k_-_3_22)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_


---

## Perfil 2 — sprandel1

**Dados gerais**

| Partidas | Posições | Erros | Taxa de erro | Fraquezas recorrentes |
|----------|----------|-------|--------------|-----------------------|
| 30 | 1119 | 257 | 23.0% | 9 |

#### Diagnóstico de causa raiz

- **Causa raiz:** Falha em priorizar lances forçantes concretos sobre planos gerais (`tactical_blindness_under_concrete_demands`)
- **Descrição:** O jogador consistentemente falha em detectar ou priorizar capturas, trocas e sequências forçantes quando estão disponíveis, recorrendo a lances posicionais ou defensivos por padrão. Isso se manifesta em uma taxa de erro de 100% em táticas perdidas (24/24), mas também se propaga para erros de peças penduradas (deixando peças desprotegidas porque alternativas forçantes não foram calculadas) e negligência de colunas abertas (escolhendo posicionamentos passivos quando movimentos ativos de torre com ameaças concretas existem). O problema raiz é um processo de pensamento que pula a verificação obrigatória de capturas-xeques-ameaças antes de selecionar um lance. Em posições de final (jogo_2 lances 33-54, jogo_10 lances 31-40, jogo_16 lances 39-53), o jogador repetidamente faz lances de aparência natural mas imprecisos, sem perceber que a posição mudou de estratégica para tática/concreta. O jogador não recalibra o processo de pensamento quando a posição exige cálculo em vez de jogo geral.
- **Padrão cognitivo:** O jogador opera em modo de 'piloto automático estratégico': seleciona lances baseado em raciocínio posicional geral (desenvolver, defender, melhorar) sem primeiro escanear possibilidades forçantes concretas. Isso cria um ponto cego sistemático onde capturas disponíveis, trocas, golpes táticos e sequências de ganho de peças são ignorados. Em momentos críticos — especialmente transições para finais e posições onde a coordenação de peças cria motivos táticos — o jogador não muda para o modo de cálculo. A mudança necessária é adotar uma lista de verificação pré-lance obrigatória: (1) O que o último lance do meu oponente ameaça? (2) Que xeques, capturas e ataques eu tenho? (3) Todas as minhas peças estão seguras? Somente após responder essas três perguntas o jogador deve considerar planos posicionais. Esta disciplina deve se tornar automática antes que o estudo estratégico produza melhoria significativa.
- **Confiança:** HIGH
- **Avaliação qualitativa do diagnóstico:** _( ) coerente com os dados   ( ) discordo — justificativa:_

**Classificação das fraquezas**

| Conceito | Classificação | Justificativa (resumo) |
|----------|---------------|------------------------|
| missed_tactic | PRIMARY | Taxa de erro de 100% em 24 ocorrências com magnitude média de 169,5 cp. Esta é a deficiênc |
| hanging_piece | PRIMARY | 13 erros com magnitude média de 186,2 cp. Embora a taxa de erro seja menor (6,9%), a alta  |
| king_safety | SECONDARY | 12 erros a 174,7 cp mas apenas 2,7% de taxa de erro em 437 posições. Os erros se concentra |
| open_file | SECONDARY | 9 erros a 1,3% de taxa. Os lances de coluna aberta perdidos (ex.: jogo_9 Tb8, jogo_13 Tc8, |
| pawn_majority | NOISE | 7 erros a 1,7% de taxa com apenas 125,6 cp de magnitude. Várias posições da amostra (jogo_ |
| space_advantage | SECONDARY | 6 erros a 4,9% de taxa com 173,7 cp de magnitude. Examinando as posições, a maioria envolv |
| piece_activity | NOISE | Apenas 4 erros a 3,8% de taxa com baixa magnitude de 83,5 cp. Posições se sobrepõem com ou |
| weak_square | NOISE | 4 erros a 1,4% de taxa. Três das quatro posições são do final do jogo_16 onde o jogador re |
| backward_pawn | NOISE | 3 erros a 1,2% de taxa com 115,7 cp de magnitude. Ocorrência muito baixa. As posições do j |

**Plano de estudo (prioridade)**

| # | Conceito | Capítulo | Página | Motivo (resumo) |
|---|----------|----------|--------|-----------------|
| 1 | missed_tactic | 1 | 26 | Prioridade absoluta. Taxa de erro de 100% significa que o jogador não tem sistem |
| 2 | hanging_piece | 1 | 26 | Maior magnitude média de erro (186,2 cp) entre todas as categorias. Diretamente  |
| 3 | king_safety | 7 | 156 | Os erros de segurança do rei em finais indicam que o jogador não recalcula ativi |
| 4 | open_file | 4 | 89 | Uma vez que a consciência tática melhorar, o jogador precisa desenvolver o refle |
| 5 | space_advantage | 8 | 178 | Prioridade menor. Os erros relacionados a espaço se resolverão parcialmente quan |

- **Avaliação qualitativa das recomendações:** _( ) relevantes e acionáveis   ( ) parcialmente   — justificativa:_

#### Detecções por conceito (lances-erro para análise qualitativa)

### Tática Perdida  (`missed_tactic`)

- **Referência Silman:** cap. 1, p. 26 — categoria *tática*
- **Conceito:** Oportunidade tática concreta deixada passar — tipicamente uma peça adversária pendurada que o jogador não capturou, ou uma troca que ganhava material.
- **Implicação estratégica:** Indica falha de visão tática/atenção, não de compreensão estratégica. Treina-se com exercícios de tática e checagem sistemática de capturas e ameaças antes de cada lance.
- **Detecções no perfil:** 24 erros em 24 ocorrências (100%), magnitude média 170 cp

_Lances-erro detectados (24):_

**Exemplo 1** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `e6d5`  |  melhor lance: `c6d5`  |  perda: **101 cp**
- FEN: `r2qk2r/p5pp/2pbbp2/1pnB4/5P2/1PN3P1/PBPQN2P/3R1RK1 b kq - 0 16`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/p5pp/2pbbp2/1pnB4/5P2/1PN3P1/PBPQN2P/3R1RK1_b_kq_-_0_16)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `d6c5`  |  melhor lance: `c6d5`  |  perda: **163 cp**
- FEN: `r2qk2r/p5pp/2pb1p2/1p1N4/3QnP2/1P4P1/PBP1N2P/3R1RK1 b kq - 2 18`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/p5pp/2pb1p2/1p1N4/3QnP2/1P4P1/PBP1N2P/3R1RK1_b_kq_-_2_18)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `h8d8`  |  melhor lance: `a2c2`  |  perda: **101 cp**
- FEN: `7r/6kp/3NR3/2p5/5P2/1P4P1/r1P4P/4K3 b - - 3 33`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/7r/6kp/3NR3/2p5/5P2/1P4P1/r1P4P/4K3_b_-_-_3_33)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `a2c2`  |  melhor lance: `c7c2`  |  perda: **335 cp**
- FEN: `8/2r3kp/4R3/8/5P2/1P1N2P1/r1P4P/4K3 b - - 2 36`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/2r3kp/4R3/8/5P2/1P1N2P1/r1P4P/4K3_b_-_-_2_36)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `h4h3`  |  melhor lance: `h4e4`  |  perda: **230 cp**
- FEN: `6N1/5k1p/8/5P2/4R2r/2K5/7r/8 b - - 0 50`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/6N1/5k1p/8/5P2/4R2r/2K5/7r/8_b_-_-_0_50)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `h4h5`  |  melhor lance: `f7g8`  |  perda: **353 cp**
- FEN: `6N1/5k1p/8/4KP2/7r/8/8/8 b - - 1 53`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/6N1/5k1p/8/4KP2/7r/8/8/8_b_-_-_1_53)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `h5f5`  |  melhor lance: `f7g8`  |  perda: **67 cp**
- FEN: `6N1/5k1p/8/3K1P1r/8/8/8/8 b - - 3 54`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/6N1/5k1p/8/3K1P1r/8/8/8/8_b_-_-_3_54)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_3` (sprandel1 vs Leelo1982, jogador de white)

- Lance jogado: `a2a4`  |  melhor lance: `f3f7`  |  perda: **61 cp**
- FEN: `1k1r3r/p1p2ppp/1p1qp3/8/8/3P1Q2/PPP2PPP/R3R1K1 w - - 1 18`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1k1r3r/p1p2ppp/1p1qp3/8/8/3P1Q2/PPP2PPP/R3R1K1_w_-_-_1_18)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_3` (sprandel1 vs Leelo1982, jogador de white)

- Lance jogado: `b5b4`  |  melhor lance: `b5a4`  |  perda: **78 cp**
- FEN: `8/k2r4/1p6/1Q1r3p/p7/3P2P1/5P1P/3R2K1 w - - 2 43`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/k2r4/1p6/1Q1r3p/p7/3P2P1/5P1P/3R2K1_w_-_-_2_43)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 10** — partida `game_9` (ALZ1828 vs sprandel1, jogador de black)

- Lance jogado: `e8g8`  |  melhor lance: `f6h5`  |  perda: **334 cp**
- FEN: `r1b1k2r/pp3ppp/2n2n2/2pp2NB/8/2NP4/PPP2PPP/R3K2R b KQkq - 2 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1k2r/pp3ppp/2n2n2/2pp2NB/8/2NP4/PPP2PPP/R3K2R_b_KQkq_-_2_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 11** — partida `game_9` (ALZ1828 vs sprandel1, jogador de black)

- Lance jogado: `f5g4`  |  melhor lance: `a6b5`  |  perda: **104 cp**
- FEN: `3r1rk1/1p3ppp/p1n2n2/1Np2bN1/3p2P1/3P3P/PPP1BP2/2KR3R b - - 0 16`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r1rk1/1p3ppp/p1n2n2/1Np2bN1/3p2P1/3P3P/PPP1BP2/2KR3R_b_-_-_0_16)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 12** — partida `game_12` (Ravenlchessl vs sprandel1, jogador de black)

- Lance jogado: `h7h6`  |  melhor lance: `d5c3`  |  perda: **187 cp**
- FEN: `2r2rk1/5ppp/p2bp3/1p1n1qB1/1PpP4/P1P2N1P/5PP1/R2Q1R1K b - - 6 21`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r2rk1/5ppp/p2bp3/1p1n1qB1/1PpP4/P1P2N1P/5PP1/R2Q1R1K_b_-_-_6_21)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 13** — partida `game_13` (Tei-guh vs sprandel1, jogador de black)

- Lance jogado: `a7a6`  |  melhor lance: `a4d4`  |  perda: **59 cp**
- FEN: `8/p4p1k/1p2p1p1/1b1pP2p/r2P1P2/1K4R1/3B4/8 b - - 3 35`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/p4p1k/1p2p1p1/1b1pP2p/r2P1P2/1K4R1/3B4/8_b_-_-_3_35)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 14** — partida `game_19` (sprandel1 vs moralis, jogador de white)

- Lance jogado: `d1d2`  |  melhor lance: `c3d5`  |  perda: **162 cp**
- FEN: `r2q1rk1/pp1nppbp/2n3p1/3p4/3P2b1/2N1BN2/PPP1BPPP/R2Q1RK1 w - - 3 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2q1rk1/pp1nppbp/2n3p1/3p4/3P2b1/2N1BN2/PPP1BPPP/R2Q1RK1_w_-_-_3_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 15** — partida `game_19` (sprandel1 vs moralis, jogador de white)

- Lance jogado: `d5e4`  |  melhor lance: `d5b7`  |  perda: **64 cp**
- FEN: `3r1rk1/pp3p1p/6pb/3Q4/7q/2N1PR1P/PPP3P1/R5K1 w - - 3 19`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r1rk1/pp3p1p/6pb/3Q4/7q/2N1PR1P/PPP3P1/R5K1_w_-_-_3_19)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 16** — partida `game_25` (MrJavadi1996 vs sprandel1, jogador de black)

- Lance jogado: `b8d7`  |  melhor lance: `d8d4`  |  perda: **135 cp**
- FEN: `rnbqk2r/pp2bppp/2p1p3/8/3P1P2/2NB4/PP3PPP/R2QK1NR b KQkq - 1 8`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnbqk2r/pp2bppp/2p1p3/8/3P1P2/2NB4/PP3PPP/R2QK1NR_b_KQkq_-_1_8)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 17** — partida `game_25` (MrJavadi1996 vs sprandel1, jogador de black)

- Lance jogado: `c8d8`  |  melhor lance: `h7h2`  |  perda: **51 cp**
- FEN: `2r1k3/1Q1b2pr/4pq2/3p4/3P1bP1/8/PP5P/1K1R1R2 b - - 0 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r1k3/1Q1b2pr/4pq2/3p4/3P1bP1/8/PP5P/1K1R1R2_b_-_-_0_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 18** — partida `game_25` (MrJavadi1996 vs sprandel1, jogador de black)

- Lance jogado: `f4h2`  |  melhor lance: `h7h2`  |  perda: **120 cp**
- FEN: `3rk3/1Q1b2pr/4pq2/3p4/3P1bP1/8/PP5P/1K1RR3 b - - 2 26`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3rk3/1Q1b2pr/4pq2/3p4/3P1bP1/8/PP5P/1K1RR3_b_-_-_2_26)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 19** — partida `game_25` (MrJavadi1996 vs sprandel1, jogador de black)

- Lance jogado: `g6g4`  |  melhor lance: `h2d6`  |  perda: **430 cp**
- FEN: `3rk3/3b2pr/3Qp1q1/8/3P2P1/8/PP5b/K2RR3 b - - 6 30`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3rk3/3b2pr/3Qp1q1/8/3P2P1/8/PP5b/K2RR3_b_-_-_6_30)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 20** — partida `game_26` (sprandel1 vs addisinia, jogador de white)

- Lance jogado: `f1d3`  |  melhor lance: `f3e5`  |  perda: **100 cp**
- FEN: `r1bqkb1r/ppppnppp/5n2/3Pp3/4P3/5N2/PPP2PPP/RNBQKB1R w KQkq - 3 5`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqkb1r/ppppnppp/5n2/3Pp3/4P3/5N2/PPP2PPP/RNBQKB1R_w_KQkq_-_3_5)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 21** — partida `game_28` (sprandel1 vs DRSENTHIL80, jogador de white)

- Lance jogado: `b3d5`  |  melhor lance: `b3b7`  |  perda: **132 cp**
- FEN: `r3kbnr/pppb1ppp/6q1/8/3P4/1QN1P3/PP1N2PP/n1BK1B1R w kq - 0 13`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kbnr/pppb1ppp/6q1/8/3P4/1QN1P3/PP1N2PP/n1BK1B1R_w_kq_-_0_13)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 22** — partida `game_28` (sprandel1 vs DRSENTHIL80, jogador de white)

- Lance jogado: `d5b7`  |  melhor lance: `f1d3`  |  perda: **764 cp**
- FEN: `r3kbnr/pppb1ppp/8/3Q4/3P4/2NqP3/PP1N2PP/n1B1KB1R w kq - 4 15`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kbnr/pppb1ppp/8/3Q4/3P4/2NqP3/PP1N2PP/n1B1KB1R_w_kq_-_4_15)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 23** — partida `game_29` (Bad-rashes vs sprandel1, jogador de black)

- Lance jogado: `d6e5`  |  melhor lance: `f6e4`  |  perda: **127 cp**
- FEN: `rnbq1rk1/ppp2pbp/3p1np1/4P3/2P1PB2/5N2/PP3PPP/RN1QKB1R b KQ - 0 7`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnbq1rk1/ppp2pbp/3p1np1/4P3/2P1PB2/5N2/PP3PPP/RN1QKB1R_b_KQ_-_0_7)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 24** — partida `game_29` (Bad-rashes vs sprandel1, jogador de black)

- Lance jogado: `b8d8`  |  melhor lance: `c5a4`  |  perda: **75 cp**
- FEN: `1r6/pp3pkp/2p3p1/2n5/P4P2/2P3PB/7P/1R4K1 b - - 0 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1r6/pp3pkp/2p3p1/2n5/P4P2/2P3PB/7P/1R4K1_b_-_-_0_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Peça Pendurada  (`hanging_piece`)

- **Referência Silman:** cap. 1, p. 26 — categoria *dinâmica*
- **Conceito:** Peça do jogador atacada pelo adversário e sem qualquer defesa aliada — pode ser capturada gratuitamente.
- **Implicação estratégica:** Peça pendurada é o erro mais custoso no xadrez amador: perde material sem contrapartida. O jogador deve verificar a segurança de todas as suas peças após cada lance do adversário, antes de escolher seu próprio lance.
- **Detecções no perfil:** 13 erros em 188 ocorrências (7%), magnitude média 186 cp

_Lances-erro detectados (13):_

**Exemplo 1** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `c7c6`  |  melhor lance: `b8c6`  |  perda: **162 cp**
- FEN: `rnbqkbnr/ppp2ppp/8/3pp3/8/1P4P1/PBPPPP1P/RN1QKBNR b KQkq - 1 3`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnbqkbnr/ppp2ppp/8/3pp3/8/1P4P1/PBPPPP1P/RN1QKBNR_b_KQkq_-_1_3)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_3` (sprandel1 vs Leelo1982, jogador de white)

- Lance jogado: `e3f3`  |  melhor lance: `e3c1`  |  perda: **147 cp**
- FEN: `1k1r3r/p5pp/1p3p2/4p3/3q4/R2PQ3/1PP2PPP/4R1K1 w - - 2 23`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1k1r3r/p5pp/1p3p2/4p3/3q4/R2PQ3/1PP2PPP/4R1K1_w_-_-_2_23)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_10` (ccamera vs sprandel1, jogador de black)

- Lance jogado: `g7g6`  |  melhor lance: `e7f5`  |  perda: **394 cp**
- FEN: `r6r/1pk1n1pp/p3bp2/4pN2/4P1P1/2P1KPN1/P6P/R6R b - - 3 19`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r6r/1pk1n1pp/p3bp2/4pN2/4P1P1/2P1KPN1/P6P/R6R_b_-_-_3_19)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_10` (ccamera vs sprandel1, jogador de black)

- Lance jogado: `g8g2`  |  melhor lance: `a8e8`  |  perda: **70 cp**
- FEN: `r5r1/1p3N1p/p1k5/4pp2/8/2P1KP2/P6P/R2R4 b - - 3 27`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r5r1/1p3N1p/p1k5/4pp2/8/2P1KP2/P6P/R2R4_b_-_-_3_27)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_10` (ccamera vs sprandel1, jogador de black)

- Lance jogado: `g2h2`  |  melhor lance: `f5f4`  |  perda: **84 cp**
- FEN: `8/1p2r3/p1k4N/4pp2/7P/2P1KP2/P5r1/R2R4 b - - 0 31`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/1p2r3/p1k4N/4pp2/7P/2P1KP2/P5r1/R2R4_b_-_-_0_31)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_11` (sprandel1 vs RoqueBaby, jogador de white)

- Lance jogado: `d3c4`  |  melhor lance: `d3f5`  |  perda: **64 cp**
- FEN: `3r1rk1/ppqn2pp/2p1Rn2/6B1/3P1b1N/3Q3P/PPP2PP1/R5K1 w - - 1 19`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r1rk1/ppqn2pp/2p1Rn2/6B1/3P1b1N/3Q3P/PPP2PP1/R5K1_w_-_-_1_19)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_13` (Tei-guh vs sprandel1, jogador de black)

- Lance jogado: `c8d7`  |  melhor lance: `c5d4`  |  perda: **115 cp**
- FEN: `r1bqkbnr/pp2pppp/2n5/2ppP3/3P1P2/2P5/PP4PP/RNBQKBNR b KQkq - 0 5`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqkbnr/pp2pppp/2n5/2ppP3/3P1P2/2P5/PP4PP/RNBQKBNR_b_KQkq_-_0_5)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_13` (Tei-guh vs sprandel1, jogador de black)

- Lance jogado: `g3f1`  |  melhor lance: `c5d4`  |  perda: **68 cp**
- FEN: `r2qk2r/pp1bbppp/2n1p3/2ppP3/3P1P2/2P1BNnP/PP1Q4/RN2KBR1 b Qkq - 1 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/pp1bbppp/2n1p3/2ppP3/3P1P2/2P1BNnP/PP1Q4/RN2KBR1_b_Qkq_-_1_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_14` (sprandel1 vs prince_egypt, jogador de white)

- Lance jogado: `g1f3`  |  melhor lance: `e3d3`  |  perda: **501 cp**
- FEN: `r1bqkbnr/1p1p1ppp/p7/4p3/2BnP3/2N1Q3/PPP2PPP/R1B1K1NR w KQkq - 2 7`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqkbnr/1p1p1ppp/p7/4p3/2BnP3/2N1Q3/PPP2PPP/R1B1K1NR_w_KQkq_-_2_7)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 10** — partida `game_27` (ronnelphil vs sprandel1, jogador de black)

- Lance jogado: `b4c2`  |  melhor lance: `f5g4`  |  perda: **393 cp**
- FEN: `2r3k1/1pr1b1pp/p7/3p1b2/1n1P2B1/1PN1P2P/PB4P1/K1R4R b - - 3 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r3k1/1pr1b1pp/p7/3p1b2/1n1P2B1/1PN1P2P/PB4P1/K1R4R_b_-_-_3_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 11** — partida `game_27` (ronnelphil vs sprandel1, jogador de black)

- Lance jogado: `f5d4`  |  melhor lance: `f5e3`  |  perda: **237 cp**
- FEN: `2r3k1/1pr1b1pp/p7/3p1n2/3P4/1PN4P/PB4P1/1KR2R2 b - - 1 28`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r3k1/1pr1b1pp/p7/3p1n2/3P4/1PN4P/PB4P1/1KR2R2_b_-_-_1_28)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 12** — partida `game_27` (ronnelphil vs sprandel1, jogador de black)

- Lance jogado: `e2d4`  |  melhor lance: `e2g3`  |  perda: **87 cp**
- FEN: `6k1/1p2b1pp/p7/3N4/8/1P5P/PB1Kn1P1/8 b - - 2 32`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/6k1/1p2b1pp/p7/3N4/8/1P5P/PB1Kn1P1/8_b_-_-_2_32)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 13** — partida `game_28` (sprandel1 vs DRSENTHIL80, jogador de white)

- Lance jogado: `e1d1`  |  melhor lance: `e1f2`  |  perda: **99 cp**
- FEN: `r3kbnr/pppb1ppp/6q1/8/3P4/1QN1P3/PPnN2PP/R1B1KB1R w KQkq - 1 12`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kbnr/pppb1ppp/6q1/8/3P4/1QN1P3/PPnN2PP/R1B1KB1R_w_KQkq_-_1_12)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Segurança do Rei  (`king_safety`)

- **Referência Silman:** cap. 7, p. 156 — categoria *dinâmica*
- **Conceito:** Avaliação da exposição do rei baseada em cobertura de peões de escudo e atividade adversária.
- **Implicação estratégica:** Rei exposto transforma o jogo em dinâmico: o adversário deve atacar imediatamente. Este desequilíbrio supera fatores posicionais estáticos quando a posição é aguda.
- **Detecções no perfil:** 12 erros em 437 ocorrências (3%), magnitude média 175 cp

_Lances-erro detectados (12):_

**Exemplo 1** — partida `game_1` (sprandel1 vs Pedritos90, jogador de white)

- Lance jogado: `f4f5`  |  melhor lance: `f2e3`  |  perda: **146 cp**
- FEN: `8/3n1p2/3N2kp/2p5/2P1PPp1/1p1P2P1/1P1R1KP1/2r5 w - - 1 32`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/3n1p2/3N2kp/2p5/2P1PPp1/1p1P2P1/1P1R1KP1/2r5_w_-_-_1_32)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `a8c8`  |  melhor lance: `e8f7`  |  perda: **128 cp**
- FEN: `r3k2r/p6p/2pR1p2/1pn5/5P2/1P4P1/P1P1N2P/5RK1 b kq - 1 22`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k2r/p6p/2pR1p2/1pn5/5P2/1P4P1/P1P1N2P/5RK1_b_kq_-_1_22)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_6` (sprandel1 vs Gennnnadiy123, jogador de white)

- Lance jogado: `e3e2`  |  melhor lance: `f3f4`  |  perda: **125 cp**
- FEN: `6k1/ppp3p1/3bR2p/3p2q1/P2P4/2PQKP1P/1P6/8 w - - 2 27`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/6k1/ppp3p1/3bR2p/3p2q1/P2P4/2PQKP1P/1P6/8_w_-_-_2_27)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_10` (ccamera vs sprandel1, jogador de black)

- Lance jogado: `c6b5`  |  melhor lance: `d8c7`  |  perda: **108 cp**
- FEN: `r2k3r/pp2n1pp/2p1bp2/1P2p3/4P1P1/N1P1KPN1/P6P/R6R b - - 0 16`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2k3r/pp2n1pp/2p1bp2/1P2p3/4P1P1/N1P1KPN1/P6P/R6R_b_-_-_0_16)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_10` (ccamera vs sprandel1, jogador de black)

- Lance jogado: `a2a5`  |  melhor lance: `e7e6`  |  perda: **75 cp**
- FEN: `8/1p2k3/p7/4p1K1/7P/2P2P2/r7/4R3 b - - 1 38`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/1p2k3/p7/4p1K1/7P/2P2P2/r7/4R3_b_-_-_1_38)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_10` (ccamera vs sprandel1, jogador de black)

- Lance jogado: `d6e7`  |  melhor lance: `a5a2`  |  perda: **103 cp**
- FEN: `8/1p6/p2k4/r3pPK1/7P/2P5/8/4R3 b - - 0 40`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/1p6/p2k4/r3pPK1/7P/2P5/8/4R3_b_-_-_0_40)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_12` (Ravenlchessl vs sprandel1, jogador de black)

- Lance jogado: `g7g6`  |  melhor lance: `d8d1`  |  perda: **293 cp**
- FEN: `3r4/4kpp1/p3p2p/1pP5/1Pp5/P7/4K3/3R4 b - - 0 39`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r4/4kpp1/p3p2p/1pP5/1Pp5/P7/4K3/3R4_b_-_-_0_39)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_16` (sprandel1 vs krokrer, jogador de white)

- Lance jogado: `g2g4`  |  melhor lance: `f3f4`  |  perda: **289 cp**
- FEN: `8/3k4/rp1p2p1/pR1Pp2p/P6P/2P1KP2/1P4P1/8 w - - 1 39`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/3k4/rp1p2p1/pR1Pp2p/P6P/2P1KP2/1P4P1/8_w_-_-_1_39)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_16` (sprandel1 vs krokrer, jogador de white)

- Lance jogado: `e4f5`  |  melhor lance: `h5h6`  |  perda: **148 cp**
- FEN: `7r/4k3/1p1p4/3Pp2P/P3K2R/2P5/8/8 w - - 5 47`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/7r/4k3/1p1p4/3Pp2P/P3K2R/2P5/8/8_w_-_-_5_47)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 10** — partida `game_16` (sprandel1 vs krokrer, jogador de white)

- Lance jogado: `g5f5`  |  melhor lance: `g5h5`  |  perda: **440 cp**
- FEN: `6r1/5k2/1p1p3P/3Pp1K1/P1P4R/8/8/8 w - - 7 53`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/6r1/5k2/1p1p3P/3Pp1K1/P1P4R/8/8/8_w_-_-_7_53)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 11** — partida `game_28` (sprandel1 vs DRSENTHIL80, jogador de white)

- Lance jogado: `e1d1`  |  melhor lance: `e1f2`  |  perda: **99 cp**
- FEN: `r3kbnr/pppb1ppp/6q1/8/3P4/1QN1P3/PPnN2PP/R1B1KB1R w KQkq - 1 12`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kbnr/pppb1ppp/6q1/8/3P4/1QN1P3/PPnN2PP/R1B1KB1R_w_KQkq_-_1_12)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 12** — partida `game_28` (sprandel1 vs DRSENTHIL80, jogador de white)

- Lance jogado: `d1e1`  |  melhor lance: `d1e2`  |  perda: **142 cp**
- FEN: `r3kbnr/pppb1ppp/8/3Q4/3P4/2N1P3/PPqN2PP/n1BK1B1R w kq - 2 14`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kbnr/pppb1ppp/8/3Q4/3P4/2N1P3/PPqN2PP/n1BK1B1R_w_kq_-_2_14)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Coluna Aberta  (`open_file`)

- **Referência Silman:** cap. 4, p. 89 — categoria *desequilíbrios dinâmicos*
- **Conceito:** Coluna sem peões de nenhuma das cores, ideal para torres. Semi-aberta: coluna sem peão do jogador mas com peão adversário.
- **Implicação estratégica:** Quem controla colunas abertas controla penetração e pode dobrar torres. Ignorar colunas abertas desperdiça a principal força das torres.
- **Detecções no perfil:** 9 erros em 710 ocorrências (1%), magnitude média 173 cp

_Lances-erro detectados (9):_

**Exemplo 1** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `e4d2`  |  melhor lance: `h8e8`  |  perda: **140 cp**
- FEN: `2r4r/p3k2p/7R/1Np5/4nP2/1P4P1/P1P4P/5RK1 b - - 0 26`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r4r/p3k2p/7R/1Np5/4nP2/1P4P1/P1P4P/5RK1_b_-_-_0_26)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_9` (ALZ1828 vs sprandel1, jogador de black)

- Lance jogado: `e2c2`  |  melhor lance: `d8b8`  |  perda: **431 cp**
- FEN: `3r2k1/5pp1/2p2R2/8/2p5/2Pp1N2/PP2rPR1/2K5 b - - 0 27`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r2k1/5pp1/2p2R2/8/2p5/2Pp1N2/PP2rPR1/2K5_b_-_-_0_27)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_12` (Ravenlchessl vs sprandel1, jogador de black)

- Lance jogado: `f5g6`  |  melhor lance: `f5d3`  |  perda: **69 cp**
- FEN: `2r2rk1/5pp1/p2bp2p/1p1n1qB1/1PpP2P1/P1P2N1P/5P2/R2Q1R1K b - - 0 22`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r2rk1/5pp1/p2bp2p/1p1n1qB1/1PpP2P1/P1P2N1P/5P2/R2Q1R1K_b_-_-_0_22)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_12` (Ravenlchessl vs sprandel1, jogador de black)

- Lance jogado: `d6e5`  |  melhor lance: `f8d8`  |  perda: **60 cp**
- FEN: `2r2rk1/5pp1/p2bp2p/1p2N3/1PpP4/P7/4R3/R4K2 b - - 0 34`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r2rk1/5pp1/p2bp2p/1p2N3/1PpP4/P7/4R3/R4K2_b_-_-_0_34)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_13` (Tei-guh vs sprandel1, jogador de black)

- Lance jogado: `e7f5`  |  melhor lance: `f8c8`  |  perda: **83 cp**
- FEN: `5rk1/p2bnp2/1p2p1p1/3pP2p/3P1P1P/P3B3/P4K2/2R2N2 b - - 0 23`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/5rk1/p2bnp2/1p2p1p1/3pP2p/3P1P1P/P3B3/P4K2/2R2N2_b_-_-_0_23)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_13` (Tei-guh vs sprandel1, jogador de black)

- Lance jogado: `g8h7`  |  melhor lance: `f8c8`  |  perda: **104 cp**
- FEN: `5rk1/p2b1p2/1p2p1p1/3pP2p/3P1P1n/P3B1N1/P4K2/6R1 b - - 1 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/5rk1/p2b1p2/1p2p1p1/3pP2p/3P1P1n/P3B1N1/P4K2/6R1_b_-_-_1_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_14` (sprandel1 vs prince_egypt, jogador de white)

- Lance jogado: `g1f3`  |  melhor lance: `e3d3`  |  perda: **501 cp**
- FEN: `r1bqkbnr/1p1p1ppp/p7/4p3/2BnP3/2N1Q3/PPP2PPP/R1B1K1NR w KQkq - 2 7`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqkbnr/1p1p1ppp/p7/4p3/2BnP3/2N1Q3/PPP2PPP/R1B1K1NR_w_KQkq_-_2_7)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_29` (Bad-rashes vs sprandel1, jogador de black)

- Lance jogado: `c4e5`  |  melhor lance: `a8d8`  |  perda: **109 cp**
- FEN: `r7/pp1B1pkp/2p3p1/2P5/2n5/2P5/P4PPP/1R4K1 b - - 0 21`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r7/pp1B1pkp/2p3p1/2P5/2n5/2P5/P4PPP/1R4K1_b_-_-_0_21)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_30` (howyoulikethatD vs sprandel1, jogador de black)

- Lance jogado: `a7a5`  |  melhor lance: `a8b8`  |  perda: **61 cp**
- FEN: `r1bqk2r/p1p1bppp/2n1pn2/2Pp2B1/3P4/4P2P/P4PP1/RN1QKBNR b KQkq - 0 8`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqk2r/p1p1bppp/2n1pn2/2Pp2B1/3P4/4P2P/P4PP1/RN1QKBNR_b_KQkq_-_0_8)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Maioria de Peões  (`pawn_majority`)

- **Referência Silman:** cap. 8, p. 185 — categoria *estrutura de peões*
- **Conceito:** Superioridade numérica de peões em um flanco — permite criar um peão passado através de avanços.
- **Implicação estratégica:** Maioria saudável de peões deve ser avançada para criar um peão passado. Ignorar a maioria desperdiça uma vantagem estrutural de longo prazo.
- **Detecções no perfil:** 7 erros em 418 ocorrências (2%), magnitude média 126 cp

_Lances-erro detectados (7):_

**Exemplo 1** — partida `game_3` (sprandel1 vs Leelo1982, jogador de white)

- Lance jogado: `f3e3`  |  melhor lance: `a5b6`  |  perda: **116 cp**
- FEN: `1k1r3r/p1p3pp/1p2pp2/P2q4/8/3P1Q2/1PP2PPP/R3R1K1 w - - 1 20`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1k1r3r/p1p3pp/1p2pp2/P2q4/8/3P1Q2/1PP2PPP/R3R1K1_w_-_-_1_20)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_5` (Sibirskii01 vs sprandel1, jogador de black)

- Lance jogado: `d2d3`  |  melhor lance: `b6f2`  |  perda: **169 cp**
- FEN: `4k1nr/p4ppp/1b2p3/8/1PN5/2P5/P2r1PPP/R3R1K1 b k - 1 18`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/4k1nr/p4ppp/1b2p3/8/1PN5/2P5/P2r1PPP/R3R1K1_b_k_-_1_18)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_13` (Tei-guh vs sprandel1, jogador de black)

- Lance jogado: `g3f1`  |  melhor lance: `c5d4`  |  perda: **68 cp**
- FEN: `r2qk2r/pp1bbppp/2n1p3/2ppP3/3P1P2/2P1BNnP/PP1Q4/RN2KBR1 b Qkq - 1 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/pp1bbppp/2n1p3/2ppP3/3P1P2/2P1BNnP/PP1Q4/RN2KBR1_b_Qkq_-_1_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_13` (Tei-guh vs sprandel1, jogador de black)

- Lance jogado: `g7g6`  |  melhor lance: `c5d4`  |  perda: **129 cp**
- FEN: `r2qk2r/pp1bbppp/2n1p3/2ppP3/3P1P2/2P1BN1P/PP1Q4/RN2KR2 b Qkq - 0 12`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2qk2r/pp1bbppp/2n1p3/2ppP3/3P1P2/2P1BN1P/PP1Q4/RN2KR2_b_Qkq_-_0_12)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_16` (sprandel1 vs krokrer, jogador de white)

- Lance jogado: `a4c6`  |  melhor lance: `d4d6`  |  perda: **206 cp**
- FEN: `3r4/1p5p/r1nppkp1/p7/B2RP3/2P2P2/PP3KPP/3R4 w - - 4 29`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r4/1p5p/r1nppkp1/p7/B2RP3/2P2P2/PP3KPP/3R4_w_-_-_4_29)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_17` (Anacletoo vs sprandel1, jogador de black)

- Lance jogado: `g5f6`  |  melhor lance: `c7c3`  |  perda: **75 cp**
- FEN: `7R/2r2p2/p3p1p1/Pp1p2k1/1P2n3/2P5/2K5/7R b - - 5 52`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/7R/2r2p2/p3p1p1/Pp1p2k1/1P2n3/2P5/2K5/7R_b_-_-_5_52)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_19` (sprandel1 vs moralis, jogador de white)

- Lance jogado: `e1g1`  |  melhor lance: `d5c6`  |  perda: **116 cp**
- FEN: `rn1q1rk1/pp2ppbp/2p2np1/3P4/6b1/2NP1N2/PPPBBPPP/R2QK2R w KQ - 0 8`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn1q1rk1/pp2ppbp/2p2np1/3P4/6b1/2NP1N2/PPPBBPPP/R2QK2R_w_KQ_-_0_8)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Vantagem de Espaço  (`space_advantage`)

- **Referência Silman:** cap. 8, p. 178 — categoria *desequilíbrios estáticos*
- **Conceito:** Controle de mais casas no tabuleiro, especialmente no campo adversário.
- **Implicação estratégica:** Mais espaço significa mais opções e restrição das peças adversárias. Deve ser explorado com avanços de peões ou criação de fraquezas no campo do adversário.
- **Detecções no perfil:** 6 erros em 123 ocorrências (5%), magnitude média 174 cp

_Lances-erro detectados (6):_

**Exemplo 1** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `g3g4`  |  melhor lance: `g3g1`  |  perda: **111 cp**
- FEN: `8/4Nk1p/8/8/2K1RP1P/6r1/3r4/8 b - - 3 45`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/4Nk1p/8/8/2K1RP1P/6r1/3r4/8_b_-_-_3_45)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_7` (sprandel1 vs chessrick, jogador de white)

- Lance jogado: `c1f4`  |  melhor lance: `e4e5`  |  perda: **53 cp**
- FEN: `rnbq1rnk/ppp1bpp1/3pp2p/8/2PPP3/2NB1N2/PP3PPP/R1BQR1K1 w - - 6 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnbq1rnk/ppp1bpp1/3pp2p/8/2PPP3/2NB1N2/PP3PPP/R1BQR1K1_w_-_-_6_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_13` (Tei-guh vs sprandel1, jogador de black)

- Lance jogado: `a2a4`  |  melhor lance: `b5c4`  |  perda: **223 cp**
- FEN: `8/p4p1k/1p2p1p1/1b1pP2p/3P1P2/1K2B1R1/r7/8 b - - 1 34`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/p4p1k/1p2p1p1/1b1pP2p/3P1P2/1K2B1R1/r7/8_b_-_-_1_34)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_27` (ronnelphil vs sprandel1, jogador de black)

- Lance jogado: `e8g8`  |  melhor lance: `b4c2`  |  perda: **161 cp**
- FEN: `2r1k2r/pp1qb1pp/8/3p1b2/1n1P4/1PN1P2P/PB2Q1P1/K2R1B1R b k - 4 20`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r1k2r/pp1qb1pp/8/3p1b2/1n1P4/1PN1P2P/PB2Q1P1/K2R1B1R_b_k_-_4_20)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_27` (ronnelphil vs sprandel1, jogador de black)

- Lance jogado: `c8c7`  |  melhor lance: `b4d3`  |  perda: **274 cp**
- FEN: `2r2rk1/pp1qb1pp/8/3p1b2/1n1P4/1PN1P2P/PB2Q1P1/K1R2B1R b - - 6 21`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r2rk1/pp1qb1pp/8/3p1b2/1n1P4/1PN1P2P/PB2Q1P1/K1R2B1R_b_-_-_6_21)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_27` (ronnelphil vs sprandel1, jogador de black)

- Lance jogado: `c2e3`  |  melhor lance: `f5g4`  |  perda: **220 cp**
- FEN: `2r3k1/1pr1b1pp/p7/3p1b2/3P2B1/1PN1P2P/PBn3P1/1KR4R b - - 5 26`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r3k1/1pr1b1pp/p7/3p1b2/3P2B1/1PN1P2P/PBn3P1/1KR4R_b_-_-_5_26)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Atividade de Peças  (`piece_activity`)

- **Referência Silman:** cap. 2, p. 45 — categoria *desequilíbrios dinâmicos*
- **Conceito:** Comparação entre a mobilidade das peças do jogador e as adversárias — peças ativas controlam mais casas.
- **Implicação estratégica:** Peças ativas são mais valiosas que material passivo. Deve-se sempre procurar melhorar a peça menos ativa antes de qualquer outra ação.
- **Detecções no perfil:** 4 erros em 105 ocorrências (4%), magnitude média 84 cp

_Lances-erro detectados (4):_

**Exemplo 1** — partida `game_2` (Player_of_Chess_Games vs sprandel1, jogador de black)

- Lance jogado: `g3g4`  |  melhor lance: `g3g1`  |  perda: **111 cp**
- FEN: `8/4Nk1p/8/8/2K1RP1P/6r1/3r4/8 b - - 3 45`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/4Nk1p/8/8/2K1RP1P/6r1/3r4/8_b_-_-_3_45)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_3` (sprandel1 vs Leelo1982, jogador de white)

- Lance jogado: `c6g6`  |  melhor lance: `c2c4`  |  perda: **71 cp**
- FEN: `8/kr6/1pQ3p1/p3pp1p/3r4/3P2P1/2P2P1P/R5K1 w - - 0 38`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/kr6/1pQ3p1/p3pp1p/3r4/3P2P1/2P2P1P/R5K1_w_-_-_0_38)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_3` (sprandel1 vs Leelo1982, jogador de white)

- Lance jogado: `c5b4`  |  melhor lance: `g1g2`  |  perda: **68 cp**
- FEN: `8/3r4/kr6/1pQ4p/p7/6P1/5P1P/1R4K1 w - - 6 49`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/3r4/kr6/1pQ4p/p7/6P1/5P1P/1R4K1_w_-_-_6_49)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_10` (ccamera vs sprandel1, jogador de black)

- Lance jogado: `g2h2`  |  melhor lance: `f5f4`  |  perda: **84 cp**
- FEN: `8/1p2r3/p1k4N/4pp2/7P/2P1KP2/P5r1/R2R4 b - - 0 31`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/1p2r3/p1k4N/4pp2/7P/2P1KP2/P5r1/R2R4_b_-_-_0_31)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Casa Fraca  (`weak_square`)

- **Referência Silman:** cap. 3, p. 67 — categoria *desequilíbrios estáticos*
- **Conceito:** Casa que não pode ser defendida por peões e pode ser ocupada por peças adversárias.
- **Implicação estratégica:** Permite infiltração de cavalos e bispos adversários em posições fixas. Deve ser bloqueada com peças ou eliminada estruturalmente.
- **Detecções no perfil:** 4 erros em 278 ocorrências (1%), magnitude média 134 cp

_Lances-erro detectados (4):_

**Exemplo 1** — partida `game_7` (sprandel1 vs chessrick, jogador de white)

- Lance jogado: `g3f4`  |  melhor lance: `a5a6`  |  perda: **187 cp**
- FEN: `1r4nk/R5p1/2p1p3/P1PpP1p1/3P1p2/2Nn2P1/3B1P1P/6K1 w - - 0 28`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1r4nk/R5p1/2p1p3/P1PpP1p1/3P1p2/2Nn2P1/3B1P1P/6K1_w_-_-_0_28)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_16` (sprandel1 vs krokrer, jogador de white)

- Lance jogado: `e3e4`  |  melhor lance: `h5h6`  |  perda: **53 cp**
- FEN: `7r/3k4/1p1p4/3Pp2P/P6R/2P1K3/8/8 w - - 3 46`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/7r/3k4/1p1p4/3Pp2P/P6R/2P1K3/8/8_w_-_-_3_46)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_16` (sprandel1 vs krokrer, jogador de white)

- Lance jogado: `e4f5`  |  melhor lance: `h5h6`  |  perda: **148 cp**
- FEN: `7r/4k3/1p1p4/3Pp2P/P3K2R/2P5/8/8 w - - 5 47`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/7r/4k3/1p1p4/3Pp2P/P3K2R/2P5/8/8_w_-_-_5_47)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_16` (sprandel1 vs krokrer, jogador de white)

- Lance jogado: `f5g5`  |  melhor lance: `h6h7`  |  perda: **146 cp**
- FEN: `7r/5k2/1p1p3P/3PpK2/P1P4R/8/8/8 w - - 5 52`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/7r/5k2/1p1p3P/3PpK2/P1P4R/8/8/8_w_-_-_5_52)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Peão Atrasado  (`backward_pawn`)

- **Referência Silman:** cap. 5, p. 109 — categoria *estrutura de peões*
- **Conceito:** Peão que não pode avançar com segurança porque a casa à sua frente é controlada por um peão adversário, e não tem apoio de peões aliados por trás nas colunas adjacentes.
- **Implicação estratégica:** Peão atrasado é fraqueza estrutural permanente: preso na coluna semi-aberta, torna-se alvo de pressão de torres. O adversário deve dobrar torres nessa coluna; o jogador deve buscar avançar o peão quando possível ou trocá-lo para eliminar a fraqueza.
- **Detecções no perfil:** 3 erros em 258 ocorrências (1%), magnitude média 116 cp

_Lances-erro detectados (3):_

**Exemplo 1** — partida `game_7` (sprandel1 vs chessrick, jogador de white)

- Lance jogado: `d1c2`  |  melhor lance: `a4a5`  |  perda: **106 cp**
- FEN: `r1bq1rnk/p2nb1p1/1pp1p2p/2PpPp2/PP1P1B2/2NB1N2/5PPP/R2QR1K1 w - - 0 14`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bq1rnk/p2nb1p1/1pp1p2p/2PpPp2/PP1P1B2/2NB1N2/5PPP/R2QR1K1_w_-_-_0_14)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_7` (sprandel1 vs chessrick, jogador de white)

- Lance jogado: `g3f4`  |  melhor lance: `a5a6`  |  perda: **187 cp**
- FEN: `1r4nk/R5p1/2p1p3/P1PpP1p1/3P1p2/2Nn2P1/3B1P1P/6K1 w - - 0 28`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1r4nk/R5p1/2p1p3/P1PpP1p1/3P1p2/2Nn2P1/3B1P1P/6K1_w_-_-_0_28)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_22` (sprandel1 vs Jcksn04, jogador de white)

- Lance jogado: `f1e1`  |  melhor lance: `d3d4`  |  perda: **54 cp**
- FEN: `r2r2k1/pppqbppp/2np1n2/4p3/4P3/2PPBN1P/PPQN1PP1/R4RK1 w - - 9 12`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2r2k1/pppqbppp/2np1n2/4p3/4P3/2PPBN1P/PPQN1PP1/R4RK1_w_-_-_9_12)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_


---

## Perfil 3 — Sprandel27

**Dados gerais**

| Partidas | Posições | Erros | Taxa de erro | Fraquezas recorrentes |
|----------|----------|-------|--------------|-----------------------|
| 30 | 866 | 166 | 19.2% | 5 |

#### Diagnóstico de causa raiz

- **Causa raiz:** Falha na Avaliação de Ameaças Pré-Lance (`threat_blindness_before_execution`)
- **Descrição:** O jogador consistentemente falha em realizar uma verificação de segurança de todas as peças e ameaças (tanto do adversário quanto próprias) antes de executar um lance. Isso se manifesta como um padrão sistemático: o jogador identifica um lance candidato baseado em uma ideia ofensiva (ataque, iniciativa ou plano posicional) e o executa sem verificar se suas próprias peças ficam penduradas, se seu rei fica exposto, ou se existe uma continuação tática mais forte. O problema raiz não é falta de compreensão estratégica, mas um processo de cálculo truncado—o jogador avalia apenas o propósito ofensivo do seu lance sem escanear as vulnerabilidades táticas imediatas criadas ou deixadas sem resolução por aquele lance.
- **Padrão cognitivo:** O jogador opera com um processo de pensamento 'ideia primeiro, segurança nunca'. Ele identifica uma ideia estratégica ou de ataque e a executa imediatamente sem uma etapa de verificação. O hábito crítico ausente é uma seleção de lance em duas fases: (1) gerar lances candidatos baseados em planos e ideias, depois (2) ANTES de executar, realizar uma auditoria defensiva—verificar se alguma de suas peças está pendurada, se seu rei está seguro, e se o adversário tem algum golpe tático na posição resultante. O padrão repetido do jogador de perder a mesma tática em vários lances consecutivos (Bxc7 no game_4) e caminhar para perda material enquanto persegue objetivos ofensivos (Cxf2 no game_22, Bxb7 no game_27) confirma que a fase de verificação está inteiramente ausente do seu processo de tomada de decisão.
- **Confiança:** HIGH
- **Avaliação qualitativa do diagnóstico:** _( ) coerente com os dados   ( ) discordo — justificativa:_

**Classificação das fraquezas**

| Conceito | Classificação | Justificativa (resumo) |
|----------|---------------|------------------------|
| hanging_piece | PRIMARY | Manifestação central da causa raiz. Em 12 posições com erro, o jogador repetidamente joga  |
| missed_tactic | PRIMARY | Taxa de erro de 100% em todas as 8 ocorrências prova que o jogador tem zero escaneamento t |
| king_safety | SECONDARY | Erros de segurança do rei são consequência derivada da mesma cegueira a ameaças. O jogador |
| space_advantage | SECONDARY | Os 6 erros aqui se sobrepõem significativamente com posições de peça pendurada e segurança |
| backward_pawn | NOISE | Apenas 1,9% de taxa de erro em 262 ocorrências indica que o jogador lida com estrutura de  |

**Plano de estudo (prioridade)**

| # | Conceito | Capítulo | Página | Motivo (resumo) |
|---|----------|----------|--------|-----------------|
| 1 | missed_tactic | 1 | 26 | Taxa de erro de 100% é o sinal mais urgente. O jogador deve construir uma checkl |
| 2 | hanging_piece | 1 | 26 | Maior contagem de ocorrências entre erros (12 instâncias) e o padrão de perda ma |
| 3 | king_safety | 7 | 156 | Maior magnitude média de erro (187,6cp) significa que quando isso dá errado, dá  |
| 4 | space_advantage | 8 | 178 | Só é relevante após a disciplina tática estar estabelecida. O jogador às vezes t |
| 5 | backward_pawn | 5 | 109 | Baixa taxa de erro indica que este não é um gargalo atual. Pode ser estudado dep |

- **Avaliação qualitativa das recomendações:** _( ) relevantes e acionáveis   ( ) parcialmente   — justificativa:_

#### Detecções por conceito (lances-erro para análise qualitativa)

### Peça Pendurada  (`hanging_piece`)

- **Referência Silman:** cap. 1, p. 26 — categoria *dinâmica*
- **Conceito:** Peça do jogador atacada pelo adversário e sem qualquer defesa aliada — pode ser capturada gratuitamente.
- **Implicação estratégica:** Peça pendurada é o erro mais custoso no xadrez amador: perde material sem contrapartida. O jogador deve verificar a segurança de todas as suas peças após cada lance do adversário, antes de escolher seu próprio lance.
- **Detecções no perfil:** 12 erros em 146 ocorrências (8%), magnitude média 171 cp

_Lances-erro detectados (12):_

**Exemplo 1** — partida `game_2` (cz1728 vs Sprandel27, jogador de black)

- Lance jogado: `c3a1`  |  melhor lance: `d4d3`  |  perda: **138 cp**
- FEN: `4k2r/1RBr1pp1/p1n1p1p1/6P1/3p3P/P1q5/2P1QP2/3K3R b k - 0 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/4k2r/1RBr1pp1/p1n1p1p1/6P1/3p3P/P1q5/2P1QP2/3K3R_b_k_-_0_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_2` (cz1728 vs Sprandel27, jogador de black)

- Lance jogado: `a2e2`  |  melhor lance: `a2d5`  |  perda: **82 cp**
- FEN: `5rk1/3r1pp1/R1n1p1p1/6P1/7P/P2PK1B1/q3QP2/8 b - - 2 31`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/5rk1/3r1pp1/R1n1p1p1/6P1/7P/P2PK1B1/q3QP2/8_b_-_-_2_31)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_4` (Sprandel27 vs KZaus, jogador de white)

- Lance jogado: `c2c8`  |  melhor lance: `c2d2`  |  perda: **238 cp**
- FEN: `6k1/p3pp2/1p2n1p1/4N2p/3PN1P1/4qP2/PPQ3KP/8 w - - 0 28`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/6k1/p3pp2/1p2n1p1/4N2p/3PN1P1/4qP2/PPQ3KP/8_w_-_-_0_28)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_5` (Sprandel27 vs pedroqui222, jogador de white)

- Lance jogado: `f4d6`  |  melhor lance: `c3d5`  |  perda: **149 cp**
- FEN: `r1b1k2r/1pqp1p2/p1nbp1p1/2p4p/5B2/P1NP3P/BPP2PP1/R2QR1K1 w kq - 2 14`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1k2r/1pqp1p2/p1nbp1p1/2p4p/5B2/P1NP3P/BPP2PP1/R2QR1K1_w_kq_-_2_14)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_6` (Moripelang00 vs Sprandel27, jogador de black)

- Lance jogado: `g8h8`  |  melhor lance: `c5b5`  |  perda: **99 cp**
- FEN: `r5k1/pp1bq1pp/5p2/2rPp3/3pP3/PQ3N2/1P3PPP/R4RK1 b - - 8 19`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r5k1/pp1bq1pp/5p2/2rPp3/3pP3/PQ3N2/1P3PPP/R4RK1_b_-_-_8_19)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_11` (Sprandel27 vs fdsakjhg, jogador de white)

- Lance jogado: `c3b5`  |  melhor lance: `b3c4`  |  perda: **123 cp**
- FEN: `2k4r/1b1pnR1p/1pn5/5p2/5P2/1BN5/PPP1NqP1/2K4R w - - 3 27`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2k4r/1b1pnR1p/1pn5/5p2/5P2/1BN5/PPP1NqP1/2K4R_w_-_-_3_27)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_12` (Sprandel27 vs BJzza801, jogador de white)

- Lance jogado: `d5e7`  |  melhor lance: `d5c7`  |  perda: **440 cp**
- FEN: `r6r/pp2b1pp/4k3/1Q1Np1Pn/4b2P/4B3/PPP5/2K4R w - - 0 24`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r6r/pp2b1pp/4k3/1Q1Np1Pn/4b2P/4B3/PPP5/2K4R_w_-_-_0_24)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_19` (Sprandel27 vs elshan013, jogador de white)

- Lance jogado: `f1e2`  |  melhor lance: `e1d1`  |  perda: **141 cp**
- FEN: `r1b1k1nr/p1pp1pBp/1pn5/8/4q3/5NQ1/PPP2PPP/R3KB1R w KQkq - 0 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b1k1nr/p1pp1pBp/1pn5/8/4q3/5NQ1/PPP2PPP/R3KB1R_w_KQkq_-_0_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_22` (Nickmofry vs Sprandel27, jogador de black)

- Lance jogado: `e4f2`  |  melhor lance: `e4d6`  |  perda: **217 cp**
- FEN: `r3kb1r/ppqn1ppp/2p5/4pb2/4n2N/3PB1PP/PPP2PB1/R2QK2R b KQkq - 1 10`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kb1r/ppqn1ppp/2p5/4pb2/4n2N/3PB1PP/PPP2PB1/R2QK2R_b_KQkq_-_1_10)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 10** — partida `game_27` (Sprandel27 vs Kruppinho, jogador de white)

- Lance jogado: `f3b7`  |  melhor lance: `f3d1`  |  perda: **148 cp**
- FEN: `r3kbnr/ppp1pppp/8/8/3n4/2NP1B2/PPP2PPP/R1B1K2R w KQkq - 1 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3kbnr/ppp1pppp/8/8/3n4/2NP1B2/PPP2PPP/R1B1K2R_w_KQkq_-_1_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 11** — partida `game_29` (MUHAMMADadnanGG vs Sprandel27, jogador de black)

- Lance jogado: `g8f7`  |  melhor lance: `d8d6`  |  perda: **173 cp**
- FEN: `3r2k1/2b3p1/p3R2p/1p3p2/8/P1B4P/1P4K1/8 b - - 0 30`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r2k1/2b3p1/p3R2p/1p3p2/8/P1B4P/1P4K1/8_b_-_-_0_30)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 12** — partida `game_30` (Sprandel27 vs samyceram, jogador de white)

- Lance jogado: `e3h6`  |  melhor lance: `g3c7`  |  perda: **99 cp**
- FEN: `5rk1/7p/p1p3p1/Pp1p4/1q1Pp3/1P2B1QP/6P1/2R3K1 w - - 3 36`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/5rk1/7p/p1p3p1/Pp1p4/1q1Pp3/1P2B1QP/6P1/2R3K1_w_-_-_3_36)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Segurança do Rei  (`king_safety`)

- **Referência Silman:** cap. 7, p. 156 — categoria *dinâmica*
- **Conceito:** Avaliação da exposição do rei baseada em cobertura de peões de escudo e atividade adversária.
- **Implicação estratégica:** Rei exposto transforma o jogo em dinâmico: o adversário deve atacar imediatamente. Este desequilíbrio supera fatores posicionais estáticos quando a posição é aguda.
- **Detecções no perfil:** 11 erros em 301 ocorrências (4%), magnitude média 188 cp

_Lances-erro detectados (11):_

**Exemplo 1** — partida `game_3` (Sprandel27 vs jonathanquilles, jogador de white)

- Lance jogado: `b3b4`  |  melhor lance: `e1f1`  |  perda: **132 cp**
- FEN: `2kr3r/pppqp1b1/2n4p/5p2/3P1Bb1/PPN1PN2/2P2PP1/R2QK2R w KQ - 1 16`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2kr3r/pppqp1b1/2n4p/5p2/3P1Bb1/PPN1PN2/2P2PP1/R2QK2R_w_KQ_-_1_16)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_7` (TheQuestionMan vs Sprandel27, jogador de black)

- Lance jogado: `b8c6`  |  melhor lance: `e8g8`  |  perda: **176 cp**
- FEN: `1nbqk2r/2p1bppp/1p2pn2/2Pp4/1P1P4/2N1PN2/3B1PPP/Q3KB1R b Kk - 0 11`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/1nbqk2r/2p1bppp/1p2pn2/2Pp4/1P1P4/2N1PN2/3B1PPP/Q3KB1R_b_Kk_-_0_11)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_8` (Sbdxhchsbsb vs Sprandel27, jogador de black)

- Lance jogado: `f6e5`  |  melhor lance: `g6g5`  |  perda: **365 cp**
- FEN: `r4r2/pb5p/1p1ppkp1/2p5/4P2Q/2NP1q2/PPP2P2/2KR3R b - - 3 20`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r4r2/pb5p/1p1ppkp1/2p5/4P2Q/2NP1q2/PPP2P2/2KR3R_b_-_-_3_20)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_12` (Sprandel27 vs BJzza801, jogador de white)

- Lance jogado: `f2f3`  |  melhor lance: `c1g5`  |  perda: **69 cp**
- FEN: `r1bqkbnr/ppp1n1pp/3p4/3Ppp2/4P3/2NB4/PPP2PPP/R1BQK1NR w KQkq - 0 6`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1bqkbnr/ppp1n1pp/3p4/3Ppp2/4P3/2NB4/PPP2PPP/R1BQK1NR_w_KQkq_-_0_6)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_14` (Sprandel27 vs farhadbandi, jogador de white)

- Lance jogado: `f2f4`  |  melhor lance: `d2f3`  |  perda: **301 cp**
- FEN: `r5k1/pp1b1rb1/n3p1p1/2ppPnBp/3P3P/2P5/PPBN1PQ1/R3K2R w KQ - 2 21`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r5k1/pp1b1rb1/n3p1p1/2ppPnBp/3P3P/2P5/PPBN1PQ1/R3K2R_w_KQ_-_2_21)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_14` (Sprandel27 vs farhadbandi, jogador de white)

- Lance jogado: `b2b3`  |  melhor lance: `g5f6`  |  perda: **112 cp**
- FEN: `5r2/p2b1rbk/n3p1p1/1p1pPnBp/2pP1P1P/2P2N2/PPB1Q3/2KR3R w - - 0 25`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/5r2/p2b1rbk/n3p1p1/1p1pPnBp/2pP1P1P/2P2N2/PPB1Q3/2KR3R_w_-_-_0_25)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_14` (Sprandel27 vs farhadbandi, jogador de white)

- Lance jogado: `d1d3`  |  melhor lance: `c1b2`  |  perda: **90 cp**
- FEN: `2r5/p2b1rbk/n3p1p1/1p1pPnBp/3P1P1P/1PP2N2/2B1Q3/2KR3R w - - 1 27`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2r5/p2b1rbk/n3p1p1/1p1pPnBp/3P1P1P/1PP2N2/2B1Q3/2KR3R_w_-_-_1_27)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_20` (Diomollura vs Sprandel27, jogador de black)

- Lance jogado: `e7c6`  |  melhor lance: `e8g8`  |  perda: **82 cp**
- FEN: `r3k2r/1p2nppp/1q2p3/pN1pPb2/Pb1P4/1Q6/1P2BPPP/R1B2RK1 b kq - 4 14`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k2r/1p2nppp/1q2p3/pN1pPb2/Pb1P4/1Q6/1P2BPPP/R1B2RK1_b_kq_-_4_14)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 9** — partida `game_20` (Diomollura vs Sprandel27, jogador de black)

- Lance jogado: `d8d6`  |  melhor lance: `e7f8`  |  perda: **634 cp**
- FEN: `r2r4/1p2kppp/8/pB1pqp2/Pb6/1Q1R4/1P3PPP/5RK1 b - - 3 21`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2r4/1p2kppp/8/pB1pqp2/Pb6/1Q1R4/1P3PPP/5RK1_b_-_-_3_21)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 10** — partida `game_29` (MUHAMMADadnanGG vs Sprandel27, jogador de black)

- Lance jogado: `g8f7`  |  melhor lance: `d8d6`  |  perda: **173 cp**
- FEN: `3r2k1/2b3p1/p3R2p/1p3p2/8/P1B4P/1P4K1/8 b - - 0 30`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/3r2k1/2b3p1/p3R2p/1p3p2/8/P1B4P/1P4K1/8_b_-_-_0_30)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 11** — partida `game_30` (Sprandel27 vs samyceram, jogador de white)

- Lance jogado: `f2f4`  |  melhor lance: `g1f3`  |  perda: **64 cp**
- FEN: `rnbqkbnr/pp3ppp/2ppp3/8/2PPP3/8/PP3PPP/RNBQKBNR w KQkq - 0 4`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnbqkbnr/pp3ppp/2ppp3/8/2PPP3/8/PP3PPP/RNBQKBNR_w_KQkq_-_0_4)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Tática Perdida  (`missed_tactic`)

- **Referência Silman:** cap. 1, p. 26 — categoria *tática*
- **Conceito:** Oportunidade tática concreta deixada passar — tipicamente uma peça adversária pendurada que o jogador não capturou, ou uma troca que ganhava material.
- **Implicação estratégica:** Indica falha de visão tática/atenção, não de compreensão estratégica. Treina-se com exercícios de tática e checagem sistemática de capturas e ameaças antes de cada lance.
- **Detecções no perfil:** 8 erros em 8 ocorrências (100%), magnitude média 117 cp

_Lances-erro detectados (8):_

**Exemplo 1** — partida `game_3` (Sprandel27 vs jonathanquilles, jogador de white)

- Lance jogado: `a3a7`  |  melhor lance: `g4f5`  |  perda: **177 cp**
- FEN: `2k1r3/ppp5/7p/5p2/1PP2PP1/R7/4NKP1/7r w - - 0 30`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2k1r3/ppp5/7p/5p2/1PP2PP1/R7/4NKP1/7r_w_-_-_0_30)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_4` (Sprandel27 vs KZaus, jogador de white)

- Lance jogado: `c2c3`  |  melhor lance: `f4c7`  |  perda: **82 cp**
- FEN: `rn2k1nr/ppp1ppbp/6p1/3p1q2/3P1B2/4PN2/PPP2PPP/RN1QK2R w KQkq - 0 7`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn2k1nr/ppp1ppbp/6p1/3p1q2/3P1B2/4PN2/PPP2PPP/RN1QK2R_w_KQkq_-_0_7)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_4` (Sprandel27 vs KZaus, jogador de white)

- Lance jogado: `b1d2`  |  melhor lance: `f4c7`  |  perda: **125 cp**
- FEN: `r3k1nr/p1pnppbp/1p4p1/3p1q2/3P1B2/1QP1PN2/PP3PPP/RN2K2R w KQkq - 0 9`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k1nr/p1pnppbp/1p4p1/3p1q2/3P1B2/1QP1PN2/PP3PPP/RN2K2R_w_KQkq_-_0_9)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_4` (Sprandel27 vs KZaus, jogador de white)

- Lance jogado: `a1c1`  |  melhor lance: `f4c7`  |  perda: **160 cp**
- FEN: `r3k2r/p1pnppbp/1p3np1/3p1q2/3P1B2/1QP1PN2/PP1N1PPP/R3K2R w KQkq - 2 10`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r3k2r/p1pnppbp/1p3np1/3p1q2/3P1B2/1QP1PN2/PP1N1PPP/R3K2R_w_KQkq_-_2_10)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_4` (Sprandel27 vs KZaus, jogador de white)

- Lance jogado: `c1c6`  |  melhor lance: `g3c7`  |  perda: **200 cp**
- FEN: `r4rk1/p1nnppbp/1pp3p1/5q2/3P4/1Q2PNB1/PP1N1PPP/2R1K2R w K - 2 14`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r4rk1/p1nnppbp/1pp3p1/5q2/3P4/1Q2PNB1/PP1N1PPP/2R1K2R_w_K_-_2_14)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_10` (arsyila03 vs Sprandel27, jogador de black)

- Lance jogado: `g7e5`  |  melhor lance: `d6e5`  |  perda: **52 cp**
- FEN: `2rqk1nr/1b3pbp/p2pp1p1/1p1PN3/4P3/PBN1B3/1P1Q1PPP/R4RK1 b k - 0 17`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2rqk1nr/1b3pbp/p2pp1p1/1p1PN3/4P3/PBN1B3/1P1Q1PPP/R4RK1_b_k_-_0_17)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 7** — partida `game_11` (Sprandel27 vs fdsakjhg, jogador de white)

- Lance jogado: `d8b6`  |  melhor lance: `h2g3`  |  perda: **80 cp**
- FEN: `2kB2nr/pb1p3p/1pn1qpp1/8/4P3/2N2Pb1/PPP3PP/2KR1BNR w - - 0 15`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2kB2nr/pb1p3p/1pn1qpp1/8/4P3/2N2Pb1/PPP3PP/2KR1BNR_w_-_-_0_15)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 8** — partida `game_23` (Sprandel27 vs akdjan_n, jogador de white)

- Lance jogado: `b5d7`  |  melhor lance: `d1d5`  |  perda: **57 cp**
- FEN: `rn1qk1nr/pp1b1ppp/8/1Bbp4/8/2N5/PPP2PPP/R1BQK1NR w KQkq - 2 8`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rn1qk1nr/pp1b1ppp/8/1Bbp4/8/2N5/PPP2PPP/R1BQK1NR_w_KQkq_-_2_8)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Vantagem de Espaço  (`space_advantage`)

- **Referência Silman:** cap. 8, p. 178 — categoria *desequilíbrios estáticos*
- **Conceito:** Controle de mais casas no tabuleiro, especialmente no campo adversário.
- **Implicação estratégica:** Mais espaço significa mais opções e restrição das peças adversárias. Deve ser explorado com avanços de peões ou criação de fraquezas no campo do adversário.
- **Detecções no perfil:** 6 erros em 116 ocorrências (5%), magnitude média 258 cp

_Lances-erro detectados (6):_

**Exemplo 1** — partida `game_4` (Sprandel27 vs KZaus, jogador de white)

- Lance jogado: `f2f3`  |  melhor lance: `c2c8`  |  perda: **244 cp**
- FEN: `6k1/p3pp2/1p2n1p1/4N2p/3PN1Pq/4P3/PPQ2P1P/6K1 w - - 2 26`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/6k1/p3pp2/1p2n1p1/4N2p/3PN1Pq/4P3/PPQ2P1P/6K1_w_-_-_2_26)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_4` (Sprandel27 vs KZaus, jogador de white)

- Lance jogado: `c8c3`  |  melhor lance: `g2f1`  |  perda: **855 cp**
- FEN: `2Q5/p3ppk1/1p2n1p1/4N2p/3PN1P1/4qP2/PP4KP/8 w - - 2 29`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2Q5/p3ppk1/1p2n1p1/4N2p/3PN1P1/4qP2/PP4KP/8_w_-_-_2_29)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_8` (Sbdxhchsbsb vs Sprandel27, jogador de black)

- Lance jogado: `f6e5`  |  melhor lance: `g6g5`  |  perda: **365 cp**
- FEN: `r4r2/pb5p/1p1ppkp1/2p5/4P2Q/2NP1q2/PPP2P2/2KR3R b - - 3 20`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r4r2/pb5p/1p1ppkp1/2p5/4P2Q/2NP1q2/PPP2P2/2KR3R_b_-_-_3_20)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_11` (Sprandel27 vs fdsakjhg, jogador de white)

- Lance jogado: `c4b3`  |  melhor lance: `c3a4`  |  perda: **60 cp**
- FEN: `2k4r/1b1pnR1p/1pn5/2q2p2/2B2P2/2N5/PPP1N1P1/2K4R w - - 1 26`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2k4r/1b1pnR1p/1pn5/2q2p2/2B2P2/2N5/PPP1N1P1/2K4R_w_-_-_1_26)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_17` (pddddddzzzzzyyyy vs Sprandel27, jogador de black)

- Lance jogado: `b4c6`  |  melhor lance: `c8c3`  |  perda: **64 cp**
- FEN: `2rqk2r/5pp1/p2bpnp1/1p1p2B1/1n1P2P1/P1N2Q1P/1PP1BP2/2KR3R b k - 0 16`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/2rqk2r/5pp1/p2bpnp1/1p1p2B1/1n1P2P1/P1N2Q1P/1PP1BP2/2KR3R_b_k_-_0_16)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 6** — partida `game_30` (Sprandel27 vs samyceram, jogador de white)

- Lance jogado: `h6f5`  |  melhor lance: `h6f7`  |  perda: **312 cp**
- FEN: `r2q1r1k/pp1n1pbp/2p3nN/P2p4/3Pp1Q1/1P2B3/4N1PP/R4RK1 w - - 8 24`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r2q1r1k/pp1n1pbp/2p3nN/P2p4/3Pp1Q1/1P2B3/4N1PP/R4RK1_w_-_-_8_24)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

### Peão Atrasado  (`backward_pawn`)

- **Referência Silman:** cap. 5, p. 109 — categoria *estrutura de peões*
- **Conceito:** Peão que não pode avançar com segurança porque a casa à sua frente é controlada por um peão adversário, e não tem apoio de peões aliados por trás nas colunas adjacentes.
- **Implicação estratégica:** Peão atrasado é fraqueza estrutural permanente: preso na coluna semi-aberta, torna-se alvo de pressão de torres. O adversário deve dobrar torres nessa coluna; o jogador deve buscar avançar o peão quando possível ou trocá-lo para eliminar a fraqueza.
- **Detecções no perfil:** 5 erros em 262 ocorrências (2%), magnitude média 229 cp

_Lances-erro detectados (5):_

**Exemplo 1** — partida `game_8` (Sbdxhchsbsb vs Sprandel27, jogador de black)

- Lance jogado: `b7b6`  |  melhor lance: `d6d5`  |  perda: **97 cp**
- FEN: `r1b2r2/pp3pkp/3ppqp1/2p5/4P2P/2NPQP2/PPP2P2/R3K2R b KQ - 2 15`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r1b2r2/pp3pkp/3ppqp1/2p5/4P2P/2NPQP2/PPP2P2/R3K2R_b_KQ_-_2_15)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 2** — partida `game_14` (Sprandel27 vs farhadbandi, jogador de white)

- Lance jogado: `f2f4`  |  melhor lance: `d2f3`  |  perda: **301 cp**
- FEN: `r5k1/pp1b1rb1/n3p1p1/2ppPnBp/3P3P/2P5/PPBN1PQ1/R3K2R w KQ - 2 21`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/r5k1/pp1b1rb1/n3p1p1/2ppPnBp/3P3P/2P5/PPBN1PQ1/R3K2R_w_KQ_-_2_21)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 3** — partida `game_23` (Sprandel27 vs akdjan_n, jogador de white)

- Lance jogado: `f4e2`  |  melhor lance: `g3g4`  |  perda: **262 cp**
- FEN: `8/1p6/5k2/2PK1p2/4nN1P/6P1/8/8 w - - 6 41`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/1p6/5k2/2PK1p2/4nN1P/6P1/8/8_w_-_-_6_41)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 4** — partida `game_23` (Sprandel27 vs akdjan_n, jogador de white)

- Lance jogado: `f4h5`  |  melhor lance: `g3g4`  |  perda: **419 cp**
- FEN: `8/1p6/5k2/2PK1p2/4nN1P/6P1/8/8 w - - 10 43`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/8/1p6/5k2/2PK1p2/4nN1P/6P1/8/8_w_-_-_10_43)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_

**Exemplo 5** — partida `game_30` (Sprandel27 vs samyceram, jogador de white)

- Lance jogado: `f2f4`  |  melhor lance: `g1f3`  |  perda: **64 cp**
- FEN: `rnbqkbnr/pp3ppp/2ppp3/8/2PPP3/8/PP3PPP/RNBQKBNR w KQkq - 0 4`
- Tabuleiro: [abrir no Lichess](https://lichess.org/analysis/rnbqkbnr/pp3ppp/2ppp3/8/2PPP3/8/PP3PPP/RNBQKBNR_w_KQkq_-_0_4)
- **Avaliação qualitativa:** _( ) detecção coerente com Silman   ( ) falso positivo   — justificativa:_


---
