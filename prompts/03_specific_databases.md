# Bases de Dados

A escolha da base segue o PASSO 2 de `02_decision_steps.md`. O padrão é `setram_sbe`.

## Visão geral
| package_id | Conteúdo | Quando usar |
|---|---|---|
| `setram_sbe` | Bilhetagem eletrônica: validações, embarques, passageiros | **Padrão.** Qualquer pergunta de transporte sem termo específico |
| `setram_sgr` | Gratuidades (idoso, estudante, PCD) | Somente com termo explícito de gratuidade |
| `setram_sbu` | Bilhete Único (integração entre modais) | Somente com BU/SBU/integração |
| `concessionaria-metrorio` | Tarifas do metrô (desde 1998) | Preço/tarifa do metrô |
| `concessionaria-ccr-barcas` | Tarifas das barcas | Preço/tarifa da barca |
| `concessionaria-supervia` | Tarifas dos trens | Preço/tarifa do trem |

As três bases SETRAM têm arquivos `consolidado_YYYY_MM` e `publico_YYYY_MM_DD` (ver `09`). As colunas variam por base. Em SBE e SBU, descubra a estrutura com `listar_recursos_da_base` e depois `preview`.

## Colunas comuns (todas as bases SETRAM)
- **Consolidado:** `Modal Operadora` e `Qtde Transações`, além das dimensões próprias da base.
- **Diário:** `Linha`, `Operadora`, `Data da Transação` e `Data do Processamento`.

## Específico de `setram_sgr`
- **Consolidado:** cada linha combina `Modal Operadora` + `Tipo de Gratuidade` (`Idoso`, `Estudante`, `Deficiente Físico`).
- **Diário:** a coluna `Descrição da Aplicação` usa códigos:
  - Idoso → `7001 - Idoso`
  - Deficiente → `7002 - Deficiente Físico`
  - Estudante → **4 códigos, somar todos:** `6001 - Vale Educação Estadual`, `6004 - Vale Educação Federal`, `6013 - Outros Estudantes`, `6007 - Vale Educação Municipal intermunicipal`
  - Alternativa: `valores_unicos` na coluna e soma manual.

## Turnos (arquivos diários, coluna `Data da Transação`)
| Turno | Período |
|---|---|
| 0 | Madrugada: 00:01–06:00 |
| 1 | Manhã: 06:01–12:00 |
| 2 | Tarde: 12:01–18:00 |
| 3 | Noite: 18:01–00:00 |

Use `contar_por_turno`. Nunca use `Data do Processamento` para turnos.

## Padrões da coluna `Linha` (diário)
| Modal | Formato | Exemplo |
|---|---|---|
| Ônibus | `<ID> - <ORIGEM> - <DESTINO>` (ID: dígitos + letra opcional) | `468B - QUEIMADOS - PENHA` |
| Metrô | `L<N> <SIGLA> - Estação <NOME> - Metrô` | `L1 CTR - Estação Central - Metrô` |
| Trem | `R<N><SIGLA> - <NOME>[ - SUPERVIA]` | `R3ATA - ESTACAO ANCHIETA - SUPERVIA` |

**Como buscar:**
- ID completo → valor exato.
- Só o número (ex.: "468") → pode casar com 468, 468B etc.
- Estação → buscar pelo nome ou pela sigla.
- Se nada funcionar → `valores_unicos` com `coluna="Linha"`.

## Tarifas (concessionárias)
- Use somente arquivos `.xlsx`/`.xls`. Ignore os `.pdf`, que não podem ser processados.
- **MetrôRio:** arquivo `tarifas.xlsx`, operação `leitura_tarifa` com `consulta_tipo`:
  - `atual`
  - `ano` (com `ano=YYYY`)
  - `ultima_mudanca`
  - `historico`
  - `buscar_por_valor` (com `ano=<valor máximo>`)
- **Barcas e SuperVia:** `listar_recursos_da_base` → escolher o `.xlsx` → `preview`.

## Operações de coluna
| Operação | Uso |
|---|---|
| `valores_unicos` | "Quais valores existem na coluna X?" — exige `coluna` exata; se não informada, pergunte ou use `preview` |
| `agrupar_valores_unicos` | Ranking/contagem por valor ("qual linha teve mais movimento?") |
| `contar_por_valor` | Contar as linhas que têm um valor |
| `agrupar_e_somar` | Filtrar por um valor e somar uma coluna numérica |

Exemplo de chamada válida:
```json
{"package_id":"setram_sbe","file_filter":"publico_2026_07_04","operation":"valores_unicos","coluna":"Linha","limite":15,"offset":0}
```