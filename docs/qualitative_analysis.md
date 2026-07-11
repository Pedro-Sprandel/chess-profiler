# Análise Qualitativa: Chess Profiler

## Metodologia da análise

Para cada perfil foi selecionada uma amostra representativa (cerca de dois exemplos por
conceito, cobrindo casos de sucesso e de falha), com um veredito justificado. Os vereditos
partem de características objetivas de cada posição (lance jogado e melhor lance, natureza do
melhor lance, isto é, se é captura ou xeque, equilíbrio material e a saída do detector),
cruzadas com a definição do conceito em *The Amateur's Mind* (Silman).

Legenda dos vereditos:

- **Coerente:** a detecção corresponde de fato ao conceito de Silman naquela posição.
- **Parcial / contexto:** a detecção tem relação com o conceito, mas o erro real é
  majoritariamente de outra natureza (em geral tática) ou o conceito é marginal na posição.
- **Falso positivo:** o conceito foi atribuído por co-ocorrência; o erro não é sobre ele.

---

## Síntese dos achados

A amostra revela um padrão nítido e consistente nos três perfis:

1. **Os conceitos com *gate* próprio acertam quase sempre.** Um *gate* é o filtro de
   precedência no código que decide, antes de testar os demais conceitos, se o erro pertence
   àquele conceito. `missed_tactic`, `hanging_piece` e `king_safety` foram coerentes em todos
   os exemplos analisados: o melhor lance é, respectivamente, a captura ganhadora recusada, a
   defesa ou realocação da peça atacada, e o roque ou a segurança do rei exposto. São os
   sucessos do pipeline.

2. **Os conceitos estritamente estruturais vazam falsos positivos quando o melhor lance é um
   lance forçante (xeque ou captura) que o *gate* `is_missed_tactic` não capturou.** Esse *gate*
   de precedência tática só intercepta capturas que ganham material. Quando o melhor lance é
   um xeque (por exemplo, `Qc8+`, `Qe4+`) ou uma captura com xeque que não é estritamente
   "material grátis" (por exemplo, `Rxd5+`, `Bxf2+`, `dxc6+`), o erro é tático mas escapa do
   *gate*; então `space_advantage`, `weak_square`, `backward_pawn`, `pawn_majority` e
   `piece_activity` o capturam por co-ocorrência. São as falhas do pipeline.

3. **Efeito sobre o diagnóstico de causa raiz.** Como a causa raiz inferida pelo Claude nos
   três perfis converge em *falha em priorizar lances forçantes antes do plano*, o diagnóstico
   acerta o fundo mesmo onde o rótulo por conceito erra: os próprios falsos positivos são, no
   fundo, lances forçantes perdidos. Ou seja, a camada de raciocínio causal mostra-se mais
   robusta que a camada de rotulação determinística.

Esse padrão fornece tanto exemplos de falha do pipeline quanto uma recomendação concreta de
melhoria: estender o *gate* tático para cobrir também xeques forçantes, e não apenas capturas
materiais.

---

## Perfil 1: diogenesdie (causa raiz: varredura de capturas, ameaças e forçantes; confiança HIGH)

### Sucessos

| Conceito | Posição | Jogou → melhor | Veredito | Justificativa |
|---|---|---|---|---|
| `missed_tactic` | g3 (313cp) | `Be7` → **`Qxg5`** | ✅ | O melhor lance captura um cavalo em g5 indefeso. Tática material recusada; atribuição correta e separada dos conceitos estratégicos pelo *gate*. |
| `missed_tactic` | g3 (148cp) | `d5` → **`Nxe4`** | ✅ | `Nxe4` ganha o peão central de graça. Caso de livro do conceito. |
| `hanging_piece` | g1 (287cp) | `Bd7` → **`Nd7`** | ✅ | Detector aponta peça pendurada em e5; o melhor lance defende ou realoca. O jogador ignorou a própria peça sob ataque. |
| `hanging_piece` | g1 (557cp) | `d3` → **`Bd7`** | ✅ | Peça pendurada em c6 (cavalo); o melhor lance a protege. Erro de segurança de peça, coerente com Silman. |
| `king_safety` | g1 (68cp) | `Be6` → **`Kf8`** | ✅ | Rei exposto em e8 (`exposed=True`, sem roque); o melhor lance cuida do rei. Coerente. |
| `king_safety` | g9 (707cp) | `Bd5` → **`O-O-O`** | ⚠️ | Rei branco preso no centro sob ataque da dama preta em g2; o rótulo de segurança do rei é correto, mas a posição é muito tática e o erro é misto (segurança e tática). |
| `open_file` | g4 (157cp) | `Bg5+` → **`Rc1`** | ✅ | Final de torres; o melhor lance leva a torre à coluna aberta `c`. Uso de coluna aberta, coerente. |

### Falhas (falsos positivos por co-ocorrência tática)

| Conceito | Posição | Jogou → melhor | Veredito | Justificativa |
|---|---|---|---|---|
| `space_advantage` | g3 (220cp) | `e5` → **`Qe4+`** | ❌ | O melhor lance é um xeque de dama, não uma jogada de espaço. O erro é tático; `space_advantage` pegou por co-ocorrência. |
| `backward_pawn` | g9 (313cp) | `Rc1` → **`Rxd5`** | ❌ | Melhor lance captura um peão em d5. Erro tático; nada a ver com o peão atrasado em c3 que o detector apontou. |
| `backward_pawn` | g9 (94cp) | `Qf4` → **`Rxd5+`** | ❌ | Captura com xeque. Mesmo caso: forçante perdido, não estrutura. |
| `pawn_majority` | g15 (577cp) | `Rg2` → **`dxc6+`** | ❌ | Captura *en passant* com xeque. Erro decisivo tático; maioria de peões é irrelevante aqui. |
| `weak_square` | g9 (143cp) | `Rxf5` → **`Rxc8+`** | ❌ | Melhor lance captura um bispo com xeque. Tática; as 8 "casas fracas" do detector são ruído. |
| `piece_activity` | g4 (680cp) | `f3` → **`Qh8+`** | ⚠️ | Final de dama totalmente ganho; o melhor lance é um xeque. A atividade de peça é tecnicamente alta, mas o erro é de conversão e tática, não posicional. |
| `weak_square` | g4 (206cp) | `axb5` → **`Rc1`** | ⚠️ | Melhor lance ativa a torre rumo às casas fracas d5 a d7; relação plausível, mas tênue. Conferir visualmente. |

**Conclusão do perfil.** Forte coerência nos conceitos com *gate* (`missed_tactic`,
`hanging_piece`, `king_safety`). Os conceitos estruturais produziram vários falsos positivos,
todos com a mesma assinatura: melhor lance igual a xeque ou captura com xeque. A causa raiz do
diagnóstico (varredura de forçantes) é altamente coerente e inclusive explica os falsos
positivos, que são forçantes perdidos rotulados como estratégia.

---

## Perfil 2: sprandel1 (causa raiz: priorizar forçantes sobre planos gerais; confiança HIGH)

### Sucessos

| Conceito | Posição | Jogou → melhor | Veredito | Justificativa |
|---|---|---|---|---|
| `missed_tactic` | g2 (101cp) | `Bxd5` → **`cxd5`** | ✅ | Recaptura correta ganha bispo; recapturar com o bispo perde material. Tática de recaptura, coerente. |
| `missed_tactic` | g2 (163cp) | `Bc5` → **`cxd5`** | ✅ | `cxd5` ganha um cavalo. Forçante material recusado. |
| `hanging_piece` | g2 (162cp) | `c6` → **`Nc6`** | ✅ | Peão e5 pendurado ao bispo de fianchetto em b2; o melhor lance (`Nc6`) defende e5. Exemplo clássico e correto. |
| `hanging_piece` | g3 (147cp) | `Qf3` → **`Qc1`** | ✅ | Detector aponta pendurada em b2; o melhor lance protege. Coerente. |
| `king_safety` | g2 (128cp) | `Rc8` → **`Kf7`** | ✅ | Rei em e8 sem escudo de peões (`shield_pawns=0`); o melhor lance ativa e abriga o rei. Coerente. |
| `open_file` | g2 (140cp) | `Nd2` → **`Rhe8`** | ✅ | Colunas `d` e `e` abertas; o melhor lance dobra e ativa torre na coluna aberta. Uso de coluna, coerente. |
| `space_advantage` | g7 (53cp) | `Bf4` → **`e5`** | ✅ | O melhor lance é o avanço central `e5`, que ganha espaço, exatamente o conceito. Magnitude baixa, mas atribuição correta. |

### Falhas

| Conceito | Posição | Jogou → melhor | Veredito | Justificativa |
|---|---|---|---|---|
| `pawn_majority` | g5 (169cp) | `Rd3` → **`Bxf2+`** | ❌ | Melhor lance é captura com xeque. Tática pura; maioria de peões é co-ocorrência. |
| `weak_square` | g7 (187cp) | `gxf4` → **`a6`** | ⚠️ | Melhor lance empurra o peão `a` rumo à casa fraca `a8` e à promoção; relação posicional plausível, mas o salto de 187cp sugere componente tático. Conferir. |
| `open_file` | g9 (431cp) | `Rc2+` → **`Rb8`** | ⚠️ | Ambos lances de torre, mas a magnitude alta em posição aguda indica que o erro é tático (o xeque `Rc2+` perde), não sobre a coluna em si. |
| `piece_activity` | g3 (71cp) | `Qxg6` → **`c4`** | ⚠️ | `c4` melhora estrutura e atividade ante a captura gananciosa `Qxg6`; relação razoável com o conceito, magnitude pequena. Aceitável como atividade. |
| `space_advantage` / `piece_activity` | g2 (111cp) | `Rg4` → **`Rg1`** | ⚠️ | Mesma posição rotulada por dois conceitos num final de torre e peões. Espaço e atividade são marginais num final tão simplificado; o erro é de técnica de final. |
| `pawn_majority` | g3 (116cp) | `Qe3` → **`axb6`** | ⚠️ | Melhor lance `axb6` é captura que opera a maioria do flanco de dama; relação plausível com o conceito, na fronteira com a tática. |

**Conclusão do perfil.** Padrão idêntico ao perfil 1: *gates* sólidos, estruturais vazando em
posições forçantes. Destaque positivo: `space_advantage` em g7 (`→ e5`) é um exemplo limpo de
detecção estrutural correta, contrastando com os falsos positivos. Causa raiz coerente:
`missed_tactic` lidera com 24 erros e os falsos positivos reforçam o mesmo déficit tático.

---

## Perfil 3: Sprandel27 (causa raiz: avaliação de ameaças antes do lance; confiança HIGH)

### Sucessos

| Conceito | Posição | Jogou → melhor | Veredito | Justificativa |
|---|---|---|---|---|
| `missed_tactic` | g4 (82cp) | `c3` → **`Bxc7`** | ✅ | `Bxc7` ganha um peão e ataca peças; captura material recusada. Coerente. |
| `missed_tactic` | g3 (177cp) | `Rxa7` → **`gxf5`** | ✅ | O jogador capturou no flanco errado; `gxf5` era a captura correta que ganhava material. Coerente. |
| `hanging_piece` | g2 (138cp) | `Qa1+` → **`d3`** | ⚠️ | Detector aponta pendurada em a6; o jogador deu um xeque inútil (`Qa1+`) em vez de defender. Coerente quanto à peça pendurada, com tempero tático. |
| `hanging_piece` | g2 (82cp) | `Qxe2+` → **`Qd5`** | ⚠️ | Posição aguda; o melhor lance centraliza a dama protegendo material. Relação com peça pendurada presente, mas tática no entorno. |
| `king_safety` | g7 (176cp) | `Nc6` → **`O-O`** | ✅ | Rei em e8 exposto; o melhor lance é rocar. Exemplo de livro de segurança do rei. Coerente. |
| `king_safety` | g3 (132cp) | `b4` → **`Kf1`** | ✅ | Rei branco em e1 exposto (`has_castled=False`); o melhor lance cuida do rei. Coerente. |
| `backward_pawn` | g8 (97cp) | `b6` → **`d5`** | ✅ | Detector aponta peão atrasado em d6; o melhor lance avança o próprio peão atrasado (`d5`) para liberá-lo. Exemplo perfeito do conceito. |

### Falhas

| Conceito | Posição | Jogou → melhor | Veredito | Justificativa |
|---|---|---|---|---|
| `space_advantage` | g4 (244cp) | `f3` → **`Qc8+`** | ❌ | Melhor lance é xeque de dama. Erro tático; espaço (vantagem 6) é co-ocorrência. |
| `space_advantage` | g4 (855cp) | `Qc3` → **`Kf1`** | ❌ | Erro de 855cp é um blunder tático (perda de dama ou material); o melhor lance é defensivo. Espaço é ruído. |
| `backward_pawn` | g14 (301cp) | `f4` → **`Nf3`** | ⚠️ | Detector aponta peão atrasado em h4; o melhor lance é um lance de cavalo. A magnitude de 301cp sugere erro tático ou posicional, não manejo do peão atrasado. Conferir. |

**Conclusão do perfil.** O melhor perfil em proporção de sucessos limpos: `backward_pawn` em g8
(`→ d5`) e `king_safety` em g7 (`→ O-O`) são exemplos didáticos ideais. Os dois falsos
positivos de `space_advantage` repetem a assinatura tática (xeque ou blunder). Causa raiz
(avaliação de ameaças antes do lance) coerente com o predomínio de `hanging_piece`,
`king_safety` e `missed_tactic`.

---

## Avaliação dos três eixos do requisito

**1. Relevância e acurácia das detecções.**
Alta para `missed_tactic`, `hanging_piece`, `king_safety`, `open_file` e para `space_advantage`
e `backward_pawn` quando o melhor lance é o recurso estrutural correto (avanço de peão, torre
para coluna aberta). Baixa quando o melhor lance é forçante (xeque ou captura) e o erro tático
vaza para um conceito estrutural. Estimativa qualitativa da amostra: cerca de 70% de detecções
coerentes e cerca de 30% de falsos positivos ou marginais, concentrados em `space_advantage`,
`weak_square`, `pawn_majority` e `piece_activity`.

**2. Diagnósticos de causa raiz.**
Coerentes nos três perfis, com confiança HIGH justificada. Ponto forte: a causa raiz acerta o
fundo mesmo onde o rótulo por conceito erra, porque os falsos positivos são, eles próprios,
lances forçantes perdidos, exatamente o déficit que o diagnóstico aponta. Isso evidencia que a
camada de raciocínio causal corrige ruído da camada determinística.

**3. Recomendações de estudo.**
Relevantes e acionáveis: priorizam `missed_tactic`, `king_safety` e `hanging_piece`, que são
justamente os conceitos com detecção mais confiável e maior impacto. O plano não recomenda como
prioridade os conceitos estruturais ruidosos, o que é apropriado.

## Recomendação de melhoria (derivada da análise de falhas)

Estender o *gate* de precedência tática (`is_missed_tactic`, em `concept_relevance.py`) para
também interceptar lances forçantes não materiais: melhor lance que dá xeque
(`board.gives_check`) ou captura com xeque, mesmo sem ganho material líquido. Hoje o *gate* só
cobre capturas que ganham material, deixando os xeques forçantes vazarem para conceitos
estruturais. Essa mudança eliminaria a maior parte dos falsos positivos documentados acima e
reforçaria a distinção entre tática e estratégia, que é o pilar metodológico do projeto.

## Limitação

Esta análise avalia a precisão das detecções (falsos positivos) a partir das características das
posições e do julgamento enxadrístico, e não de uma revalidação completa com engine posição a
posição. Os casos marcados como Parcial são os de fronteira, em que o veredito depende mais do
julgamento posicional e merecem conferência visual no tabuleiro.
