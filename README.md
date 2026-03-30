# ARCOS-RJ 

O **ARCOS-RJ** é um agente conversacional especializado em dados do Rio de Janeiro, projetado para interagir com o portal de Dados Abertos do RJ.

---

## Objetivo

O ARCOS-RJ foi desenvolvido para facilitar o acesso e análise de dados públicos, permitindo através do agente:

- Consultar informações
- Baixar arquivos
- Realizar análises simples
- Gerem visualizações e gráficos

---

## LangChain e LangGraph

O LangChain é um framework usado para criar agentes através de modelos de linguagem (LLMs). O LangGraph é uma extensão do LangChain que adiciona suporte para gerenciar estados e fluxos de execução

### Funcionalidades:

Para garantir que o ARCOS funcione corretamente e atenda os pedidos do usuário durante a conversa de forma ordenada e sem perder contexto, temos funcionalidades como:

- **Persistência**  
  Utiliza checkpoint para salvar o que foi conversado na sessão, através do conceito de memória

- ~~**Gerenciamento de Estados**~~  
  ~~Define estados e transições no fluxo de conversação.~~
  #Ainda WIP 

- **Integração com Ferramentas**  
  Permite executar ferramentas específicas conforme disponível no agente e direcionamentos prévios do prompt a LLM.

---

##  Estrutura do Projeto

O projeto é dividido em ferramentas (as `tools`) e cada uma delas possui responsabilidade definida:

### 1. `listar_bases.py`

**Função:**  
Retorna a lista de todas as bases disponíveis no portal Dados Abertos RJ. Conecta-se na API do CKAN em Dados Abertos RJ. 

**Detalhes:**
- Consulta a API do portal
- Retorna identificadores das bases

**Exemplo:**
- "Quais bases estão disponíveis?" 
- "Você conhece quais bases?"

---

### 2. `buscar_infos_base.py`

**Função:**  
Busca informações detalhadas sobre uma base específica. Geralmente executada após a tool anterior, onde todas as bases disponíveis são apresentadas.

**Detalhes:**
- Título
- Descrição
- Quantidade de recursos

**Exemplo:**
- "Conhece a base de Gratuidades?"
- "O que você sabe sobre base X?"

---

### 3. `listar_recursos_da_base.py`

**Função:**  
Lista todos os arquivos disponíveis em uma base específica. Geralmente executada após a tool anterior, dando mais detalhes dos recursos/arquivos que estão disponíveis. 

**Detalhes:**
- Permite filtros por termos
- Analisa padrões de nomes
- Retorna:
  - Nome
  - Formato
  - Tamanho
  - URL

**Exemplo:**
- "Quais arquivos tem em base Y?"
- "Me mostra arquivos de Dezembro de 2025 da base Z"
---

### 4. `baixar_arquivo_dados.py`

**Função:**  
Baixa e processa arquivos para um dataframe Pandas, que vai ser utilizado para fazer análises futuras. Usa parametros dados pelo usuário e então identifica o pacote que deve ser tratado.

**Detalhes:**
- Usa um sistema de cache para evitar downloads repetidos
- Consultar o mesmo arquivo várias vezes fará com que o sistema verifique o cache antes de baixar novamente
- Cria pasta temporária que armazenará os arquivos baixados
- Gerencia essa pasta temporária também, excluindo-a quando o fluxo tiver que ser encerrado
- Suporta arquivos ZIP contendo um CSV
- Suporta CSV
- Lê o arquivo de acordo com o tipo de separador identificado
- ~~Suportará ainda arquivos .xlsx. Sem estar em .zip primeiro~~ WIP
- Retorna sobre :
  - Número de linhas
  - Número de Colunas
  - Tamanho do arquivo
  - Se arquivo está em cache ou está sendo baixado para lá.

**Exemplo:**
- "Quantas linhas tem os dados consolidados de janeiro 2025?"

Essa tool será acionada passivamente pois é necessário ter o arquivo baixado para fazer a leitura nele e por consequência, realizar alguma operação.

---

### 5. `analisar_dados_arquivo.py`

**Função:**  
Executa análises nos dados já baixados. Usa o que está em cache evitando duplicações, recebendo como entrada o pacote a ser tratado e que operação deve ser feita nele

**Operações disponíveis:**
- `contar_linhas`: retorna o numero total de linhas de um arquivo
- `mostrar_colunas`: lista o nome das colunas disponíveis para a consulta
- `preview`: mostra as 5 primeiras linhas no arquivo
- `contar_por_valor`: conta quantas linhas possuem um valor especifico
- `agrupar_e_somar`: filtra por um valor de uma coluna e soma valores de outra coluna referente a mesma informação
- Valores em um arquivo: `média`, `soma`, `máximo`, `mínimo`

**Exemplo:**
- "Quais são as colunas que existem nesse arquivo?"
- "Qual o valor total da quantidade de transações em Julho de 2025?"

---

### 6. `gerar_graficos.py`

**Função:**  
Gera visualizações a partir dos dados. Requer solicitação explícita do usuário ou confirmação após sugestão do próprio agente.

**Tipos de gráficos:**
- Barras
- Linhas
- Pizza

**Exemplo:**
- "Faça um gráfico comparando o total de transações de Janeiro de 2025 e Fevereiro de 2025"
- "Pode me dar as informações do gráfico por escrito?"

---

### 7. `gerenciar_cache_sessao.py`

**Função:**  
Gerencia todos os arquivos que estão armazenados em cache. Lista arquivos, dá informações básicas sobre eles e os remove.

**Ações:**
- `listar`: list autdo que está armanezado 
- `limpar`: limpa tudo da pasta temporária no encerramento
- `remover_arquivo`: remove arquivo específico 

---

### 8. `limpeza_encerramento.py`

**Função:**  
Remove arquivos temporários ao final da execução.

---

## Fluxo de Interação

O ARCOS-RJ segue um fluxo controlado:

1. Identifica a solicitação do usuário  
2. Confirma disponibilidade dos dados  
3. Perguntar qual operação deve ser realizada  
4. Executa _somente o que foi_ solicitado  
5. Oferecer próximos passos  

---

## Regras de Uso definidas em prompt

- Não executa ações automaticamente sem ser pedido
- Usuário sempre no controle do próximo passo
- Utilizar cache sempre que possível, evitando baixar novamente arquivos mencionados em outro momento futuro na conversa
- Análises rápidas de um arquivo com operações listadas anteriormente

---

## Observação

O ARCOS-RJ está sendo projetado como Projeto Final do curso de Ciência da Computação da UERJ, em competências do uso de Inteligência Artificial, Ciência de Dados e Agentes de IA. 

---