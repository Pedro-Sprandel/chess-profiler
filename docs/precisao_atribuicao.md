# Precisão e cobertura da atribuição erro → conceito

Este documento registra a revisão da etapa que liga cada erro confirmado pelo Stockfish
a um conceito de Silman (`modules/attribution.py`), a medição feita antes e depois e o
classificador LLM para os erros que as regras não explicam (`modules/error_classifier.py`).

## Motivação

A validação qualitativa (`qualitative_analysis.md`) estimou cerca de 70% de atribuições
coerentes. Os falsos positivos tinham uma assinatura única: o melhor lance era forçante
(xeque, captura com xeque) e o erro "vazava" para conceitos estruturais
(`space_advantage`, `weak_square`, `backward_pawn`, `pawn_majority`) por co-ocorrência.
A mesma análise recomendava estender o filtro tático aos lances forçantes.

Além disso, cerca de 70–77% dos erros confirmados não recebiam conceito nenhum (244 erros
e 70 atribuídos para diogenesdie; 257/75 para sprandel1; 166/38 para Sprandel27), e um
mesmo erro podia ser creditado a até três conceitos.

## O que mudou

1. **Linhas do engine.** O validador guarda a linha principal a partir da posição (6
   meios-lances) e a refutação do lance jogado (melhor resposta do adversário e
   continuação). Ficam no cache SQLite (`fen_cache.pv`).
2. **Camada tática determinística**, com precedência sobre os conceitos estratégicos:
   - `missed_tactic`: o melhor lance é captura vantajosa (SEE) **ou** a linha principal
     ganha ≥ 200 cp de material em poucos lances (garfos, cravadas, descobertas);
   - `hanging_piece`: peça do jogador pendurada e o melhor lance a salva;
   - `allowed_tactic` (novo conceito, "Tática Permitida"): a refutação do lance jogado
     ganha ≥ 200 cp para o adversário;
   - `missed_tactic` (motivo "xeque"): o melhor lance é um xeque forçante.
3. **Um conceito por erro.** Entre os conceitos estratégicos que passam em todos os
   filtros, fica o de maior ganho relativo ao seu limiar.
4. **Filtros de vínculo causal** para conceitos estratégicos:
   - xeque como melhor lance não conta para conceito estrutural;
   - captura só conta se for na própria casa do conceito;
   - localidade: o melhor lance sai de, chega a ou ataca as casas que o detector apontou;
   - espaço exige lance de peão (Silman: o espaço vem das cadeias de peões);
   - espaço e controle do centro desligados em finais (material de peças ≤ 20);
   - na dúvida (sem melhor lance, exceção), não atribui.
5. **Cobertura.** Todas as posições passam pelo Stockfish, não só as com conceito
   detectado. Em partidas de tamanho normal, toda posição já tem algum conceito detectado
   (460 de 460 posições num teste com 6 partidas), então o custo extra é desprezível; a
   diferença aparece nos primeiros lances de partidas curtas.
6. **Classificador LLM** para os erros que sobram sem conceito (ver abaixo).

## Medição

Conjunto de referência: `data/gold_attributions.json`, gerado por
`scripts/build_gold_set.py` a partir de `qualitative_dataset.md` (183 posições reais de
erro) e `qualitative_analysis.md` (38 vereditos humanos casados por posição). Avaliação:
`scripts/evaluate_precision.py` (Stockfish depth 16, melhor lance do dataset).

| Métrica (38 vereditos) | Antes (`ea61a7e`) | Depois |
|---|---|---|
| Coerentes mantidos | 18/18 | 18/18 |
| Falsos positivos ainda atribuídos | 5/8 | 0/8 |
| Parciais mantidos | 10/12 | 4/12 |
| Precisão das atribuições mantidas (parcial = ½) | 70% (33) | 91% (22) |
| Posições com 2+ conceitos (de 183) | 21 | 0 |
| Posições sem conceito (de 183) | 9 | 19 |

Os parciais que mudaram foram, em sua maioria, para rótulos táticos, o que concorda com
as notas humanas ("tempero tático", "erro misto", "magnitude sugere componente tático").

**Ablação** (mesmo conjunto):

| Variante | Coerentes | FP removidos | Sem conceito |
|---|---|---|---|
| Final | 18/18 | 8/8 | 19 |
| Linha tática ≥ 100 cp | 15/18 | 8/8 | 17 |
| Linha tática ≥ 300 cp | 18/18 | 8/8 | 20 |
| Sem filtro de fase do jogo | 18/18 | 8/8 | 19 |
| Com filtro de persistência na linha | 18/18 | 8/8 | 27 |

O filtro de persistência (exigir que o ganho estrutural continue no fim das linhas do
engine) foi **descartado**: não removeu nenhum falso positivo julgado e derrubou oito
atribuições que, inspecionadas, são rupturas de peão legítimas (d3–d4 libertando o peão
atrasado, g3–g4, e5), porque as trocas seguintes na linha mudam a estrutura de novo.

## Limitações desta medição

- **Não é um teste independente.** A assinatura de falha usada para desenhar os filtros
  veio da mesma análise qualitativa que fornece os vereditos. Os limiares não foram
  ajustados posição a posição, mas a generalização só fica demonstrada com uma nova
  rodada de rotulagem humana em partidas que não participaram do desenho.
- **Revocação dos conceitos estratégicos.** A distribuição mudou bastante (créditos de
  `king_safety` 35 → 19, `space_advantage` 16 → 1, `open_file` 18 → 8). Dos 16 erros que
  saíram de `king_safety`, 6 viraram tática permitida, 4 peça pendurada, 2 tática perdida
  e 4 ficaram sem conceito; a maioria são lances de rei em finais ou erros que perdem
  material, mas há casos mistos (melhor lance = levar o rei a salvo, lance jogado entrega
  material) em que a precedência tática é discutível. Nenhum deles tem veredito humano;
  são os primeiros candidatos à próxima rodada de rotulagem.
- A amostra julgada é pequena (38 vereditos).

## Classificador LLM (erros sem conceito)

O LLM não lê o tabuleiro: recebe uma ficha calculada por erro (lances em SAN, linhas do
engine em SAN, material ganho/perdido ao longo delas, peças penduradas dos dois lados,
conceitos detectados e quanto o melhor lance melhora cada um) e escolhe numa lista
fechada (os 19 conceitos ou `none`). Só rótulos de confiança alta/média são aceitos; a
atribuição fica marcada como `llm`, com justificativa curta, e a interface mostra
"inferido pela IA". O diagnóstico é instruído a tratar essa evidência como mais fraca.

Custo (estimado a partir do tamanho real das fichas: ~1.100 caracteres/erro e ~4.400 no
catálogo fixo; preços de `claude-opus-4-6`, US$5 / US$25 por milhão de tokens):

- teto de 60 erros por análise (`LLM_CLASSIFY_MAX_ERRORS`), maiores perdas primeiro;
- 3 lotes de 20 → ~26 mil tokens de entrada e ~4 mil de saída ≈ **US$0,25 por análise no
  teto**; menos quando há poucos erros sem conceito;
- cache por posição/lance/versão do prompt: re-análises não pagam de novo;
- em contrapartida, o prompt do diagnóstico passou a levar só as 8 posições de maior
  perda por fraqueza (antes, todas), o que compensa boa parte do custo novo.

Desligue com `LLM_CLASSIFY_ERRORS=0`; troque o modelo com `ANTHROPIC_CLASSIFIER_MODEL`.
A precisão do classificador ainda não foi medida com a API real; o próximo passo é rodá-lo
também nos erros que as regras já classificam e medir a concordância (kappa de Cohen).
