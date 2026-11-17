# Anti-Exemplos

## Roteamento de base
| ❌ Errado | ✅ Correto |
|---|---|
| Pergunta genérica com dia específico → `setram_sgr` | → `setram_sbe` (um arquivo diário não implica SGR) |
| Usar `setram_sgr` sem termo de gratuidade | Usar SGR **somente** com idoso/estudante/PCD/gratuidade |
| Assumir colunas da SGR (`Descrição da Aplicação`) em SBE/SBU | Usar os nomes conhecidos (ver `03`) ou, se desconhecidos, `preview` |

## file_filter
| ❌ | ✅ |
|---|---|
| `2025_08`, `2025_08_15`, `YYYY_MM` | `consolidado_2025_08`, `publico_2025_08_15` |

## Colunas e filtros
| ❌ | ✅ |
|---|---|
| `coluna="Col1,Col2"` | Uma coluna por chamada |
| `valor="ONIBUS"` | `"ÔNIBUS"` (valor exato) |
| `valor="Estudante"` no diário | 4 códigos (6001, 6004, 6013, 6007) somados |
| `"Estudante"` em uma única chamada | 4 chamadas + soma |
| Turno via `coluna` ou `Data do Processamento` | `contar_por_turno` sobre `Data da Transação` |
| 00:00 tratado como madrugada | 00:00 = noite (turno 3); madrugada começa 00:01 |

## Operações
| Pergunta | ❌ | ✅ |
|---|---|---|
| "Quantos estudantes?" (consolidado) | `contar_por_valor` | `agrupar_e_somar` com `Tipo de Gratuidade=Estudante` |
| "Quantas linhas tiveram movimento?" | `contar_linhas` | `agrupar_valores_unicos` com `coluna="Linha"` |
| Duas dimensões no diário | Confiar no `preview` | Filtros `agrupar_e_somar` sequenciais |

## Cache e verificação
- ❌ Chamar `gerenciar_cache_sessao`/`baixar_arquivo_dados` por rotina antes de analisar (a análise já consulta o cache e baixa).
- ❌ Concluir que não há dados sem `listar_recursos_da_base`.
- ❌ Ler só a primeira página. ✅ Seguir enquanto `tem_proxima_pagina=true`.

## Respostas
- ❌ "Não encontrei dados" sem chamar ferramentas. ✅ "Busquei com X=Y e não houve registros."
- ❌ Números de memória. ✅ Citar a fonte (base, tipo de arquivo, período).
- ❌ Repetir sugestões já feitas. ✅ Oferecer próximos passos novos.
