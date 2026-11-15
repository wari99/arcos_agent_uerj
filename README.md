<h1 align="center">  ARCOS-RJ 

![GitHub Status](https://img.shields.io/badge/Status-Work%20In%20Progress-yellow)
![Python](https://img.shields.io/badge/python-=3.13.12-blue?logo=python)
![Langchain](https://img.shields.io/badge/LangChain-1.0.7-ffffff?logo=langchain&logoColor=green)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-3.8.Flash-886FBF?logo=googlegemini&logoColor=fff)

---

## Sobre o Projeto

**ARCOS-RJ** é um agente de IA conversacional que está em desenvolvimento como trabalho de conclusão de curso na disciplina de Projeto Final do bacharelado em Ciência da Computação na Universidade do Estado do Rio de Janeiro (UERJ).

O sistema é um assistente conversacional que facilita o acesso e análise de dados públicos do Rio de Janeiro, abstraindo a complexidade da navegação da plataforma de dados abertos.

---

## Motivação 

A plataforma [Dados Abertos do RJ](https://dadosabertos.rj.gov.br/) contém um extenso acervo de informações públicas. Os usuários da plataforma podem encontrar alguns desafios ao navegar entre os grupos de arquivos:

- **Segmentação dos dados**: grande quantidade de bases de dados espalhadas pela plataforma
- **Navegação é confusa**: usuários que não conhecem a plataforma não são capazes de encontrar informações desejadas com facilidade
- **Volume de arquivos**: não há clareza na categorização e descrição dos recursos armazenados
- **Formatos dos arquivos**: diferentes formatos (CSV, XLSX, ZIP, PDF) exigem processamento manual
- **Alta complexidade em análises**: é necessário realizar download dos arquivos e descompactá-los para poder visualizar-los. Para fazer análises simples é necessário conhecer ferramentas que manipulem planilhas. 

### Solução desenvolvida:

ARCOS-RJ se integra à **API de Dados Abertos do RJ**, abstraindo a complexidade técnica da navegação e análise. O usuário pode fazer perguntas em linguagem natural e o agente de IA pode:

- **Localizar** automaticamente a base de dados correta
- **Baixar** e processar arquivos em múltiplos formatos
- **Analisar** os dados conforme solicitado
- **Apresentar** resultados de forma acessível
- **Incentivar** extração de informações extras nos arquivos

Dessa forma, tanto um usuário leigo quanto um usuário mais experiente e conhecedor da plataforma de Dados Abertos é capaz de navegar e obter informações com o uso de linguagem natural.

---

## Funcionalidades  

### Principais Ferramentas / Tools do Agente

| Ferramenta/Tool | Capacidade |
|-----------|-----------|
| **listar_bases** | Descobre as bases disponíveis no portal |
| **buscar_infos_base** | Encontra bases por nome ou descrição | 
| **listar_recursos_da_base** | Lista arquivos disponíveis numa base específica | 
| **baixar_arquivo_dados** | Baixa e processa arquivos (CSV, XLSX, ZIP) |
| **analisar_dados_arquivo** | Executa análises e operações sobre dados |
| **gerar_graficos** | Cria visualizações dos dados |
| **gerenciar_cache_sessao** | Gerencia cache local de arquivos |

---

##  Exemplos de Uso

### Exemplo 1: Buscar informação simples

```
👤 Você: Quantas pessoas andaram de ônibus em março?

🏖️ ARCOS-RJ:
   → Identifica base: setram_sgr (gratuidades)
   → Detecta período: março (arquivo consolidado)
   → Baixa dados automaticamente
   → Analisa e filtra por "ÔNIBUS"
   
   Em março de 2025, foram registradas **3.320.000** transações 
   de gratuidade no modal ÔNIBUS. 📊
```

### Exemplo 2: Analisar dados específicos

```
👤 Você: Quantos idosos andaram de metrô em julho do ano passado?

🏖️ ARCOS-RJ:
   → Base: setram_sgr
   → Período: julho de 2024 (consolidado)
   → Localiza linha: METRÔ + Idoso
   
   Em julho de 2024, **500.000** idosos utilizaram o METRÔ 
   através do programa de gratuidade. 
```

### Exemplo 3: Gerar visualização

```
👤 Você: Quero um gráfico com a distribuição de idosos por turno em abril.

🏖️ ARCOS-RJ:
   → Baixa dados de abril
   → Agrupa por turno (manhã, tarde, noite, madrugada)
   → Gera gráfico de barras
   
   📊 Gráfico salvo! [Visualização]
   Maior uso: **Tarde** com 45% das transações.
```

### Exemplo 4: Consultar tarifas

```
👤 Você: Quanto custa a passagem do metrô hoje?

🏖️ ARCOS-RJ:
   → Base: concessionaria-metrorio
   → Operação: leitura_tarifa (atual)
   
   A passagem do MetrôRio hoje custa **R$ 7,90**. 💰
```

---

## 🏗️ Arquitetura (WIP: biblioteca Diagrams)

![Arquitetura](./diagrams/imgs/architecture.png)

---

## Como Usar

> [!IMPORTANT]  
> O agente foi desenvolvido em ambiente MacOS. Portanto, algumas ferramentas do projeto podem depender de compatibilidade com Unix.
> No Windows, o uso do *make* pelo PowerShell pode apresentar problemas nas configurações de Path. Dê preferência para o WSL para utilizar os comandos abaixo.

### I. Pré-requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [make](https://www.gnu.org/software/make/) 
- LLM Model: chave da **Gemini API** *ou* projeto no **Google Cloud (Vertex AI)** *ou* **Ollama** rodando localmente. Para outras LLMs, modificar em model.py

### II. Clonar o repositório

```bash
git clone <url-do-repositorio>
```

### III. Criar o ambiente e instalar as dependências

```bash
make create-env
```

Cria o `.venv` com o Python 3.13.12 e instala as versões definidas em `pyproject.toml` e `uv.lock`. Ative o ambiente com:

```bash
source .venv/bin/activate
```

### IV. Configurar as variáveis de ambiente

```bash
cp .env.example .env
```

Abra o `.env` e preencha:

| Variável | Uso |
|---|---|
| `ROOT_AGENT_MODEL` | Nome do modelo. Se contiver `gemini`, usa Gemini; senão, usa Ollama |
| `GEMINI_API_KEY` | Chave da Gemini API. Se ficar vazia, usa Vertex AI |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Só para Vertex AI |
| `OLLAMA_BASE_URL` | Somente para Ollama (padrão `http://localhost:11434`) |
| `URL_*` | Endpoints da API de Dados Abertos do RJ. Não modificar.  |


### V. Executar o Agente

Chat no terminal (digite `/sair` para encerrar):

```bash
make run
```

Interface web (Streamlit):

```bash
make web
```

### Outros comandos

| Comando | O que faz |
|---|---|
| `make chat-history` | Mostra o histórico de conversas salvo no banco |
| `make f-chat-history` | Mostra o histórico formatado |
| `make delete-env` | Apaga o `.venv` |

---

## 🔐 API - endpoints do Portal de Dados Abertos

```env
# .env: 

URL_LISTAR_BASES=https://dadosabertos.rj.gov.br/api/3/action/package_list
URL_BUSCAR_BASE=https://dadosabertos.rj.gov.br/api/3/action/package_search?q={}
URL_CONSULTAR_PROCESSAR_ARQUIVO=https://dadosabertos.rj.gov.br/api/3/action/package_show?id={}
```

---

## Dados mais apoiados pelo ARCOS

### Bases Principais - Maior quantidade de arquivos padronizados e recursos testados durante o desenvolvimento

1. **setram_sgr** - Gratuidades no Transporte
   - Dados mensais
   - Dados diários

2. **setram_sbe** - Bilhetagem Eletrônica
   - Validações e embarques
   - Volume de passageiros

2. **setram_sbu** - Bilhete Único
   - Dados mensais
   - Dados diários

3. **concessionaria-metrorio** - Tarifas do Metrô

4. **concessionaria-ccr-barcas** - Tarifas das Barcas

5. **concessionaria-supervia** - Tarifas dos Trens

---

**Departamento de Ciência da Computação**  
**Instituto de Matemática e Estatística (IME)**  
**Universidade do Estado do Rio de Janeiro (UERJ)**


---
