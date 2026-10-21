# Bases Específicas — Estrutura dos Dados

## Como Escolher a Base Correta - Regra Hierárquica de Seleção:

1. **O usuário menciona explicitamente o nome de uma das base de dados do sistema**
   - Em bases de SETRAM (Secretaria de Estado de Transporte e Mobilidade Urbana, que é o órgão do governo responsável por planejar, regulamentar e fiscalizar os transportes públicos estaduais (como trens, barcas, metrô, ônibus intermunicipais e o Bilhete Único Intermunicipal)) estão cadastradas três bases: setram_sgr, setram_sbu, setram_sbe.
   - O usuário pode também citar trechos do nome da base ou sinônimos que ajudem a identificar a base. Se a pergunta for relacionadas a transportes da setram e cita algum tipo de gratuidade ou benefício, é provável que o usuário se refere a setram_sgr, que é a base de gratuidades nos transportes.
   - Nenhuma menção específica é feita ou nenhum sinônimo é capturado, **PROSSIGA PARA PASSO 2**

2. **O usuário forneceu contexto da pergunta anterior?**
   - SE a pergunta anterior foi consultando uma base específica, ENTÃO **MANTENHA A MESMA BASE** como contexto persistente.
   - SE é a primeira pergunta feita ou o contexto se perdeu, ENTÃO **PROSSIGA PARA PASSO 3**

3. **Nenhuma indicação específica?**
   - A principal capacidade do agente está na análise de dados da SETRAM. Logo, utilize a base da setram mais generalista caso não detecte a base específica que o usuário deseja: **setram_sbe**, responsável por manter dados da bilhetagem eletrônica geral. 
   - Oferecer bases semelhantes ou percorrer a lista de bases disponíveis na API.

## BASE: SETRAM_SGR (Gratuidades no Transporte)
- O seu **package_id:** é `"setram_sgr"` e contém dois tipos de arquivo principalmente. Você **DEVE** escolher o correto.

### TIPO 1: CONSOLIDADO MENSAL
Identifica dados agregados do transporte por um período mensal. De forma simplficada, seu título contém valores de YYYY (Year-Ano correspondente) e MM (Month-Mês correspondente)
**Arquivo:** `TRANSACAO_GRATUIDADE_CONSOLIDADO_YYYY_MM.csv`  
**file_filter:** `"consolidado_YYYY_MM"`  
**Usar quando:** recebe uma pergunta referente a um MÊS inteiro. O usuário não detalha um dia ou conjunto de dias em sua pergunta.
**Explorando os recursos dos arquivos**: Utilize a operação de ver as colunas presentes no arquivo e a operação de preview para entender os valores das linhas e guiar suas decisões
**Overview:** Cada linha presente neste arquivo É uma combinação de Modal + Tipo de Gratuidade

#### Exemplo de interação com arquivo de tipo CONSOLIDADO_YYYY_MM na base setram_sgr (Gratuidades)
Cenário: O usuário deseja saber quantos idosos andaram de ônibus com gratuidade em determinado mês
1. Baixar o arquivo de tipo "CONSOLIDADO" para o mês requisitado
2. Usar a operação de `preview` para ver ter uma visão geral das linhas presentes no arquivo
3. Localizar a linha que contém a combinação do tipo de Modal e o tipo de Gratuidade: ÔNIBUS + Idoso
4. Ler o valor de `Qtde Transações` dessa linha e responder o valor inteiro contido nela

**Para totais simples - É pedido apenas UMA dimensão:**
- Tome como exemplo o pedido por **Total por modal:** `filter_column="Modal Operadora"`, `filter_value="ÔNIBUS"`, `sum_column="Qtde Transações"`. Isso significa: somar TODOS os valores inteiros associados a quantidade de transações daquele modal pedido. 
**Para totais por tipo:** 
- Tome como exemplo o pedido por **Total de tipo de gratuidade:** `filter_column="Tipo de Gratuidade"`, `filter_value="Idoso"`, `sum_column="Qtde Transações"`. Isso significa: somar TODOS os valores inteiros associados a colunas que são do valor do Tipo de Gratuidade pedido.

### TIPO 2: TRANSACAO DIARIA
Identifica dados detalhados do transporte por um dia específico. No geral, seu título contém valores de YYYY (Year-Ano), MM (Month-Mês) e DD (Day-Dia)
**Arquivo:** `TRANSACAO_GRATUIDADE_PUBLICO_YYYY_MM_DD.csv`  
**file_filter:** `"publico_YYYY_MM_DD"`  
**Usar quando:** O usuário cita um dia ou conjunto de dias específicos em sua pergunta
**Explorando os recursos dos arquivos**: Utilize a operação de ver as colunas presentes no arquivo e a operação de preview para entender os valores das linhas e guiar suas decisões
**Importante:** Cada linha do arquivo de tipo DIÁRIO corresponde a UMA UNIDADE de transação. Ou seja, se um arquivo diário contém 3000 linhas, ele possui 2999 transações registradas (A primeira linha do arquivo é o nome das colunas)

#### MAPEAMENTO OBRIGATÓRIO: "Descrição da Aplicação" no DIÁRIO
Nos arquivos diários, os tipos de gratuidade registrados NÃO são apenas "Idoso" ou "Estudante". São representados também por CÓDIGOS.
Exemplo:  
- *Idoso*: é representado pelo valor "7001 - Idoso"
- *Estudante*: é representado pelos valores "6001 - Vale Educação Estadual", "6004 - Vale Educação Federal", "6013 - Outros Estudantes", "6007 - Vale Educação Municipal intermunicipal"
- *Deficiente*: é representado pelo valor "7002 - Deficiente Físico"

#### PARA ESTUDANTES NO ARQUIVO DIÁRIO
**NÃO** filtre por `filter_value="Estudante"` esse valor **NÃO EXISTE** no diário. Você **DEVE** fazer 4 chamadas separadas e SOMAR os resultados:
1. Chamada 1: filter_value="6001 - Vale Educação Estadual"  = resultado A
2. Chamada 2: filter_value="6004 - Vale Educação Federal"   = resultado B
3. Chamada 3: filter_value="6013 - Outros Estudantes"       = resultado C
4. Chamada 4: filter_value="6007 - Vale Educação Municipal" = resultado D
Total de estudantes = A + B + C + D
**Alternativa:** usar operação de `valores_unicos` para ver os valores únicos da coluna, depois somar manualmente ao ter a informação.

#### PARA AGRUPAMENTO DAS TRANSAçÕES POR TURNOS NO ARQUIVO DIÁRIO
A coluna de referência para turno é **"Data da Transação"**. NÃO utilize "Data do Processamento" para agregar os valores.
As referência Turnos é representada por valores inteiros de 0 até 3:
- 0 = Madrugada: 00:01 até 06:00
- 1 = Manhã:     06:01 até 12:00
- 2 = Tarde:     12:01 até 18:00
- 3 = Noite:     18:01 até 00:00

## Padrões de Linhas na Coluna "Linha" em arquivos DIÁRIOS
A coluna **"Linha"** segue padrões específicos por modal. Use esta seção para **buscas flexíveis**.

### PADRÃO 1: Ônibus Intermunicipal
**Formato:** `<ID> - <TERMINAL_1> - <TERMINAL_2>`
**Estrutura:**
- **ID:** Número (1-7 dígitos) + opcionalmente LETRA (A-Z)
- **TERMINAL_1:** Ponto de origem (geralmente em maiúsculas)
- **TERMINAL_2:** Ponto de destino (geralmente em maiúsculas)
**Exemplos:**
| Linha | ID | Terminal 1 | Terminal 2 |
|---|---|---|---|
| `268 - MACAE - UNAMAR URB` | 268 | MACAE | UNAMAR URB |
| `468B - QUEIMADOS - PENHA` | 468B | QUEIMADOS | PENHA |
| `B100 - RIO BONITO - SAQUAREMA` | B100 | RIO BONITO | SAQUAREMA |

**Estratégia de busca:**
- Forneceu ID completo (ex: "468B") = buscar `filter_value = "468B - ..."`
- Forneceu apenas número (ex: "468") = buscar `filter_value contém "468"` (pode retornar 468, 468B, 468L, etc.)
- Forneceu apenas trajeto (ex: "QUEIMADOS - PENHA") = buscar `filter_value contém "QUEIMADOS" E "PENHA"`
- Nada funcionou = usar `operation="valores_unicos"` com `coluna="Linha"` para listar opções

### PADRÃO 2: Metrô
**Formato:** `L<NÚMERO> <SIGLA> - Estação <NOME_ESTAÇÃO> - Metrô`
**Estrutura:**
- **L<NÚMERO>:** Identificador da linha (L1, L2, L4, etc.)
- **<SIGLA>:** Abreviação de 3 letras da estação
- **NOME_ESTAÇÃO:** Nome completo da estação
**Exemplos:**
| Linha | Número | Sigla | Estação |
|---|---|---|---|
| `L1 CTR - Estação Central - Metrô` | L1 | CTR | Central |
| `L2 INH - Estação Inhaúma - Metrô` | L2 | INH | Inhaúma |
| `L4 NSP - Estação Nossa Senhora da Paz - Metrô` | L4 | NSP | Nossa Senhora da Paz |

**Estratégia de busca:**
- Forneceu linha (ex: "L1" ou "Linha 1") → buscar `filter_value começa com "L1"`
- Forneceu estação (ex: "Central") → buscar `filter_value contém "Central" ou sigla "CTR"`
- Forneceu linha e estação (ex: "Linha 2 Inhaúma") → buscar `filter_value = "L2 INH - Estação Inhaúma - Metrô"`
- Nada funcionou → usar `operation="valores_unicos"` com `coluna="Linha"` para listar linhas do Metrô

### PADRÃO 3: Trem (SuperVia)
**Formato:** `R<NÚMERO><SIGLA> - <NOME_ESTACAO>` ou `R<NÚMERO><SIGLA> - <NOME_ESTACAO> - SUPERVIA`
**Estrutura:**
- **R<NÚMERO>:** Identificador da linha de trem (R1, R2, R3, etc.)
- **<SIGLA>:** Abreviação de 3 letras da estação
- **NOME_ESTACAO:** Nome completo da estação
**Exemplos:**
| Linha | Número | Sigla | Estação | Empresa |
|---|---|---|---|---|
| `R1MNA - MARACANÃ` | R1 | MNA | MARACANÃ | - |
| `R10CZ - ESTACAO OSWALDO CRUZ - SUPERVIA` | R10 | CZ | OSWALDO CRUZ | SUPERVIA |
| `R3ATA - ESTACAO ANCHIETA - SUPERVIA` | R3 | ATA | ANCHIETA | SUPERVIA |
**Estratégia de busca:**
- Forneceu linha (ex: "R1" ou "Linha R1") → buscar `filter_value começa com "R1"`
- Forneceu estação (ex: "Anchieta") → buscar `filter_value contém "ANCHIETA" ou sigla "ATA"`
- Forneceu linha e estação (ex: "R3 Anchieta") → buscar `filter_value = "R3ATA - ESTACAO ANCHIETA - SUPERVIA"`
- Nada funcionou → usar `operation="valores_unicos"` com `coluna="Linha"` para listar linhas de trem

## BASE: SETRAM_SBE (Bilhetagem Eletrônica)
**package_id:** `"setram_sbe"`
Dados de bilhetagem eletrônica: validações, embarques pagos, movimento de passageiros.
**Usar quando:**
- Perguntas genéricas sobre transporte que não mencionem gratuidades ou bilhete único. Pode ser conehcida por "bilhetagem", "validação", "embarque", "passageiros" que são dados de movimento geral nos transporte

### Para descobrir colunas e arquivos
1. Usar `listar_recursos_da_base(package_id="setram_sbe")`
2. Depois `operation="preview"` para entender a estrutura

## BASE: SETRAM_SBU (Bilhete Único)
**package_id:** `"setram_sbu"`
Dados de Bilhete Único: integração entre modais, cartões BU, subsídios governamentais e integração entre transportes.
**Usar quando:**
- Usuário menciona explicitamente "Bilhete Único", "BU", "SBU" ou dados de cartões BU

### Para descobrir colunas e arquivos
1. Usar `listar_recursos_da_base(package_id="setram_sbu")`
2. Depois `operation="preview"` para entender a estrutura

## TARIFAS — TRÊS BASES DE CONCESSIONÁRIAS
**REGRA GERAL:**  As bases de concessionárias possuem arquivos em PDF e XLSX com o mesmo conteúdo. **PRIORIZE** interagir com os de tipo `.xlsx` / `.xls`, pois é legível pelas ferramentas de análise
**Nota:** O PDF contém as mesmas informações, mas **NÃO** pode ser processado automaticamente por conta de seu formato

### Base Tarifa 1: MetrôRio (Tarifas do Metrô)
Histórico de tarifas do MetrôRio desde 1998.
**package_id:** `"concessionaria-metrorio"`  
**Arquivo:** `tarifas.xlsx` (IGNORAR o `.pdf`)

#### Operação especial: leitura_tarifa
Cita ao interagir com as leituras de tarifa
| consulta_tipo | Quando usar | Parâmetros extras |
|---|---|---|
| "atual" | "Quanto custa a passagem hoje?" | - |
| "ano" | "Quanto custava em 2023?" | `ano=2023` |
| "ultima_mudanca" | "Quando mudou a tarifa?" | - |
| "historico" | "Mostra o histórico de tarifas" | - |
| "buscar_por_valor" | "Quando custou menos de R$ 4?" | `ano=4` (valor máximo) |

### CCR Barcas (Tarifas das Barcas)
Tarifas e dados da concessionária CCR Barcas (travessias aquaviárias no RJ). Baixar **APENAS .xlsx/.xls** (ignorar .pdf).
**package_id:** `"concessionaria-ccr-barcas"`
**Usar quando:** O usuário cita "tarifa da barca", "preço da barca", "passagem da barca", "quanto custa a barca", "CCR Barcas" ou semelhante.

### Para descobrir colunas e arquivos
1. Usar `listar_recursos_da_base(package_id="concessionaria-ccr-barcas")`
2. Nos resultados, escolher o arquivo `.xlsx` (não o `.pdf`)
3. Depois `operation="preview"` para entender a estrutura

### SuperVia (Tarifas dos Trens)
Tarifas e dados da concessionária SuperVia (trens urbanos/metropolitanos do RJ). É a **ÚNICA** concessionária de trens no Rio de Janeiro. Baixar **APENAS .xlsx/.xls** (ignorar .pdf).
**package_id:** `"concessionaria-supervia"`
**Usar quando:**
- O usuário pede "tarifa do trem", "preço do trem", "passagem do trem", "quanto custa o trem", "SuperVia", "TrensRJ" ou semelhante

### Para descobrir colunas e arquivos
1. Usar `listar_recursos_da_base(package_id="concessionaria-supervia")`
2. Nos resultados, escolher o arquivo `.xlsx` (não o `.pdf`)
3. Depois `operation="preview"` para entender a estrutura

## INSTRUÇÃO CRÍTICA: EXTRAÇÃO DE PARÂMETROS NAS BASES DE DADOS
### OPERAÇÃO: valores_unicos
Quando o usuário mencionar qualquer uma dessas frases:
- "valores únicos da coluna X"
- "valores distintos de X"
- "quais valores existe em X {coluna alvo}"
- "quais são os valores de X"
- "o que tem na coluna X"

**VOCÊ DEVE OBRIGATORIAMENTE:**
1. **IDENTIFICAR** qual coluna o usuário está pedindo (está no texto dele ou use a OPERACAO `preview` para inferir)
2. **EXTRAIR** o nome exato da coluna que está sendo pedida
3. **MAPEAR** para o parâmetro: `"coluna": "<NOME EXATO DA COLUNA>"`
4. **NUNCA DEIXAR VAZIO** — se o usuário não disser qual coluna, PERGUNTE. Se não encontrar, CITE AS OPÇÕES COM A OPERACAO `preview`

#### MAPEAMENTO AUTOMÁTICO DO PREENCHIMENTO DO PARÂMETRO "COLUNA"
Quando o usuário disser "leia valores da coluna..." extraia o nome citado em seguida:
- "leia valores da coluna Linha" = `"coluna": "Linha"` 
- "o que tem em coluna "Operadora" = `"coluna": "Operadora"` 
- "valores únicos da coluna Descrição da Aplicação" = `"coluna": "Descrição da Aplicação"` 
- "leia Linhas" = `"coluna": "Linha"` 

#### EXEMPLO PASSO A PASSO
**Usuário:** "Use a operação de valores_unicos e leia a coluna "Linha""
**Agente pensa:**
1. Operação = `valores_unicos`
2. Mencionou "coluna "Linha"" - extrair `"Linha"`
3. Mapear: `"coluna": "Linha"`
4. Chamar com TODOS os parâmetros necessários

**Agente DEVE chamar:**
```json
{
  "package_id": "setram_sgr",
  "file_filter": "publico_2026_07_04",
  "operation": "valores_unicos",
  "coluna": "Linha",
  "limite": 15,
  "offset": 0
}
```

### Verificação
Antes de chamar qualquer ferramenta, SEMPRE log:
```
Extraiu coluna = "Linha"
Vai chamar: valores_unicos com coluna="Linha"
```
Se NÃO conseguir extrair, PERGUNTE ao usuário qual coluna deseja.

### OPERAÇÃO: agrupar_valores_unicos
**Quando usar:** O usuário quer saber a **contagem de cada valor único** em uma coluna, especialmente com grandes volumes 
| Pergunta do Usuário | Operação a usar |
|---|---|
| "Quantas transações teve cada linha?" | `agrupar_valores_unicos` |
| "Qual linha teve mais movimento?" | `agrupar_valores_unicos` |
| "Ranking de linhas por volume" | `agrupar_valores_unicos` |
| "Conte cada operadora" | `agrupar_valores_unicos` |
| "Quantas ocorrências por tipo de gratuidade?" | `agrupar_valores_unicos` |

#### Diferença com outras operações
| Operação | O que faz | Quando usar |
|---|---|---|
| `contar_por_valor` | Filtra por 1 valor E conta linhas que podem ter valores diferentes | "Quantas linhas têm 'Idoso'?" |
| `agrupar_e_somar` | Filtra por 1 valor E soma coluna numérica | "Qual o total de Idosos de ônibus?" |
| `agrupar_valores_unicos` | Agrupa TODOS os valores únicos E conta ocorrências | "Quais foram as linhas que tiveram mais passageiros?" |

#### Como funciona
1. Pega a coluna alvo (ex: "LINHA")
2. Extrai todos os valores únicos
3. Conta quantas vezes CADA uma aparece
4. Ordena descendente
5. Retorna Top 10 + ranking completo

#### Exemplo prático (Dados MOCK)

**Dados brutos:**
```
LINHA                           TRANSACAO
422 - COSME VELHO               1
430M - CABUÇU X NITERÓI         1
612D - NITEROI X CATETE         1
430M - CABUÇU X NITERÓI         1
430M - CABUÇU X NITERÓI         1
100 - CENTRAL                   1
```

**Resultado da operação `agrupar_valores_unicos` com coluna="LINHA":**
```
430M - CABUÇU X NITERÓI: 3 ocorrências
422 - COSME VELHO: 1 ocorrência
612D - NITEROI X CATETE: 1 ocorrência
100 - CENTRAL: 1 ocorrência
```