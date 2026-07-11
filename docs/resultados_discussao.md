# Resultados e Discussão

Este capítulo apresenta e discute os resultados obtidos com o Chess Strategic Profiler.
A avaliação é feita em duas frentes complementares, correspondentes aos dois objetivos do
trabalho: a **viabilidade técnica** da arquitetura híbrida de três camadas (detecção
determinística, validação quantitativa e raciocínio causal) e a **viabilidade pedagógica**
do diagnóstico produzido, isto é, sua utilidade como instrumento de estudo orientado pelos
conceitos de *The Amateur's Mind* (Silman). A discussão é sustentada por dados reais de três
jogadores do Chess.com em faixas de rating distintas e por exemplos concretos extraídos das
posições analisadas, e é ilustrada por capturas de tela da interface Streamlit.

A metodologia de validação combina duas leituras. A leitura **quantitativa** mede taxa de
erro, distribuição de fraquezas e magnitude média dos erros em centipawns. A leitura
**qualitativa** inspeciona uma amostra representativa de posições (cerca de dois exemplos por
conceito, cobrindo sucessos e falhas) e emite um veredito justificado para cada detecção,
cruzando as características objetivas da posição (lance jogado *versus* melhor lance, natureza
do melhor lance e equilíbrio material) com a definição do conceito em Silman.

---

## 1. Resultados quantitativos

O pipeline foi executado sobre três jogadores reais, selecionados para cobrir uma faixa ampla
de força enxadrística (de iniciante a intermediário). A Tabela 1 resume os números agregados.

**Tabela 1 — Síntese quantitativa dos três perfis analisados**

| Jogador | Rating aprox. | Partidas | Posições | Erros | Taxa de erro | Fraquezas |
|---|---|---|---|---|---|---|
| diogenesdie | ~520 (rapid) | 30 | 981 | 244 | 24,9% | 9 |
| sprandel1 | ~1295 (blitz) | 30 | 1.119 | 257 | 23,0% | 9 |
| Sprandel27 | ~1555 (rapid) | 30 | 866 | 166 | 19,2% | 5 |

Três regularidades emergem dos dados e sustentam a validade externa da ferramenta:

1. **A taxa de erro decresce monotonicamente com o rating** (24,9% → 23,0% → 19,2%). O
   sistema, sem qualquer conhecimento prévio do nível dos jogadores, reproduz a ordenação
   esperada por força — um indício de que os erros detectados são reais e não artefatos do
   método.

2. **O número de fraquezas distintas diminui com o nível.** O jogador mais forte concentra
   suas falhas em cinco conceitos; os dois mais fracos espalham-se por nove. Isso é coerente
   com a noção pedagógica de que jogadores mais avançados têm lacunas mais focalizadas.

3. **O perfil tático varia com o nível, mas o eixo de segurança não.** A `missed_tactic`
   (tática perdida) tem peso decrescente em ocorrências absolutas (16 → 24 → 8) enquanto
   `hanging_piece` (peça pendurada) e `king_safety` (segurança do rei) aparecem nos três
   perfis como fraquezas recorrentes — exatamente os conceitos de verificação de segurança
   que Silman situa no capítulo inicial.

> **Figura 1** — Dashboard de perfil (`#profile-dashboard`). Métricas agregadas (partidas,
> posições, taxa de erro) e cartão de fraquezas do jogador diogenesdie.
> *[Inserir captura da página "Profile" da interface Streamlit, com o seletor de perfil em
> `diogenesdie_profile.json`.]*

A Figura 2 detalha a distribuição de erros por conceito. Um traço metodológico importante é
visível no gráfico: a `missed_tactic` exibe taxa de erro de 100% porque, por construção, só é
registrada quando há erro — ela não acumula ocorrências de posições corretas, ao contrário dos
conceitos estruturais, cujas taxas ficam entre 1% e 8%. Essa assimetria não é um defeito, e sim
o efeito do *gate* de precedência tática, discutido na seção seguinte.

> **Figura 2** — Gráfico de fraquezas por conceito (`weakness_chart`). Erros absolutos e taxa
> de erro por conceito Silman.
> *[Inserir captura do gráfico Plotly da seção "Profile" para o perfil sprandel1, em que
> `missed_tactic` lidera com 24 erros.]*

---

## 2. Viabilidade técnica: a camada de detecção

A questão técnica central é: **as detecções correspondem de fato ao conceito estratégico que
nomeiam, ou são meras co-ocorrências?** A inspeção qualitativa da amostra revela um padrão
nítido e consistente nos três perfis, que separa claramente os acertos das falhas do pipeline.

### 2.1 Sucessos: conceitos com *gate* próprio

Os conceitos que possuem um *gate* de precedência — um filtro que decide, **antes** de testar
os demais conceitos, se o erro pertence àquele conceito — acertam quase sempre. `missed_tactic`,
`hanging_piece` e `king_safety` foram coerentes em todos os exemplos analisados. A assinatura do
acerto é direta: o melhor lance indicado pelo Stockfish é, respectivamente, a captura ganhadora
recusada, a defesa/realocação da peça atacada, e o roque ou a proteção do rei exposto.

**Exemplos comentados (sucessos):**

| Perfil | Conceito | Posição | Jogou → melhor | Leitura |
|---|---|---|---|---|
| sprandel1 | `hanging_piece` | g2 (162cp) | `c6` → **`Nc6`** | O peão e5 estava pendurado ao bispo de fianchetto em b2; o melhor lance defende e5. Caso de livro: o jogador ignorou a própria peça sob ataque. |
| Sprandel27 | `king_safety` | g7 (176cp) | `Nc6` → **`O-O`** | Rei em e8 exposto; o melhor lance é simplesmente rocar. Exemplo didático ideal de segurança do rei. |
| Sprandel27 | `backward_pawn` | g8 (97cp) | `b6` → **`d5`** | Peão atrasado em d6; o melhor lance avança o próprio peão atrasado para liberá-lo — o recurso estrutural exato que o conceito prescreve. |
| diogenesdie | `missed_tactic` | g3 (313cp) | `Be7` → **`Qxg5`** | O melhor lance captura um cavalo indefeso em g5. Tática material recusada, corretamente isolada dos conceitos estratégicos pelo *gate*. |

Estes casos comprovam o pilar metodológico do projeto: o gate `is_missed_tactic()` impede que
um erro tático (uma captura ganhadora recusada) "vaze" para um conceito estratégico como
`weak_square` por co-ocorrência estrutural. A separação entre **falha de visão tática** e
**incompreensão estratégica** funciona como projetado.

### 2.2 Falhas: vazamento dos conceitos estruturais

As falhas têm todas a mesma origem e a mesma assinatura. O *gate* de precedência tática só
intercepta capturas que ganham material. Quando o melhor lance é um **xeque forçante**
(p.ex. `Qe4+`, `Qc8+`) ou uma **captura com xeque** que não é estritamente "material grátis"
(p.ex. `Rxd5+`, `Bxf2+`, `dxc6+`), o erro é tático, mas escapa do *gate*; então os conceitos
estritamente estruturais — `space_advantage`, `weak_square`, `backward_pawn`, `pawn_majority`,
`piece_activity` — o capturam por co-ocorrência.

**Exemplos comentados (falsos positivos):**

| Perfil | Conceito | Posição | Jogou → melhor | Leitura |
|---|---|---|---|---|
| diogenesdie | `space_advantage` | g3 (220cp) | `e5` → **`Qe4+`** | O melhor lance é um xeque de dama, não uma jogada de espaço. Erro tático rotulado como ganho de espaço. |
| diogenesdie | `pawn_majority` | g15 (577cp) | `Rg2` → **`dxc6+`** | Captura *en passant* com xeque; erro decisivo tático. A maioria de peões é irrelevante na posição. |
| Sprandel27 | `space_advantage` | g4 (855cp) | `Qc3` → **`Kf1`** | Um *blunder* de 855cp (perda de material); o melhor lance é defensivo. Espaço é puro ruído aqui. |

A estimativa qualitativa da amostra é de **cerca de 70% de detecções coerentes e 30% de falsos
positivos ou marginais**, estes últimos concentrados precisamente em `space_advantage`,
`weak_square`, `pawn_majority` e `piece_activity` — os conceitos sem *gate* próprio.

> **Figura 3** — Explorador de partidas (`#game-explorer`). Tabuleiro SVG com seta do lance
> jogado e do melhor lance, permitindo inspeção visual posição a posição.
> *[Inserir captura da página "Explorer" mostrando uma posição de falso positivo, p.ex.
> `e5` → `Qe4+` no perfil diogenesdie, com as duas setas contrastantes.]*

A interface de exploração (Figura 3) foi decisiva para esta análise: ao sobrepor a seta do
lance jogado e a do melhor lance, ela torna imediatamente visível por que um erro é tático e
não estrutural — sempre que a seta do melhor lance aponta para um xeque ou captura forçante,
o rótulo de conceito estrutural é suspeito.

---

## 3. Viabilidade pedagógica: a camada de raciocínio causal

Se a camada determinística produz cerca de 30% de ruído, a pergunta pedagógica é se o
diagnóstico final ainda é útil. **A resposta é afirmativa, e a razão é instrutiva.**

### 3.1 A causa raiz corrige o ruído da camada determinística

Nos três perfis, a causa raiz inferida pelo Claude converge para a **mesma família de
problema** — falha em varrer lances forçantes (xeques, capturas e ameaças) antes de escolher o
lance —, ainda que com formulações específicas para cada jogador:

- **diogenesdie:** *"Falha sistemática na varredura de capturas, ameaças e lances forçantes"*
- **sprandel1:** *"Falha em priorizar lances forçantes concretos sobre planos gerais"*
- **Sprandel27:** *"Falha na avaliação de ameaças pré-lance"*

Todos os três diagnósticos foram emitidos com confiança **HIGH**. O ponto crucial é que esta
causa raiz **acerta o fundo mesmo onde o rótulo por conceito erra**: os próprios falsos
positivos da camada determinística são, no fundo, lances forçantes perdidos rotulados como
estratégia. Ou seja, o erro de rotulação e a causa raiz apontam para o mesmo déficit cognitivo.
A camada de raciocínio causal mostra-se, assim, **mais robusta que a camada de rotulação
determinística** — ela reabsorve como sintoma aquilo que a camada inferior classificou
erroneamente.

Isso é confirmado pela classificação que o LLM atribui a cada fraqueza. Para diogenesdie, por
exemplo, `missed_tactic` e `hanging_piece` são marcados como **PRIMARY**; `king_safety` e
`open_file` como **SECONDARY**; e justamente os conceitos estruturais ruidosos
(`backward_pawn`, `pawn_majority`, `space_advantage`, `weak_square`) como **NOISE**. O LLM
identifica autonomamente como ruído os mesmos conceitos que a análise qualitativa apontou como
falsos positivos.

> **Figura 4** — Relatório de diagnóstico (`#diagnosis-report`). Causa raiz, classificação das
> fraquezas em PRIMARY/SECONDARY/NOISE e padrão cognitivo do jogador.
> *[Inserir captura da página "Diagnosis" para diogenesdie, destacando a causa raiz e a tabela
> de classificação.]*

### 3.2 Recomendações de estudo acionáveis

O plano de estudo gerado é pedagogicamente coerente: nos três perfis ele prioriza
`missed_tactic`, `hanging_piece` e `king_safety` — exatamente os conceitos de detecção mais
confiável e maior impacto — e **não** promove os conceitos estruturais ruidosos. O padrão
cognitivo descrito para diogenesdie ilustra a qualidade do raciocínio:

> *"O jogador opera com um processo de pensamento 'posicional primeiro' [...]. A correção
> requer inverter a ordem de pensamento: PRIMEIRO verificar todos os lances forçantes (xeques,
> capturas, ameaças), DEPOIS avaliar considerações posicionais."*

A recomendação de prioridade 1 traduz isso em uma intervenção concreta — treino diário de
10–15 problemas táticos focado em reconhecimento de padrões — e observa que essa única
intervenção também reduzirá os erros de peça pendurada, conectando dois sintomas a uma causa.
É exatamente o tipo de orientação acionável que justifica o uso do LLM como **componente de
raciocínio** sobre dados quantitativos, e não como gerador de texto pedagógico genérico.

---

## 4. Discussão crítica

**O que funciona.** A arquitetura de três camadas cumpre seu propósito. A detecção
determinística com *gate* tático isola corretamente os erros de visão (tática perdida, peça
pendurada, rei exposto); a validação por Stockfish elimina falsos erros (a correção de
`is_error` quando `move_played == best_move` evita o efeito horizonte); e a camada de raciocínio
causal sintetiza os dados em um diagnóstico coerente, com confiança calibrada e plano de estudo
acionável. O sistema reproduz, sem supervisão, a ordenação por força dos jogadores — evidência
de validade.

**O que falha, e por quê.** O limite técnico é bem delimitado e tem causa única: o *gate* de
precedência tática cobre apenas capturas materiais, deixando os **xeques forçantes** vazarem
para os conceitos estruturais. Isso produz os ~30% de falsos positivos, concentrados em quatro
conceitos sem *gate* próprio. A falha é, portanto, sistemática e previsível — não aleatória — o
que a torna corrigível.

**Recomendação de melhoria.** Estender o *gate* `is_missed_tactic()` para interceptar também
lances forçantes não materiais — melhor lance que dá xeque (`board.gives_check`) ou captura com
xeque, mesmo sem ganho material líquido. Essa mudança pontual eliminaria a maior parte dos
falsos positivos documentados e reforçaria a distinção tática/estratégia que é o pilar do
projeto. É uma direção de trabalho futuro derivada diretamente da análise de falhas, e não uma
conjectura.

**Limitações da avaliação.** A análise qualitativa estima a precisão das detecções a partir
das características das posições e do julgamento enxadrístico, e não de uma revalidação completa
posição a posição com engine em profundidade alta; os casos de fronteira (marcados como
"parcial") dependem mais de julgamento posicional e mereceriam conferência visual no tabuleiro.
Além disso, a amostra de validação cobre três jogadores em uma faixa de rating de ~500 a ~1550;
a generalização para jogadores fortes (>2000), cujos erros são mais sutis e menos táticos,
permanece em aberto.

---

## 5. Síntese

Os resultados sustentam a viabilidade técnica e pedagógica da abordagem proposta. **Tecnicamente**,
a combinação de detecção determinística, validação por engine e *gate* de precedência tática
produz detecções coerentes em cerca de 70% dos casos, com um modo de falha único, sistemático e
corrigível. **Pedagogicamente**, a camada de raciocínio causal entrega diagnósticos de causa
raiz coerentes e com alta confiança nos três perfis, classifica corretamente o ruído da camada
inferior e gera planos de estudo acionáveis e alinhados a Silman — chegando a corrigir, no nível
do diagnóstico, o ruído gerado no nível da rotulação. O achado mais relevante para o TCC é
justamente esse: **a hierarquia de camadas confere robustez**, pois a camada de raciocínio
superior reabsorve como sintoma de uma mesma causa aquilo que a camada determinística inferior
classificou de forma imperfeita. É a demonstração empírica de que o LLM, empregado como
componente de raciocínio sobre dados quantitativos estruturados — e não como produtor autônomo
de texto —, agrega valor real ao diagnóstico.
