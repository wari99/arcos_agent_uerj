# Tipos de Arquivo: CONSOLIDADO vs. PÚBLICO (diário)

⚠️ **Os dois tipos existem em `setram_sbe`, `setram_sgr` e `setram_sbu`.** O tipo de arquivo depende do **período** pedido; a base depende do **PASSO 2** de `02_decision_steps.md`.

| Aspecto | CONSOLIDADO | PÚBLICO (diário) |
|---|---|---|
| Nome | `TRANSACAO_<XXX>_CONSOLIDADO_YYYY_MM.csv` | `TRANSACAO_<XXX>_PUBLICO_YYYY_MM_DD.csv` |
| file_filter | `consolidado_YYYY_MM` | `publico_YYYY_MM_DD` |
| Período | Mês inteiro | Um dia |
| Linhas | ~15 (agregado) | ~300.000 (uma transação por linha) |
| Tem horário/linha/operadora? | Não | Sim |
| Quando usar | Mês sem dia específico | Dia específico, ranking, turno, linha |

`<XXX>` indica a base: `BE` = SBE, `GRATUIDADE` = SGR, `BU` = SBU.

## Consolidado
- **Uma dimensão:** `agrupar_e_somar` (ex.: `Modal Operadora=ÔNIBUS`, `coluna_soma="Qtd. Transações"`; nomes ilustrativos, confirme em `colunas`).
- **Duas ou mais dimensões:** `preview` com `limite=20` e leitura da linha que combina os filtros.

## Diário
| Objetivo | Operação |
|---|---|
| Total do dia | `contar_linhas` (desconsiderar o cabeçalho) |
| Soma filtrada | `agrupar_e_somar` |
| Quantos veículos/linhas distintos (no dia ou de um sindicato) | `contar_unicos` (ex.: `coluna_alvo="Nº Carro"`, filtro opcional `coluna="Sindicato"`, `valor="SINTERJ"`) |
| Ranking | `agrupar_valores_unicos` (ex.: `coluna="Linha"`) |
| Turno | `contar_por_turno` (distribuição por turno; `coluna_data` padrão = `Data da Transação`) ou `filtrar_por_turno` (`turno` 0–3) |

Colunas do diário em SBE/SBU: ver `03_specific_databases.md`. Use `preview` só se a coluna for desconhecida.
