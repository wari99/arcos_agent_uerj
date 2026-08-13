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


| Operação | Quando usar | Parâmetros extras | Retorna |
|---|---|---|---|
| `contar_linhas` | "Quantas linhas tem?" | - | Total de linhas e colunas |
| `mostrar_colunas` | "Que colunas tem?" | - | Lista de colunas e tipos |
| `preview` | "Mostra as primeiras linhas" | - | Primeiras 5 linhas |
| `soma` | "Qual o total em todas as colunas numéricas?" | - | Soma de TODAS colunas numéricas |
| `media` | "Qual a média das colunas numéricas?" | - | Média de TODAS colunas numéricas |
| `max` | "Qual o valor máximo?" | - | Máximo de TODAS colunas numéricas |
| `min` | "Qual o valor mínimo?" | - | Mínimo de TODAS colunas numéricas |
| `agrupar_e_somar` | "Qual o total de X filtrando por Y?" | `filter_column`, `filter_value`, `sum_column` | Soma de coluna com filtro |
| `contar_por_valor` | "Quantas linhas têm valor X?" | `column`, `filter_value` | Contagem de linhas com filtro |
| `filtrar_por_turno` | "Quantos de manhã?" | `turno`, `filter_column`, `filter_value` | Dados filtrados por turno |
| `contar_por_turno` | "Qual turno teve mais ...?" | - | Contagem por turno |
| `valores_unicos` | "Quais valores únicos em <coluna>?" | `column` (opcional: `limite`, `offset`) | Lista de valores únicos paginada |
| `agrupar_valores_unicos` | "Quantas ocorrências por valor em <coluna>?" | `column` | Contagem de cada valor único |



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