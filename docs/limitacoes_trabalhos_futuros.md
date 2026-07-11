# Limitações

O Chess Strategic Profiler é um protótipo de pesquisa, e sua avaliação honesta exige delimitar
com precisão o que ele **não** faz e por quê. As limitações abaixo são organizadas pelas três
camadas da arquitetura — detecção determinística, validação por engine e raciocínio causal por
LLM — acrescidas das restrições do processo de validação. Várias delas não são defeitos a
corrigir, e sim fronteiras de escopo deliberadas de um trabalho de conclusão; todas, contudo,
condicionam a interpretação dos resultados.

## 1. Escopo dos detectores

A camada de detecção repousa sobre **17 conceitos estratégicos extraídos manualmente** de *The
Amateur's Mind* (Silman), mais o conceito tático derivado `missed_tactic`. Esse desenho impõe
quatro limites.

**Cobertura conceitual fechada.** O sistema só enxerga o que está codificado. Conceitos
estratégicos relevantes ausentes da base — iniciativa dinâmica, profilaxia, transformação de
vantagens, jogo de coluna semiaberta, sacrifícios posicionais — são invisíveis ao pipeline.
Ampliar a cobertura exige trabalho manual de extração e um novo detector por conceito, o que
não escala automaticamente.

**Detecção estática, por posição isolada.** Cada detector analisa um único tabuleiro com
`python-chess`, sem memória do plano em curso. Conceitos que só fazem sentido como **sequência
de lances** (um ataque de minoria, a manobra de um cavalo até um *outpost* em três lances, um
plano de avanço de peões) são percebidos apenas pelo seu efeito instantâneo, nunca como
estratégia. O sistema diagnostica sintomas posicionais, não a ausência de um plano.

**Vazamento tático nos conceitos sem *gate* próprio.** Como documentado na análise de
resultados, o *gate* de precedência tática (`is_missed_tactic()`) só intercepta capturas que
ganham material. Quando o melhor lance é um **xeque forçante** ou uma **captura com xeque** sem
ganho material líquido, o erro é tático mas escapa do *gate* e é capturado por co-ocorrência por
conceitos estruturais (`space_advantage`, `weak_square`, `pawn_majority`, `piece_activity`).
Isso produz a estimativa de ~30% de falsos positivos concentrados nesses quatro conceitos.

**Artefato estatístico do conceito tático.** Por construção, `missed_tactic` só é registrado
quando há erro; ele não acumula ocorrências de posições corretas. Sua taxa de erro tende a
100%, o que é correto, mas torna a métrica de "taxa de erro" não comparável diretamente entre
esse conceito e os estruturais.

## 2. Dependência de engine

A validação quantitativa depende inteiramente do Stockfish, com as restrições associadas.

**Profundidade fixa e efeito horizonte.** A análise roda em `STOCKFISH_DEPTH = 10`, suficiente
para erros estratégicos mas raso para táticas longas e finais técnicos. Em profundidade fixa,
o melhor lance pode mudar com mais profundidade; o sistema mitiga o caso mais comum forçando
`is_error = False` quando `move_played == best_move`, mas não elimina o efeito horizonte em
posições agudas. O limiar único `ERROR_THRESHOLD_CP = 50` também trata todas as fases do jogo
da mesma forma, embora 50 centipawns pesem de modo diferente na abertura e num final.

**Avaliação posicional, não plano.** O Stockfish entrega uma avaliação numérica e um melhor
lance, não uma explicação do plano correto. Toda a "intenção" estratégica do diagnóstico é
reconstruída indiretamente, cruzando o melhor lance com os detectores — uma inferência, não uma
leitura direta do plano.

**Custo e infraestrutura.** A análise exige um binário local do Stockfish e tempo de CPU
proporcional ao número de posições. O cache SQLite por FEN amortiza reanálises, mas a primeira
passagem sobre dezenas de partidas é custosa, o que limita a escala (centenas, não milhares de
jogadores) e a viabilidade de um serviço em tempo real.

## 3. Limitações do LLM

A camada de raciocínio causal herda as limitações intrínsecas de um modelo de linguagem.

**Não-determinismo.** A mesma entrada pode produzir diagnósticos textualmente distintos entre
execuções. Embora a estrutura (causa raiz, classificação, plano) seja estável, a redação e
ocasionalmente a fronteira PRIMARY/SECONDARY variam, o que dificulta a reprodutibilidade exigida
em contexto acadêmico.

**Dependência de serviço externo e custo.** O diagnóstico requer uma chave de API e uma chamada
de rede à Anthropic, com latência, custo por *token* e indisponibilidade potencial. O sistema
levanta `RuntimeError` sem a chave; não há modo *offline* de diagnóstico.

**Risco residual de alucinação.** A extração robusta de JSON e o uso da base Silman como
referência reduzem, mas não eliminam, a possibilidade de o modelo inferir uma causa raiz
plausível porém não sustentada pelos dados. O sistema não possui um verificador automático que
confronte cada afirmação do diagnóstico com as posições de origem.

**Fidelidade da base de conhecimento.** A base Silman foi extraída manualmente para preservar
fidelidade interpretativa — uma decisão metodológica deliberada —, mas isso a torna uma única
fonte de verdade pedagógica, dependente da leitura de um intérprete e limitada a um único livro.
Toda a moldura conceitual do sistema é a de *The Amateur's Mind*.

## 4. Limitações da validação

**Amostra pequena e estreita.** A validação cobre três jogadores reais numa faixa de rating de
~500 a ~1550. Não há garantia de que o comportamento se generalize para jogadores fortes
(>2000), cujos erros são mais sutis e menos táticos, nem para amostras grandes e diversas.

**Ausência de *ground truth* humano.** A precisão das detecções foi estimada por julgamento
enxadrístico sobre as características das posições, não por anotação independente de um mestre
nem por revalidação posição a posição em profundidade alta. Os casos de fronteira dependem de
inspeção visual.

**Sem evidência de eficácia pedagógica.** O trabalho demonstra que o diagnóstico é *coerente*,
mas não que *melhora o desempenho* de quem o segue. Não houve estudo longitudinal com grupo de
intervenção e controle medindo ganho real de rating ou redução de erros após o plano de estudo.

## 5. Outras restrições de escopo

- **Fases do jogo não modeladas explicitamente.** O pipeline não distingue abertura, meio-jogo
  e final, nem usa o código ECO da abertura para contextualizar erros, embora `fen_fetcher.py`
  já suporte esses filtros (módulo não integrado ao pipeline principal).
- **Análise unilateral por cor.** Cada partida é analisada da perspectiva de uma única cor por
  vez; não há síntese conjunta do comportamento do jogador como brancas e como pretas em um só
  relatório.
- **Interface de pesquisa, não de produto.** A aplicação Streamlit é página única, voltada à
  demonstração, sem autenticação, persistência de usuários ou histórico de progresso.

---

# Trabalhos Futuros

As oportunidades abaixo derivam diretamente das limitações acima e estão organizadas em um
**roadmap de três horizontes**, do refinamento imediato do protótipo até a evolução para um
sistema completo de treinamento. Cada item indica a limitação que endereça.

## Horizonte 1 — Refinamento do protótipo (curto prazo)

**Estender o *gate* de precedência tática.** Intervenção de maior impacto e menor custo: fazer
`is_missed_tactic()` interceptar também lances forçantes não materiais — melhor lance que dá
xeque (`board.gives_check`) ou captura com xeque sem ganho material líquido. Elimina a maior
parte dos ~30% de falsos positivos documentados e reforça a distinção tática/estratégia que é o
pilar metodológico do projeto. *(Endereça 1 e a análise de falhas dos resultados.)*

**Calibrar limiares por fase do jogo.** Substituir o `ERROR_THRESHOLD_CP` único por limiares
sensíveis à fase (abertura, meio-jogo, final), reduzindo falsos erros em finais técnicos e
aumentando a sensibilidade na abertura. *(Endereça 2.)*

**Aprofundamento adaptativo.** Elevar a profundidade do Stockfish seletivamente em posições
táticas ou agudas (onde a avaliação é instável), mantendo a profundidade rasa nas posições
calmas para preservar custo. *(Endereça 2.)*

**Ampliar a base de detectores.** Acrescentar conceitos de alto valor pedagógico ausentes
(iniciativa, profilaxia, coluna semiaberta, par de bispos em finais), cada um com seu detector e
testes de FEN conhecidas, no padrão já estabelecido. *(Endereça 1.)*

## Horizonte 2 — Robustez e validação científica (médio prazo)

**Validação com *ground truth* de especialista.** Construir um conjunto anotado por mestres
(rótulo de conceito e veredito por posição) para medir precisão e *recall* dos detectores de
forma quantitativa, substituindo a estimativa qualitativa atual. *(Endereça 4.)*

**Estudo longitudinal de eficácia pedagógica.** Acompanhar um grupo de jogadores que sigam o
plano de estudo *versus* um grupo de controle, medindo redução de erros e variação de rating ao
longo de semanas — a evidência que falta para sustentar a utilidade pedagógica real.
*(Endereça 4.)*

**Modelagem explícita de fases e aberturas.** Integrar `fen_fetcher.py` e o código ECO ao
pipeline, contextualizando erros por abertura e por fase, e permitindo diagnósticos do tipo "o
jogador erra sistematicamente a transição para o final". *(Endereça 5.)*

**Verificador automático do diagnóstico.** Adicionar uma etapa que confronte cada afirmação do
LLM com as posições de origem (p.ex., conferir que as posições citadas como `missed_tactic` de
fato têm captura ganhadora recusada), reduzindo o risco residual de alucinação. *(Endereça 3.)*

**Cache e camada de diagnóstico reproduzível.** Persistir o diagnóstico com semente/temperatura
controladas e versionamento do *prompt*, de modo que a mesma entrada gere a mesma saída — requisito
de reprodutibilidade acadêmica. *(Endereça 3.)*

## Horizonte 3 — Sistema completo de treinamento (longo prazo)

**Recomendação de exercícios concretos.** Em vez de apenas nomear o conceito a estudar, gerar
ou selecionar problemas táticos e posições de treino direcionados à fraqueza primária do
jogador (p.ex., baterias de garfos e cravadas para um perfil dominado por `missed_tactic`).

**Acompanhamento temporal de progresso.** Reanalisar periodicamente as partidas novas do
jogador, exibindo a evolução de cada fraqueza ao longo do tempo e fechando o ciclo
diagnóstico → estudo → reavaliação. Requer modelo de usuário persistente e histórico.

**Integração com plataformas.** Conectar a Lichess e Chess.com via API para ingestão contínua e
automática de partidas, transformando o protótipo de análise sob demanda em um serviço de
monitoramento permanente.

**Modo treinador interativo.** Usar o LLM em diálogo — explicando uma posição específica,
respondendo "por que este lance é melhor?", conduzindo o jogador pelo raciocínio correto — em
vez de apenas emitir um relatório estático. A camada de raciocínio causal já existente é a base
natural para essa evolução.

**Diversificação da base pedagógica.** Expandir a base de conhecimento para além de *The
Amateur's Mind*, incorporando outras obras de referência (Nimzowitsch, Dvoretsky) com curadoria,
ampliando a moldura conceitual hoje restrita a um único autor.

## Síntese do roadmap

**Tabela — Roadmap de evolução**

| Horizonte | Foco | Itens-chave | Limitação endereçada |
|---|---|---|---|
| 1 — Curto prazo | Refinar o protótipo | *Gate* de xeques forçantes; limiares por fase; aprofundamento adaptativo; novos detectores | Escopo dos detectores; dependência de engine |
| 2 — Médio prazo | Robustez e validação | *Ground truth* de especialista; estudo longitudinal; fases/ECO; verificador de diagnóstico; reprodutibilidade | Validação; LLM |
| 3 — Longo prazo | Sistema completo | Exercícios direcionados; acompanhamento temporal; integração com plataformas; treinador interativo; base multi-autor | Todas — evolução para produto |

O fio condutor do roadmap é claro: o protótipo já demonstra a **viabilidade** da arquitetura
híbrida de três camadas; a evolução para um sistema completo consiste em (i) fechar o modo de
falha conhecido da camada determinística, (ii) substituir a validação qualitativa por evidência
científica, e (iii) transformar o diagnóstico estático em um ciclo contínuo e interativo de
treinamento. Cada passo é incremental e construído sobre a base já validada, o que torna a
trajetória de maturação concreta e de baixo risco técnico.
