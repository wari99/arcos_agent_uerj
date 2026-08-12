# Exemplos Completos — Few-Shot

Siga estes padrões.

---

## EXEMPLO 1: Pergunta mensal simples (1 dimensão)

**Usuário:** "Quantas pessoas andaram de trem em agosto?"

### Raciocínio

- Transporte → base "setram_sbe" 
- "agosto" sem dia → **CONSOLIDADO** mensal
- Mês 08 > mês atual (7) → ano 2025
- `file_filter = "consolidado_2025_08"`
- 1 dimensão (só modal) → agrupar_e_somar direto

### Ações

**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sbe", "file_filter": "consolidado_2025_08" })`

**Ação 2:** `analisar_dados_arquivo({ "package_id": "setram_sbe", "file_filter": "consolidado_2025_08", "operation": "agrupar_e_somar", "filter_column": "Modal Operadora", "filter_value": "TRENS", "sum_column": "Qtde Transações" })`

### Resposta

"Em agosto de 2025, foram registradas **107.700** transações em Bilhetagem Eletrônica no modal TRENS."

---

## EXEMPLO 2: Pergunta cruzada — modal + tipo (CONSOLIDADO)

**Usuário:** "Quantos idosos andaram de ônibus em janeiro com gratuidade?"

### Raciocínio

- Transporte → "setram_sgr"
- "janeiro" sem dia → **CONSOLIDADO** mensal
- Mês 01 <= mês atual (7) → ano 2026
- Quer cruzar 2 dimensões: Modal="ÔNIBUS" + Tipo="Idoso"
- Consolidado tem ~15 linhas → usar `preview` para VER todas as linhas
- Localizar a linha que tem AMBOS: ÔNIBUS + Idoso

### Ações

**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sgr", "file_filter": "consolidado_2026_01" })`

**Ação 2:** `analisar_dados_arquivo({ "package_id": "setram_sgr", "file_filter": "consolidado_2026_01", "operation": "preview" })`

→ Resultado mostra TODAS as ~15 linhas do consolidado  
→ Localizar a linha: Modal Operadora="ÔNIBUS" E Tipo de Gratuidade="Idoso"  
→ Ler o valor da coluna "Qtde Transações" dessa linha

### Resposta

"Em janeiro de 2026, foram registradas **2.150.000** transações de gratuidade de idosos no modal ÔNIBUS."

---

## EXEMPLO 3: Pergunta com dia específico

**Usuário:** "Quantas gratuidades para idosos existiu nos ônibus no dia 5 de março?"

### Raciocínio

- Transporte → "setram_sgr"
- "dia 5 de março" → **DIÁRIO** detalhado
- Mês 03 <= mês atual (7) → ano 2026
- `file_filter = "publico_2026_03_05"`
- Coluna: "Descrição da Aplicação", valor: "7001 - Idoso"

### Ações

**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sgr", "file_filter": "publico_2026_03_05" })`

**Ação 2:** `analisar_dados_arquivo({ "package_id": "setram_sgr", "file_filter": "publico_2026_03_05", "operation": "agrupar_e_somar", "filter_column": "Descrição da Aplicação", "filter_value": "7001 - Idoso", "sum_column": "Transações" })`

---

## EXEMPLO 4: Pergunta sobre tarifa

**Usuário:** "Quanto custa a passagem do metrô?"

### Ações

**Ação 1:** `baixar_arquivo_dados({ "package_id": "concessionaria-metrorio", "file_filter": "tarifas" })`

**Ação 2:** `analisar_dados_arquivo({ "package_id": "concessionaria-metrorio", "operation": "leitura_tarifa", "consulta_tipo": "atual" })`

### Resposta

"A passagem do MetrôRio hoje custa **R$ 7,90**."

---

## EXEMPLO 5: Erro — modal não existe

**Usuário:** "Quantas pessoas andaram de helicóptero em janeiro?"

### Raciocínio

- "helicóptero" NÃO é modal da base setram_sgr
- Modais: ÔNIBUS, TRENS, METRÔ, BARCAS, VANS

### Resposta

"A base de gratuidades não possui dados sobre helicóptero. Os modais disponíveis são: Ônibus, Trens, Metrô, Barcas e Vans."

(NÃO chame nenhuma ferramenta)

---

## EXEMPLO 6: Usuário só quer explorar

**Usuário:** "Que dados vocês têm de agosto?"

### Raciocínio

- Quer EXPLORAR, não analisar
- NÃO baixar, apenas listar

### Ações

`listar_recursos_da_base({ "package_id": "setram_sgr", "termo_busca": "2025_08" })`

### Resposta

"Encontrei 32 arquivos de agosto. O que você gostaria de saber?"

---

## EXEMPLO 7: Total geral de um modal (soma todos os tipos)

**Usuário:** "Quantas transações de ônibus em fevereiro?"

### Raciocínio

- NÃO especificou tipo de gratuidade → quer TOTAL do modal
- "fevereiro" sem dia → **CONSOLIDADO**
- Mês 02 <= mês atual (7) → ano 2026
- `agrupar_e_somar` com `filter_column="Modal Operadora"` soma TODOS os tipos

### Ações

**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sbe", "file_filter": "consolidado_2026_02" })`

**Ação 2:** `analisar_dados_arquivo({ "package_id": "setram_sbe", "file_filter": "consolidado_2026_02", "operation": "agrupar_e_somar", "filter_column": "Modal Operadora", "filter_value": "ÔNIBUS", "sum_column": "Qtde Transações" })`

### Resposta

"Em fevereiro de 2026, o modal ÔNIBUS registrou **3.320.000** transações de gratuidade (somando idosos, estudantes, deficientes, etc)."

---

## EXEMPLO 8: Estudantes no DIÁRIO (requer múltiplas chamadas)

**Usuário:** "Quantos estudantes andaram de ônibus no dia 10 de abril?"

### Raciocínio

- "dia 10 de abril" → **DIÁRIO**
- `file_filter = "publico_2026_04_10"`
- "Estudante" NÃO EXISTE como valor no diário
- Preciso somar 4 códigos: 6001, 6004, 6013, 6007

### Ações

**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sgr", "file_filter": "publico_2026_04_10" })`

**Ação 2:** `analisar_dados_arquivo({ "operation": "agrupar_e_somar", "filter_column": "Descrição da Aplicação", "filter_value": "6001 - Vale Educação Estadual", "sum_column": "Transações" })` → Resultado: 95.000

**Ação 3:** `analisar_dados_arquivo({ "operation": "agrupar_e_somar", "filter_column": "Descrição da Aplicação", "filter_value": "6004 - Vale Educação Federal", "sum_column": "Transações" })` → Resultado: 12.000

**Ação 4:** `analisar_dados_arquivo({ "operation": "agrupar_e_somar", "filter_column": "Descrição da Aplicação", "filter_value": "6013 - Outros Estudantes", "sum_column": "Transações" })` → Resultado: 7.000

**Ação 5:** `analisar_dados_arquivo({ "operation": "agrupar_e_somar", "filter_column": "Descrição da Aplicação", "filter_value": "6007 - Vale Educação Municipal intermunicipal", "sum_column": "Transações" })` → Resultado: 10.000

### Resposta

"No dia 10 de abril de 2026, **124.000** estudantes usaram transporte gratuito (95.000 Vale Educação Estadual + 12.000 Federal + 7.000 Outros Estudantes + 10.000 Vale Educação Municipal intermunicipal)."

## EXEMPLO 9: Período de tempo que PARECE não existir

**Usuário:** "Quantas gratuidades na semana passada?"

**Data de hoje:** usar a get_current_date() para obter a data atual

### Raciocínio

- "semana passada" = calcular o intervalo pedido de acordo com suas regras de inferencia de tempo
- Parece "fora do período visível"? **FORCE A BUSCA PELAS DATAS PEDIDAS PARA VERIFICAR A DISPONIBILIDADE**
- VOCÊ DEVE verificar mesmo assim
- Usar `listar_recursos_da_base` com os dias pedidos.

### REGRA CRÍTICA - Pedidos com inferência de tempo

**Mesmo que pareça improvável que haja os dados pedidos:**
1. Chamar `listar_recursos_da_base` para VERIFICAR
2. Verificar `total_recursos_na_base`
3. Se total > 0, baixar e analisar
4. NÃO assumir que não existe sem verificar

**A verificação é obrigatória.**

---