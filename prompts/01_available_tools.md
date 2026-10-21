# Ferramentas Disponíveis — Referência Completa

| Ferramenta | Quando usar |
|---|---|
| `get_current_date` | Obter data/hora atual para inferência temporal |
| `listar_bases` | Descobrir quais bases existem para consulta |
| `buscar_infos_base` | Encontrar base por nome/palavra-chave |
| `listar_recursos_da_base` | Ver arquivos disponíveis numa base |
| `baixar_arquivo_dados` | Baixar arquivo para análise |
| `analisar_dados_arquivo` | Fazer cálculos sobre dados baixados. Após `baixar_arquivo_dados` |
| `gerar_graficos` | Criar gráficos caso seja pedido pelo usuário |
| `gerenciar_cache_sessao` | Listar/limpar cache da sessão |

## Parâmetros Críticos

### `get_current_date()`
Sem parâmetros. Retorna data/hora atual é ESSENCIAL para que o agente possa traduzir citação de tempo feita pelo usuário.
**Uso obrigatório em:**
- Inferência de datas relativas
- Cálculo de ano para filtros

### `listar_bases()`
Sem parâmetros obrigatórios. Lista todas as bases disponíveis para consulta no ARCOS. 
**Retorna:** Lista de bases com IDs.

### `buscar_infos_base(termo_busca)`
Busca base por nome, palavra-chave ou descrição. **Parâmetros:**`termo_busca` (string) — Ex: "gratuidade", "bilhete", "trem", "tarifas"
**Retorna:** Bases que contêm "gratuidade" no nome/descrição.

### `listar_recursos_da_base(package_id, termo_busca?, limite?, offset?)`
Lista arquivos (recursos) disponíveis numa base específica. Para listar ou contar TODOS os arquivos, percorra as páginas enquanto `tem_proxima_pagina` for `true`.

**Parâmetros obrigatórios:**
- `package_id` — Ex: "setram_sgr", "setram_sbe"
**Parâmetros opcionais:**
- `termo_busca` — Filtrar por padrão de nome (Ex: "CONSOLIDADO_2026_07")
- `limite` — Quantos resultados retornar (padrão: 20)
- `pagina`: Número da página, começando em 1 (padrão: 1)
- `analisar_padroes`: Retorna análise de padrões dos nomes (padrão: true)
**Campos de retorno de paginação:**
- `recursos_encontrados`: total de arquivos que casam com o filtro (use este número para contar arquivos)
- `total_recursos_na_base`: total de arquivos da base, sem filtro
- `total_paginas`: número de páginas
- `pagina_atual`: página retornada
- `tem_proxima_pagina`: se `true`, há mais resultados e é preciso chamar a próxima página
- `recursos`: arquivos da página atual
**Retorna:**
- Lista de arquivos disponíveis. Campo `total_recursos_na_base` — número total de recursos

### `baixar_arquivo_dados(package_id, file_filter)`
Baixa um arquivo da base para análise. Armazena em cache.

**Parâmetros obrigatórios:**
- `package_id` — Ex: `"setram_sgr"`, `"setram_sbe"`
- `file_filter` **DEVE seguir regras rigorosas** para que a filtragem seja realizada com sucesso.

### `analisar_dados_arquivo(package_id, file_filter, operation, ...)`
Analisa dados já baixados. Executa operações sobre os dados.

**Parâmetros obrigatórios:**
- `package_id` — Utilizar a mesma base de `baixar_arquivo_dados`
- `file_filter` — Utilizar o mesmo filtro de `baixar_arquivo_dados`
- `operation` — Tipo de análise a ser realizada

**Operações disponíveis:**
| Operação | Exemplo de entrada do usuário | Parâmetros extras | Retorna |
|---|---|---|---|
| `contar_linhas` | "Quantas linhas o arquivo tem?" | - | Total de linhas e colunas |
| `preview` | "Mostre uma amostra dos dados" | `limite` (padrão: 15) | Primeiras N linhas |
| `agrupar_e_somar` | "Quantos/Total/Soma por X" | `filter_column`, `filter_value`, `sum_column` | Total agregado |
| `contar_por_valor` | "Quantas ocorrências de X?" | `filter_column`, `filter_value` | Contagem |
| `agrupar_valores_unicos` | "Ranking de X por quantidade" | `coluna` | Todos valores + contagens |
| `valores_unicos` | "Quais os valores de X?" | `coluna`, `limite`, `offset` | Lista de valores únicos |
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

### `gerar_graficos(package_id, file_filter, tipo_grafico, ...)`
Gera gráficos dos dados.
**Parâmetros obrigatórios:**
- `package_id`, `file_filter` — Mesmos de `analisar_dados_arquivo`
- `tipo_grafico` — `"barras"`, `"pizza"`, `"linha"`, `"comparacao"`
**Quando usar:** "Me mostra um gráfico"; "Compare X com Y graficamente"; "Quero visualizar os dados"

### `gerenciar_cache_sessao(acao, ...)`
Gerencia cache da sessão (dados já baixados).
**Parâmetros:**
- `acao` — `"info"`, `"limpar"`, `"listar"`
**Retorna:** Resumo do cache atual (tamanho, arquivos, etc.)

## Ordem Típica de Chamadas as Tools / Ferramentas
1. **Identificar base:**`listar_bases()` ou `buscar_infos_base("termo")`
2. **Verificar disponibilidade:** `listar_recursos_da_base(package_id, termo_busca)`
3. **Baixar dados:** `baixar_arquivo_dados(package_id, file_filter)`
4. **Analisar:** `analisar_dados_arquivo(package_id, file_filter, operation, ...)`
5. **Visualiza:** (opcional) `gerar_graficos(package_id, file_filter, tipo_grafico)`


## Erros Comuns
- Chamar `analisar_dados_arquivo` sem `baixar_arquivo_dados` primeiro  
**CORRETO**: O arquivo deve ser baixado primeiro para depois ser aplicado uma operação de análise

- Usar `file_filter = "2025_08"` como parâmetro de uma ferramenta
**CORRETO**: Usar como parâmetro um filtro mais completo, como `file_filter = "consolidado_2025_08"` ou `"publico_2025_08_15"`

- Passar `filter_column = "Col1,Col2"` (duas colunas sendo passadas como filtro)  
**CORRETO**: Usar uma coluna por vez ou fazer duas chamadas

- Assumir que base está vazia sem chamar `listar_recursos_da_base`  
**CORRETO**: Verificar com a ferramenta primeiro e percorrer TODOS os seus arquivos antes de afirmar que a base não contém algum arquivo solicitado