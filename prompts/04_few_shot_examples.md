# Exemplos Completos — Few-Shot

## EXEMPLO 1: Pergunta mensal simples (1 dimensão)
**Usuário:** "Quantas pessoas andaram de trem em agosto?"
**Raciocínio do agente:** 
- Identificar que é uma pergunta generalista, pois não cita nada relacionado a gratuidade nem a bilhete único, portanto é a base: setram_sbe (Bilhetagem eletrônica)
- Agosto é citado isoladamente: Utilizar **CONSOLIDADO** mensal e inferir o *ano* a ser utilizado por quando o mês ocorreu de forma mais recente com a ferramenta **get_current_date()**
- A pergunta apenas filtra por **Modal** = Trem. Use a operação *agrupar_e_somar*.

### Ações
**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sbe", "file_filter": "consolidado_2026_08" })`
**Ação 2:** `analisar_dados_arquivo({ "package_id": "setram_sbe", "file_filter": "consolidado_2026_08", "operation": "agrupar_e_somar", "filter_column": "Modal Operadora", "filter_value": "TRENS", "sum_column": "Qtde Transações" })`
**Resposta esperada:** "Em agosto de 2026, foram registradas **107.700** transações em Bilhetagem Eletrônica no modal TRENS."

## EXEMPLO 2: Pergunta cruza dois filtros — Modal + Tipo Gratuidade
**Usuário:** "Quantos idosos andaram de ônibus em janeiro deste ano com gratuidade?"
**Raciocínio do agente:** 
- Identificar que é uma pergunta que cita um tipo de gratuidade, portanto é da base: setram_sgr (Gratuidades)
- Janeiro é citado sem o dia e com o ano atual: Utilizar **CONSOLIDADO** mensal e inferir o ano atual com a **get_current_date()**
- O usuário deseja cruzar 2 dimensões Modal="ÔNIBUS" + Tipo="Idoso". Logo, localizar a linha que tem contém AMBOS os valores: ÔNIBUS + Idoso e retornar o total de transações

### Ações
**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sgr", "file_filter": "consolidado_2026_01" })`
**Ação 2:** `analisar_dados_arquivo({ "package_id": "setram_sgr", "file_filter": "consolidado_2026_01", "operation": "preview" })`
**Resposta esperada:** "Em janeiro de 2026, foram registradas **2.150.000** transações de gratuidade de idosos no modal ÔNIBUS."

## EXEMPLO 3: Pergunta fornece um dia específico
**Usuário:** "Quantas gratuidades para idosos existiu nos ônibus no dia 5 de março?"
**Raciocínio do agente:** 
- Identificar que a base de gratuidades é citada, portanto usar: setram_sgr (Gratuidades)
- O mês é citado junto com o dia (05 de março): Utilizar arquivo diário **PUBLICO**. Usar a **get_current_date()** para entender se é o mês é do ano atual ou anterior.
- Identificar o tipo de gratuidade pela coluna "Descrição da Aplicação". O valor e o ID na base é: "7001 - Idoso"

### Ações
**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sgr", "file_filter": "publico_2026_03_05" })`
**Ação 2:** `analisar_dados_arquivo({ "package_id": "setram_sgr", "file_filter": "publico_2026_03_05", "operation": "agrupar_e_somar", "filter_column": "Descrição da Aplicação", "filter_value": "7001 - Idoso", "sum_column": "Transações" })`


## EXEMPLO 4: Pergunta sobre tarifa
**Usuário:** "Quanto custa a passagem do metrô?"

### Ações
**Ação 1:** `baixar_arquivo_dados({ "package_id": "concessionaria-metrorio", "file_filter": "tarifas" })`
**Ação 2:** `analisar_dados_arquivo({ "package_id": "concessionaria-metrorio", "operation": "leitura_tarifa", "consulta_tipo": "atual" })`

**Resposta esperada:** "A passagem do MetrôRio hoje custa **R$ 7,90**."

## EXEMPLO 5: Erro — modal não existe
**Usuário:** "Quantas pessoas andaram de helicóptero em janeiro?"
**Raciocínio do agente:** 
- "helicóptero" NÃO é modal da base setram_sgr
- Modais: ÔNIBUS, TRENS, METRÔ, BARCAS, VANS
**Resposta esperada:** "A base de gratuidades não possui dados sobre helicóptero. Os modais disponíveis são: Ônibus, Trens, Metrô, Barcas e Vans." (NÃO chame nenhuma ferramenta)

## EXEMPLO 6: Usuário quer explorar
**Usuário:** "Que dados vocês têm de agosto?"

### Raciocínio
- Use **get_current_date()** para saber o ano atual. O usuário quer EXPLORAR, não analisar. Por isso, NÃO baixe arquivos, apenas liste-os.
- Se o usuário cita apenas o *mês* sem pedir informacao de dado diário, acrescente "_<número inteiro do mês>" ao fim do *termo_busca*
**Exemplo:**
- O ano é 2027 e o mês citado é Janeiro -> termo_busca = 2027_01
- O ano é 2022 e os meses citados são Outubro e Agosto. Execute a tool para cada mês com -> termo_busca = 2022_10 // termo_busca = 2022_08

### Ações
`listar_recursos_da_base({ "package_id": "setram_sbe", "termo_busca": "2025_08" })` -> Use o package_id correspondente a base requisitada pelo usuário

**Resposta esperada:** "Encontrei 32 arquivos de agosto. O que você gostaria de saber?"
**Atencao com a geracao da resposta:** A resposta só é válida se o agente percorrer todas as páginas. A contagem deve vir de recursos_encontrados e a listagem deve usar paginação.

## EXEMPLO 7: Total geral de um modal (soma todos os tipos)

**Usuário:** "Quantas transações de ônibus em fevereiro?"
**Raciocínio do agente:** 
- O usuário não especificou tipo de gratuidade. Entenda que ele deseja TOTAL de transações de um Modal específico.
- A referência de tempo é "Fevereiro" sem o dia. Portanto, use a **get_current_date()** para entender o ano de referência e use o filtro para arquivo **CONSOLIDADO**
- `agrupar_e_somar` com `filter_column="Modal Operadora"` soma TODOS os tipos

### Ações
**Ação 1:** `baixar_arquivo_dados({ "package_id": "setram_sbe", "file_filter": "consolidado_2026_02" })`
**Ação 2:** `analisar_dados_arquivo({ "package_id": "setram_sbe", "file_filter": "consolidado_2026_02", "operation": "agrupar_e_somar", "filter_column": "Modal Operadora", "filter_value": "ÔNIBUS", "sum_column": "Qtde Transações" })`

**Resposta esperada:**  "Em fevereiro de 2026, o modal ÔNIBUS registrou **3.320.000** transações de gratuidade (somando idosos, estudantes, deficientes, etc)."

## EXEMPLO 8: Estudantes no DIÁRIO (requer múltiplas chamadas)
**Usuário:** "Quantos estudantes andaram de ônibus no dia 10 de abril?"
**Raciocínio do agente:** 
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

**Resposta esperada:** "No dia 10 de abril de 2026, **124.000** estudantes usaram transporte gratuito (95.000 Vale Educação Estadual + 12.000 Federal + 7.000 Outros Estudantes + 10.000 Vale Educação Municipal intermunicipal)."

## EXEMPLO 9: Período de tempo que PARECE não existir
**Usuário:** "Quantas gratuidades na semana passada?"
**Data de hoje:** usar a get_current_date() para obter a data atual

**Raciocínio do agente:** 
- O usuário cita a "semana passada", então é necessário calcular o intervalo pedido de acordo com suas regras de inferencia de tempo
- Parece "fora do período visível"? **FORCE A BUSCA PELAS DATAS PEDIDAS PARA VERIFICAR A DISPONIBILIDADE**
- Usar `listar_recursos_da_base` com os dias pedidos.
- A verificação deve checar recursos_encontrados com *termo_busca* e, se houver tem_proxima_pagina, buscar as demais páginas.

### REGRA CRÍTICA - Pedidos com inferência de tempo

**Mesmo que pareça improvável que haja os dados pedidos:**
1. Chamar `listar_recursos_da_base` para VERIFICAR
2. Verificar `total_recursos_na_base`
3. Se total > 0, baixar e analisar
4. NÃO assumir que não existe sem verificar
**A verificação é obrigatória.**
