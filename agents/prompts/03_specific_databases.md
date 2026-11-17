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

As três bases SETRAM têm arquivos `consolidado_YYYY_MM` e `publico_YYYY_MM_DD` (ver `09`). As colunas variam por base, por tipo de arquivo (consolidado ou diário) e por ano. **Não presuma nomes de coluna:** use exatamente os da lista `colunas` que `analisar_dados_arquivo` devolve em `_resumo_analise` (é o cabeçalho real do arquivo analisado). Se ainda não tiver essa lista, chame antes `mostrar_colunas` no arquivo. Os nomes citados neste prompt são exemplos de arquivos já vistos (ex. de diários SBE/SBU: `Data da Transação`, `Descrição da Aplicação`, `Operadora`, `Linha`, `Nº Carro`, `Sentido`, `Vl Trans`) e podem não existir no arquivo que você abrir.

## Colunas vistas nas bases SETRAM (exemplos; confirme em `colunas`)
- **Consolidado:** uma coluna de modal (ex.: `Modal Operadora`) e uma de quantidade (ex.: `Qtd. Transações`), além das dimensões próprias da base.
- **Diário:** ex.: `Linha`, `Operadora`, `Data da Transação` e `Data do Processamento`.

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
- **MetrôRio:** `file_filter="Tarifas.xlsx"` (o filtro `tarifas` puxa também um PDF), operação `leitura_tarifa` com `consulta_tipo`:
  - `atual`
  - `ano` (com `ano=YYYY`)
  - `ultima_mudanca`
  - `historico`
  - `buscar_por_valor` (com `ano=<valor máximo>`)
- **SuperVia:** `file_filter="Tarifas históricas.xlsx"` com `leitura_tarifa` (mesmas consultas do MetrôRio).
- **Barcas:** `listar_recursos_da_base` → escolher o `.xlsx` → `preview`.
- **Como informar as colunas (vale para as três):** as planilhas têm títulos antes do cabeçalho e os nomes variam. Faça `preview` do arquivo, veja qual linha tem os nomes reais das colunas (a posição 0 é a primeira linha mostrada) e informe em `leitura_tarifa`: `linha_cabecalho`, `coluna_tarifa`, `coluna_data` (início da vigência) e `coluna_descricao` (o que identifica cada tarifa: a linha/trajeto nas Barcas, a descrição do ato nas demais). Exemplos já vistos, para você conferir no `preview`: MetrôRio e SuperVia têm `Tarifa Autorizada (R$)`, `Início da Vigência` e `Descrição`; Barcas tem `Valor Praticado R$`, `Início Cobrança` e `Linha - Trajeto`; em todas o cabeçalho estava na posição 1.
- Se você não informar as colunas, o código tenta inferi-las e o retorno traz `colunas_usadas` e um `aviso`: confira se as colunas usadas fazem sentido e, se não, repita informando-as.

## Operações de coluna
| Operação | Uso |
|---|---|
| `valores_unicos` | "Quais valores existem na coluna X?" — exige `coluna` exata; se não informada, pergunte ou use `preview` |
| `agrupar_valores_unicos` | Ranking/contagem por valor ("qual linha teve mais movimento?"). Devolve o top 10; só para "os próximos", "do 11º ao 20º" ou "a lista toda" chame de novo com `offset` (e `limite`, máx. 100), seguindo `proximo_offset` enquanto `tem_mais` for verdadeiro |
| `contar_por_valor` | Contar as linhas que têm um valor |
| `contar_unicos` | Contar valores DISTINTOS de uma coluna (`coluna_alvo`), no arquivo todo ou só nas linhas de um filtro (`coluna`+`valor`). Ex.: carros em uso do Sinterj = `coluna_alvo="Nº Carro"`, `coluna="Sindicato"`, `valor="SINTERJ"` |
| `agrupar_e_somar` | Filtrar por um valor e somar uma coluna numérica |

Exemplo de chamada válida:
```json
{"package_id":"setram_sbe","file_filter":"publico_2026_07_04","operation":"valores_unicos","coluna":"Linha","limite":15,"offset":0}
```
