# O Que Nunca Fazer — Anti-Exemplos

---

## file_filter

❌ `file_filter = "2025_08"`  
(ambíguo — baixa diários E consolidados misturados)

✅ `file_filter = "consolidado_2025_08"`  
(preciso — baixa só o consolidado)

---

❌ `file_filter = "2025_08_15"`  
(ambíguo — pode casar com consolidado)

✅ `file_filter = "publico_2025_08_15"`  
(preciso — baixa só o diário daquele dia)

---

## Colunas e Filtros

❌ `filter_column = "Descrição da Aplicação,Operadora"`  
(duas colunas numa string — causa erro "coluna não encontrada")

✅ `filter_column = "Descrição da Aplicação"`  
(uma coluna por vez)

---

❌ `filter_value = "ONIBUS"` quando dado é `"ÔNIBUS"`  
(o sistema normaliza acentos, mas PREFIRA o valor correto)

✅ `filter_value = "ÔNIBUS"`

---

## Comportamento do Agente

❌ **Usuário:** "Que arquivos tem de janeiro?"  
**Agente:** [baixa 31 arquivos] "Pronto, baixei tudo!"  
(usuário só queria LISTAR, não baixar)

✅ **Agente:** `listar_recursos_da_base()` → "Encontrei 32 arquivos. O que quer saber?"

---

❌ **Usuário:** "Quantos idosos em agosto?"  
**Agente:** [baixa publico_2025_08_01, 02, 03...] → analisa 5 diários  
(errado — pergunta mensal deve usar CONSOLIDADO)

✅ **Agente:** [baixa consolidado_2025_08] → analisa 1 arquivo → resposta imediata

---

❌ **Usuário:** "Quantos idosos de ônibus em janeiro?"  
**Agente:** "Não consigo filtrar por dois critérios ao mesmo tempo"  
(ERRADO — consolidado tem ~15 linhas, basta usar preview e LER)

✅ **Agente:** `preview` → localiza linha ÔNIBUS+Idoso → responde com o número

---

❌ Responder com dados inventados quando ferramenta falha

✅ "Não consegui encontrar essa informação. Valores disponíveis são: [lista]"

---

## Interação com Ferramentas

❌ Dizer "Quer que eu baixe?" ou "Posso baixar?"

✅ Baixar silenciosamente quando precisar analisar

---

❌ Usar `preview` para ler arquivo de tarifas de concessionária (mostra só 5 linhas)

✅ Usar `operation="leitura_tarifa"` que lê o arquivo inteiro e retorna dados estruturados

---

❌ "Não consigo visualizar todas as 229 linhas"

✅ Usar `leitura_tarifa` com `consulta_tipo="historico"` ou `"buscar_por_valor"`

---

## Tratamento de Dados Específicos

❌ **No DIÁRIO:** `filter_value="Estudante"` para contar estudantes  
(esse valor NÃO EXISTE no diário — retorna 0 ou match parcial inconsistente)

✅ Somar os códigos: "6001 - Vale Educação Estadual" + "6004 - Vale Educação Federal" + "6013 - Outros Estudantes" + "6007 - Vale Educação Municipal"

---

❌ **No DIÁRIO:** contar turno usando "Data do Processamento"  
(processamento pode ser no dia seguinte)

✅ Usar "Data da Transação" como referência para turno