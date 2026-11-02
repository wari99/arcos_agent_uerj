# Mapeamento de Sinônimos

---

## Bases de Dados
| Sinônimos | Base | package_id |
|---|---|---|
| gratuidade, idoso, estudante, PCD, transação gratuita, passagem grátis | SETRAM-SGR | `setram_sgr` |
| bilhete único, BU, integração, cartão BU | SETRAM-SBU | `setram_sbu` |
| bilhetagem, validação, embarque, passageiro, movimento de transporte | SETRAM-SBE | `setram_sbe` |
| tarifa, preço, passagem do metrô, MetrôRio | Concessionária MetrôRio | `concessionaria-metrorio` |
| tarifa, preço, passagem da barca, CCR Barcas | Concessionária CCR Barcas | `concessionaria-ccr-barcas` |
| tarifa, preço, passagem do trem, supervia, SuperVia | Concessionária SuperVia | `concessionaria-supervia` |

---

## Modais de Transporte
| Sinônimos | Modal | Valor em datasets |
|---|---|---|
| ônibus, onibus, busão, bus, coletivo, intermunicipal | Ônibus | `ÔNIBUS` |
| metrô, metro, estação de metrô, linha de metro | Metrô | `METRÔ` |
| trem, trens, supervia, estação de trem, linha de trem | Trens | `TRENS` |
| barca, barcas, travessia aquaviária | Barcas | `BARCAS` |
| van, vans, perua, kombi, transporte alternativo | Vans | `VANS` |

---

## Tipos de Gratuidade
| Sinônimos | Tipo | Valor no Consolidado | Código no Diário |
|---|---|---|---|
| idoso, coroa, senior, terceira idade | Idoso | `Idoso` | `7001 - Idoso` |
| estudante, aluno, brisolão, CIEP, escolar | Estudante | `Estudante` | ⚠️ 4 códigos (veja 03_specific_databases.md) |
| deficiente, PCD, pessoa com deficiência, portador de necessidades especiais | Deficiente | `Deficiente Físico` | `7002 - Deficiente Físico` |

---

## Operações e Análises
| Sinônimos do Usuário | Operação correta | Referência |
|---|---|---|
| quantos, total, soma, quanto, quantidades | `agrupar_e_somar` | `01_available_tools.md` |
| quantas linhas, quantas vezes, ocorrências, contagem | `contar_por_valor` ou `agrupar_valores_unicos` | `01_available_tools.md` |
| de manhã, pela manhã, turno da manhã, café da manhã | `contar_por_turno` com turno=1 | `03_specific_databases.md` |
| à tarde, turno da tarde, período da tarde | `contar_por_turno` com turno=2 | `03_specific_databases.md` |
| à noite, turno da noite, período noturno | `contar_por_turno` com turno=3 | `03_specific_databases.md` |
| madrugada, de madrugada, noite de madrugada | `contar_por_turno` com turno=0 | `03_specific_databases.md` |
| gráfico, visualizar, mostra, chart, plotar | `gerar_graficos` | `01_available_tools.md` |
| comparar, vs, versus, diferença, qual foi maior | `gerar_graficos` com tipo="comparacao" | `01_available_tools.md` |
| ranking, top, mais, menos, qual é o maior | `agrupar_valores_unicos` | `03_specific_databases.md` |
| amostra, preview, mostra um pouco, como é o dado | `preview` | `01_available_tools.md` |
| que colunas tem, quais campos, estrutura do dado | `preview` | `01_available_tools.md` |

---

## Padrões de Linhas — Referência Rápida

⚠️ **Para padrões COMPLETOS de linhas (ônibus, metrô, trem) e estratégias de busca, consulte `03_specific_databases.md` seção "Padrões de Linhas".**

| Modal | Padrão | Exemplo | Busca por |
|---|---|---|---|
| **ÔNIBUS** | `<ID> - <TERMINAL_1> - <TERMINAL_2>` | `468B - QUEIMADOS - PENHA` | ID ou trajeto |
| **METRÔ** | `L<NUM> <SIGLA> - Estação <NOME> - Metrô` | `L1 CTR - Estação Central - Metrô` | Número ou estação |
| **TRENS** | `R<NUM><SIGLA> - <NOME> - SUPERVIA` | `R3ATA - ESTACAO ANCHIETA - SUPERVIA` | Número ou estação |

---

## Períodos Temporais
| Expressão | Significado | Inferência |
|---|---|---|
| "esse ano", "este ano" | Ano atual | Use `get_current_date()` |
| "ano passado" | Ano anterior ao atual | Use `get_current_date()` |
| "este mês", "mês atual" | Mês atual | Use `get_current_date()` |
| "mês passado" | Mês anterior ao atual | Use `get_current_date()` |
| "semana passada" | 7 dias atrás | Use `get_current_date()` |
| "ontem", "dia anterior" | Dia anterior ao atual | Use `get_current_date()` |
| "em agosto", "no mês de agosto" | Mês específico (ano deve ser inferido) | Usar regra de `08_datetime_inference.md` |
| "dia 15 de julho" | Dia específico | Usar regra de `08_datetime_inference.md` |

**CRÍTICO**: SEMPRE que o usuário citar um período de tempo de agrupamento, você **DEVE** acionar a **get_current_date()**.

---

## Tipos de Arquivo
| Expressão | Tipo | file_filter |
|---|---|---|
| "mensal", "mês todo", "agregado" | Consolidado | `consolidado_YYYY_MM` |
| "diário", "dia específico", "detalhado" | Público (diário) | `publico_YYYY_MM_DD` |
| "sem especificar período" | PADRÃO: Consolidado | `consolidado_YYYY_MM` |

---

## Contexto Persistente
| Situação | Ação |
|---|---|
| Pergunta anterior foi sobre SGR, nova pergunta sem base → | **MANTENHA** SGR |
| Pergunta anterior foi sobre SBU, nova pergunta sem base → | **MANTENHA** SBU |
| Pergunta anterior foi sobre SBE, nova pergunta sem base → | **MANTENHA** SBE |
| Primeira pergunta ou contexto ambíguo → | Use regra hierárquica (veja 03_specific_databases.md) |