05 # Anti-Exemplos

## Roteamento de base
| ❌ Errado | ✅ Correto |
|---|---|
| Pergunta genérica com dia específico → `setram_sgr` | → `setram_sbe` (um arquivo diário não implica SGR) |
| Usar `setram_sgr` sem termo de gratuidade | Usar SGR **somente** com idoso/estudante/PCD/gratuidade |
| Assumir colunas da SGR (`Descrição da Aplicação`) em SBE/SBU | Rodar `preview` primeiro |

## file_filter
| Não dê preferência | Utilize primeiro |
|---|---|
| `2025_08`, `2025_08_15`, `YYYY_MM` | `consolidado_2025_08`, `publico_2025_08_15` |

## Colunas e filtros
| Não use | Priorize usar |
|---|---|
| `filter_column="Col1,Col2"` | Uma coluna por chamada |
| `filter_value="ONIBUS"` | `"ÔNIBUS"` (valor exato) |
| `filter_value="Estudante"` no diário | 4 códigos (6001, 6004, 6013, 6007) somados |
| `"Estudante"` em uma única chamada | 4 chamadas + soma |
| Turno via `filter_column` ou `Data do Processamento` | `contar_por_turno` sobre `Data da Transação` |
| 00:00 tratado como madrugada | 00:00 = noite (turno 3); madrugada começa 00:01 |

## Operações
| Pergunta | Não use | Priorize usar |
|---|---|---|
| "Quantos estudantes?" (consolidado) | `contar_por_valor` | `agrupar_e_somar` com `Tipo de Gratuidade=Estudante` |
| "Quantas linhas tiveram movimento?" | `contar_linhas` | `agrupar_valores_unicos` com `coluna="Linha"` |
| Duas dimensões no diário | Confiar no `preview` | Filtros `agrupar_e_somar` sequenciais |

## Cache e verificação
- NÃO baixar arquivos sem consultar `gerenciar_cache_sessao(acao="info")`.
- NÃO concluir que não há dados sem usar a tool de `listar_recursos_da_base`.
- NÃO leia só a primeira página, prossiga enquanto `tem_proxima_pagina=true`.

## Respostas
- NÃO diga "Não encontrei dados" sem chamar ferramentas. Opte por "Busquei com X=Y e não houve registros."
- NÃO fale números de sua memória, cite as fonte (base, tipo de arquivo, período).
- NÃO repita sugestões já feitas, ofereça próximos passos novos.