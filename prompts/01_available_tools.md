# Ferramentas Disponíveis

## Visão Geral

| Ferramenta | Quando usar | Pré-requisito |
|---|---|---|
| `listar_bases` | Descobrir quais bases existem | - |
| `buscar_infos_base` | Encontrar base por nome | - |
| `listar_recursos_da_base` | Ver arquivos disponíveis numa base | - |
| `baixar_arquivo_dados` | Baixar arquivo para análise | - |
| `analisar_dados_arquivo` | Fazer cálculos sobre dados baixados | `baixar_arquivo_dados` |
| `gerar_graficos` | Criar gráfico (só se pedir) | `baixar_arquivo_dados` |
| `gerenciar_cache_sessao` | Listar/limpar cache | - |

---

## Parâmetros Críticos

### baixar_arquivo_dados

**Parâmetros obrigatórios:**
- `package_id`: ID da base
- `file_filter`: DEVE seguir estas regras:

| Tipo de pergunta | file_filter |
|---|---|
| Mês inteiro (sem dia) | `consolidado_YYYY_MM` |
| Dia específico | `publico_YYYY_MM_DD` |
| Vários meses | chamar 1x por mês |

---

### analisar_dados_arquivo - Operações

| Operação | Quando usar | Parâmetros extras |
|---|---|---|
| `contar_linhas` | "Quantas linhas tem?" | - |
| `mostrar_colunas` | "Que colunas tem?" | - |
| `preview` | "Mostra as primeiras linhas" | - |
| `agrupar_e_somar` | "Qual o total de X?" | `filter_column`, `filter_value`, `sum_column` |
| `contar_por_valor` | "Quantas linhas têm valor X?" | `column`, `value` |
| `filtrar_por_turno` | "Quantos de manhã?" | `turno`, `filter_column`, `filter_value` |
| `contar_por_turno` | "Qual turno teve mais?" | `filter_column`, `filter_value` |

**Turnos:**
- 0 = Manhã (06:00 - 11:59)
- 1 = Tarde (12:00 - 17:59)
- 2 = Noite (18:00 - 23:59)
- 3 = Madrugada (00:00 - 05:59)

---

### gerar_graficos

**Tipos:** barras, comparacao, linhas, pizza

**Parâmetros:** tipo_grafico, arquivos, coluna_categoria, coluna_valor

---

### gerenciar_cache_sessao

**Ações:** listar, info, limpar