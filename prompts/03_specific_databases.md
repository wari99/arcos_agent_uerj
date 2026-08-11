# Bases Específicas — Estrutura dos Dados

---

## BASE: SETRAM_SGR (Gratuidades no Transporte)

Contém dois tipos de arquivo. Você **DEVE** escolher o correto.

### TIPO 1: CONSOLIDADO MENSAL

**Arquivo:** `TRANSACAO_GRATUIDADE_CONSOLIDADO_YYYY_MM.csv`  
**file_filter:** `"consolidado_YYYY_MM"`  
**Volume:** ~15 linhas por arquivo 
**Usar quando:** pergunta sobre MÊS inteiro, sem dia específico

#### Colunas

| Coluna | Tipo | Valores exemplo |
|---|---|---|
| Ano | int | 2025 |
| Mês | int | 1, 2, ..., 12 |
| Modal Operadora | string | ÔNIBUS, METRÔ, TRENS, BARCAS, VANS |
| Tipo de Gratuidade | string | Idoso, Deficiente Físico, Estudante |
| Qtde Transações | int | 2150000 |

#### IMPORTANTE

Cada linha JÁ É uma combinação (Modal + Tipo de Gratuidade).

**Exemplo de dados reais:**

| Modal Operadora | Tipo de Gratuidade | Qtde Transações |
|---|---|---|
| ÔNIBUS | Idoso | 2.150.000 |
| ÔNIBUS | Estudante | 850.000 |
| ÔNIBUS | Deficiente Físico | 320.000 |
| METRÔ | Idoso | 500.000 |
| METRÔ | Estudante | 200.000 |
| TRENS | Idoso | 107.700 |
| BARCAS | Idoso | 50.000 |
| VANS | Idoso | 30.000 |

#### Como usar

**Para "idosos de ônibus":**

1. Baixar o consolidado
2. Usar `preview` para ver TODAS as ~15 linhas
3. Localizar a linha: ÔNIBUS + Idoso
4. Ler o valor de `Qtde Transações` dessa linha
5. Responder com o número

**Para totais simples (1 dimensão):**

- **Total por modal:** `filter_column="Modal Operadora"`, `filter_value="ÔNIBUS"`, `sum_column="Qtde Transações"`  
  (soma TODOS os tipos de gratuidade daquele modal)

- **Total por tipo:** `filter_column="Tipo de Gratuidade"`, `filter_value="Idoso"`, `sum_column="Qtde Transações"`  
  (soma TODOS os modais daquele tipo)

---

### TIPO 2: DIÁRIO DETALHADO

**Arquivo:** `TRANSACAO_GRATUIDADE_PUBLICO_YYYY_MM_DD.csv`  
**file_filter:** `"publico_YYYY_MM_DD"`  
**Volume:** ~300k linhas por arquivo  
**Usar quando:** pergunta sobre DIA específico, ou detalhes por linha/operadora

#### Colunas

| Coluna | Tipo | Valores exemplo |
|---|---|---|
| Data do Processamento | datetime | 2025-01-15 00:00:00 |
| Data da Transação | datetime | 2025-01-15 08:32:00 |
| Descrição da Aplicação | string | "7001 - Idoso", "6001 - Vale Educação..." |
| Escola | string | Nome da escola (se estudante) |
| Linha | string | "128003 - S. JOÃO - CAXIAS" ou "L1 LMC - Estação Largo do Machado" |
| Nº Carro | int | 12345 |
| Nº Cartão | string | Identificador do cartão |
| Nº Censo Escola | int | Código INEP |
| Nº Validador | int | 67890 |
| Operadora | string | Nome da empresa |
| Sindicato | string | Nome do sindicato |
| Transações | int | 1 (sempre 1, cada linha = 1 passagem) |

#### MAPEAMENTO OBRIGATÓRIO: "Descrição da Aplicação" no DIÁRIO

No arquivo diário, os tipos de gratuidade NÃO são "Idoso" ou "Estudante" direto. São CÓDIGOS.

| Tipo no Consolidado | Códigos no Diário ("Descrição da Aplicação") |
|---|---|
| Idoso | "7001 - Idoso" |
| Estudante |  SÃO VÁRIOS — você DEVE somar TODOS:<br/>• "6001 - Vale Educação Estadual"<br/>• "6004 - Vale Educação Federal"<br/>• "6013 - Outros Estudantes"<br/>• "6007 - Vale Educação Municipal intermunicipal" |
| Deficiente | "7002 - Deficiente Físico" |

#### PARA ESTUDANTES NO DIÁRIO

**NUNCA** filtre por `filter_value="Estudante"` — esse valor NÃO EXISTE no diário.

Você **DEVE** fazer 4 chamadas separadas e SOMAR os resultados:

```
Chamada 1: filter_value="6001 - Vale Educação Estadual"  → resultado A
Chamada 2: filter_value="6004 - Vale Educação Federal"   → resultado B
Chamada 3: filter_value="6013 - Outros Estudantes"       → resultado C
Chamada 4: filter_value="6007 - Vale Educação Municipal" → resultado D
Total de estudantes = A + B + C + D
```

**Alternativa:** usar `preview` para ver os valores únicos da coluna, depois somar manualmente.

#### PARA TURNOS NO DIÁRIO

A coluna de referência para turno é **"Data da Transação"** (NÃO "Data do Processamento").

Turnos:
- 0 = Manhã (06:00 - 11:59)
- 1 = Tarde (12:00 - 17:59)
- 2 = Noite (18:00 - 23:59)
- 3 = Madrugada (00:00 - 05:59)

Transações com hora 00:00 são **MADRUGADA (turno 3)**, NÃO noite.

---

## BASE: SETRAM_SBE (Bilhetagem Eletrônica)

**package_id:** `"setram_sbe"`

Dados de bilhetagem eletrônica: validações, embarques pagos, movimento de passageiros.

### Quando usar

- "bilhetagem", "validação", "embarque", "passageiros"
- Perguntas sobre volume total de passageiros (pagos + gratuitos)
- Dados de movimento geral do transporte

### Para descobrir colunas e arquivos

1. Usar `listar_recursos_da_base(package_id="setram_sbe")`
2. Depois `preview` para entender a estrutura

---

## TARIFAS — 3 BASES DE CONCESSIONÁRIAS

### REGRA GERAL

As bases de concessionárias possuem arquivos em PDF e XLSX com o mesmo conteúdo.

- **SEMPRE** priorizar o `.xlsx` / `.xls` — é legível pelas ferramentas de análise
- O PDF contém as mesmas informações, mas **NÃO** pode ser processado automaticamente

---

### MetrôRio (Tarifas do Metrô)

**package_id:** `"concessionaria-metrorio"`  
**Arquivo:** `tarifas.xlsx` (IGNORAR o `.pdf`)

Histórico de tarifas do MetrôRio desde 1998.

#### Operação especial: leitura_tarifa

| consulta_tipo | Quando usar | Parâmetros extras |
|---|---|---|
| "atual" | "Quanto custa a passagem hoje?" | - |
| "ano" | "Quanto custava em 2023?" | `ano=2023` |
| "ultima_mudanca" | "Quando mudou a tarifa?" | - |
| "historico" | "Mostra o histórico de tarifas" | - |
| "buscar_por_valor" | "Quando custou menos de R$ 4?" | `ano=4` (valor máximo) |

---

### CCR Barcas (Tarifas das Barcas)

**package_id:** `"concessionaria-ccr-barcas"`

Tarifas e dados da concessionária CCR Barcas (travessias aquaviárias no RJ).

 Baixar **APENAS .xlsx/.xls** (ignorar .pdf). Os dados são espelhados, ou seja, o mesmo conteúdo está em ambos os tipos.

### Quando usar

- "tarifa da barca", "preço da barca", "passagem da barca"
- "quanto custa a barca", "CCR Barcas"

### Para descobrir colunas e arquivos

1. Usar `listar_recursos_da_base(package_id="concessionaria-ccr-barcas")`
2. Nos resultados, escolher o arquivo `.xlsx` (não o `.pdf`)
3. Depois `preview` para entender a estrutura

---

### SuperVia (Tarifas dos Trens)

**package_id:** `"concessionaria-supervia"`

Tarifas e dados da concessionária SuperVia (trens urbanos/metropolitanos do RJ).

É a **ÚNICA** concessionária de trens no Rio de Janeiro.

Baixar **APENAS .xlsx/.xls** (ignorar .pdf).

### Quando usar

- "tarifa do trem", "preço do trem", "passagem do trem"
- "quanto custa o trem", "SuperVia"

### Para descobrir colunas e arquivos

1. Usar `listar_recursos_da_base(package_id="concessionaria-supervia")`
2. Nos resultados, escolher o arquivo `.xlsx` (não o `.pdf`)
3. Depois `preview` para entender a estrutura

---

# INSTRUÇÃO CRÍTICA: EXTRAÇÃO DE PARÂMETROS NAS BASES DE DADOS

## OPERAÇÃO: valores_unicos

Quando o usuário mencionar qualquer uma dessas frases:
- "valores únicos da coluna X"
- "valores distintos de X"
- "quais valores existe em X {coluna alvo}"
- "quais são os valores de X"
- "o que tem na coluna X"

**VOCÊ DEVE OBRIGATORIAMENTE:**

1. **IDENTIFICAR** qual coluna o usuário está pedindo (está no texto dele ou use a OPERACAO `mostrar_colunas` para inferir)
2. **EXTRAIR** o nome exato da coluna que está sendo pedida
3. **MAPEAR** para o parâmetro: `"coluna": "<NOME EXATO DA COLUNA>"`
4. **NUNCA DEIXAR VAZIO** — se o usuário não disser qual coluna, PERGUNTE. Se não encontrar, CITE AS OPÇÕES COM A OPERACAO `mostrar_colunas`

### MAPEAMENTO AUTOMÁTICO DO PREENCHIMENTO DO PARÂMETRO "COLUNA"

Quando o usuário disser "leia valores da coluna...", extraia o nome citado em seguida:

| Texto do Usuário | Parâmetro coluna |
|---|---|
| "leia valores da coluna Linha" | `"coluna": "Linha"` |
| "o que tem em coluna "Operadora"" | `"coluna": "Operadora"` |
| "valores únicos da coluna Descrição da Aplicação" | `"coluna": "Descrição da Aplicação"` |
| "leia Linha" | `"coluna": "Linha"` |

### EXEMPLO PASSO A PASSO

**Usuário:** "Use a operação de valores_unicos e leia a coluna "Linha""

**Agente pensa:**
1. Operação = `valores_unicos`
2. Mencionou "coluna "Linha"" → extrair `"Linha"`
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

---

## VERIFICAÇÃO

Antes de chamar qualquer ferramenta, SEMPRE log:
```
Extraiu coluna = "Linha" ✓
Vai chamar: valores_unicos com coluna="Linha"
```

Se NÃO conseguir extrair, PERGUNTE ao usuário qual coluna deseja.

---

## OPERAÇÃO: agrupar_valores_unicos

### Quando usar

Quando o usuário quer saber a **contagem de cada valor único** em uma coluna, especialmente com grandes volumes (como encontramos em arquivos do tipo diário)

| Pergunta do Usuário | Operação a usar |
|---|---|
| "Quantas transações teve cada linha?" | `agrupar_valores_unicos` |
| "Qual linha teve mais movimento?" | `agrupar_valores_unicos` |
| "Ranking de linhas por volume" | `agrupar_valores_unicos` |
| "Conte cada operadora" | `agrupar_valores_unicos` |
| "Quantas ocorrências por tipo de gratuidade?" | `agrupar_valores_unicos` |

### Diferença com outras operações

| Operação | O que faz | Quando usar |
|---|---|---|
| `contar_por_valor` | Filtra por 1 valor E conta linhas que podem ter valores diferentes | "Quantas linhas têm 'Idoso'?" |
| `agrupar_e_somar` | Filtra por 1 valor E soma coluna numérica | "Qual o total de Idosos de ônibus?" |
| `agrupar_valores_unicos` | Agrupa TODOS os valores únicos E conta ocorrências | "Quais foram as linhas que tiveram mais passageiros?" |

### Como funciona a operação agrupar_valores_unicos

1. Pega a coluna alvo (ex: "LINHA")
2. Extrai todos os valores únicos
3. Conta quantas vezes CADA uma aparece
4. Ordena descendente
5. Retorna Top 10 + ranking completo

### Exemplo prático (Dados MOCK)

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

