# Ferramentas Disponíveis — Referência Completa

---

## Visão Geral

| Ferramenta | Quando usar | Referência |
|---|---|---|
| `get_current_date()` | Obter data/hora atual para inferência temporal | `08_datetime_inference.md` |
| `listar_bases` | Descobrir quais bases existem | - |
| `buscar_infos_base` | Encontrar base por nome/palavra-chave | - |
| `listar_recursos_da_base` | Ver arquivos disponíveis numa base | - |
| `baixar_arquivo_dados` | Baixar arquivo para análise | `02_decision_steps.md` PASSO 5 |
| `analisar_dados_arquivo` | Fazer cálculos sobre dados baixados | Depois de `baixar_arquivo_dados` |
| `gerar_graficos` | Criar gráfico (só se pedir explicitamente) | `07_format_response_and_error_handling.md` |
| `gerenciar_cache_sessao` | Listar/limpar cache da sessão | - |

---

## Parâmetros Críticos

### `get_current_date()`

Sem parâmetros. Retorna data/hora atual.

```python
get_current_date()
# Retorna, por exemplo: "10 de julho de 2026"
```

**Uso obrigatório em:**
- Inferência de datas relativas (veja `08_datetime_inference.md`)
- Cálculo de ano para filtros

---

### `listar_bases()`

Lista todas as bases disponíveis no ARCOS.

**Sem parâmetros obrigatórios.**

```json
{
  "limite": 50,
  "offset": 0
}
```

**Retorna:** Lista de bases com IDs.

---

### `buscar_infos_base(termo_busca)`

Busca base por nome, palavra-chave ou descrição.

**Parâmetros:**
- `termo_busca` (string) — Ex: "gratuidade", "bilhete", "trem"

**Exemplo:**

```json
{
  "termo_busca": "gratuidade"
}
```

**Retorna:** Bases que contêm "gratuidade" no nome/descrição.

---

### `listar_recursos_da_base(package_id, termo_busca?, limite?, offset?)`

Lista arquivos (recursos) disponíveis numa base específica.

**Parâmetros obrigatórios:**
- `package_id` — Ex: `"setram_sgr"`, `"setram_sbe"`

**Parâmetros opcionais:**
- `termo_busca` — Filtrar por padrão de nome (Ex: "2026_07")
- `limite` — Quantos resultados retornar (padrão: 20)
- `offset` — Para paginação (padrão: 0)

**Exemplo:**

```json
{
  "package_id": "setram_sgr",
  "termo_busca": "2026_07",
  "limite": 50
}
```

**Retorna:**
- Lista de arquivos disponíveis
- Campo `total_recursos_na_base` — número total de recursos

---

### `baixar_arquivo_dados(package_id, file_filter)`

Baixa um arquivo da base para análise. Armazena em cache.

**Parâmetros obrigatórios:**
- `package_id` — Ex: `"setram_sgr"`, `"setram_sbe"`
- `file_filter` — **DEVE seguir regras rigorosas** (veja abaixo)

**Regras obrigatórias para `file_filter`:**

| Tipo de pergunta | file_filter | Exemplo |
|---|---|---|
| Mês inteiro (sem dia específico) | `consolidado_YYYY_MM` | `consolidado_2025_08` |
| Dia específico | `publico_YYYY_MM_DD` | `publico_2025_08_15` |
| Múltiplos meses | Chamar 1x por mês | 2 chamadas |

⚠️ **NUNCA** use `"2025_08"` (genérico) — **SEMPRE** use prefixo!

**Exemplo correto:**

```json
{
  "package_id": "setram_sgr",
  "file_filter": "consolidado_2025_08"
}
```

---

### `analisar_dados_arquivo(package_id, file_filter, operation, ...)`

Analisa dados já baixados. Executa operações sobre os dados.

**Parâmetros obrigatórios:**
- `package_id` — Mesma base de `baixar_arquivo_dados`
- `file_filter` — Mesmo filtro de `baixar_arquivo_dados`
- `operation` — Tipo de análise (veja tabela abaixo)

**Operações disponíveis:**

| Operação | Quando usar | Parâmetros extras | Retorna |
|---|---|---|---|
| `contar_linhas` | "Quantas linhas tem?" | - | Total de linhas e colunas |
| `preview` | "Mostra um amostra dos dados" | `limite` (padrão: 15) | Primeiras N linhas |
| `agrupar_e_somar` | "Quantos/Total/Soma por X" | `filter_column`, `filter_value`, `sum_column` | Total agregado |
| `contar_por_valor` | "Quantas ocorrências de X?" | `filter_column`, `filter_value` | Contagem |
| `agrupar_valores_unicos` | "Ranking de X por volume" | `coluna` | Todos valores + contagens |
| `valores_unicos` | "Quais valores tem em X?" | `coluna`, `limite`, `offset` | Lista de valores únicos |
| `contar_por_turno` | "Quantos em manhã/tarde/noite?" | `filter_column`, `filter_value` | Contagem por turno |
| `gerar_graficos` | (veja `gerar_graficos` abaixo) | - | - |

**Exemplo — Contar transações de idosos:**

```json
{
  "package_id": "setram_sgr",
  "file_filter": "consolidado_2025_08",
  "operation": "agrupar_e_somar",
  "filter_column": "Tipo de Gratuidade",
  "filter_value": "Idoso",
  "sum_column": "Qtde Transações"
}
```

---

### `gerar_graficos(package_id, file_filter, tipo_grafico, ...)`

Gera gráficos dos dados.

**Parâmetros obrigatórios:**
- `package_id`, `file_filter` — Mesmos de `analisar_dados_arquivo`
- `tipo_grafico` — `"barras"`, `"pizza"`, `"linha"`, `"comparacao"`

**Quando usar:**
- "Me mostra um gráfico"
- "Compara X com Y"
- "Visualiza os dados"

---

### `gerenciar_cache_sessao(acao, ...)`

Gerencia cache da sessão (dados já baixados).

**Parâmetros:**
- `acao` — `"info"`, `"limpar"`, `"listar"`

**Exemplo:**

```json
{
  "acao": "info"
}
```

**Retorna:** Resumo do cache atual (tamanho, arquivos, etc.)

---

## ⚠️ Ordem Típica de Chamadas

1. **Identificar base** → `listar_bases()` ou `buscar_infos_base("termo")`
2. **Verificar disponibilidade** → `listar_recursos_da_base(package_id, termo_busca)`
3. **Baixar dados** → `baixar_arquivo_dados(package_id, file_filter)`
4. **Analisar** → `analisar_dados_arquivo(package_id, file_filter, operation, ...)`
5. **Visualizar** (opcional) → `gerar_graficos(package_id, file_filter, tipo_grafico)`

---

## 🚫 Erros Comuns

❌ Chamar `analisar_dados_arquivo` sem `baixar_arquivo_dados` primeiro  
✅ **SEMPRE** baixar → depois analisar

❌ Usar `file_filter = "2025_08"` (ambíguo)  
✅ Usar `file_filter = "consolidado_2025_08"` ou `"publico_2025_08_15"`

❌ Passar `filter_column = "Col1,Col2"` (duas colunas)  
✅ Usar uma coluna por vez, ou fazer duas chamadas

❌ Assumir que base está vazia sem chamar `listar_recursos_da_base`  
✅ **SEMPRE** verificar com a ferramenta primeiro