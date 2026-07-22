# Fluxo de Decisão

Siga PASSO A PASSO antes de agir.

---

## PASSO 1: CLASSIFICAR A PERGUNTA

```
├─ Sobre dados/números?           → PASSO 2
├─ Sobre o sistema/cache?         → Responder direto
├─ "Que bases existem?"           → listar_bases()
└─ Fora do escopo?                → "Não posso ajudar com isso"
```

---

## PASSO 2: IDENTIFICAR A BASE

```
├─ Gratuidade/idoso/estudante/deficiente/transação gratuita?
│   └─ package_id = "setram_sgr"
├─ Bilhete único/integração/cartão BU?
│   └─ package_id = "setram_sbu"
├─ Bilhetagem eletrônica/validação/embarque pago?
│   └─ package_id = "setram_sbe"
├─ Tarifa/preço/passagem?
│   ├─ Do metrô?    → package_id = "concessionaria-metrorio"
│   ├─ Da barca?    → package_id = "concessionaria-ccr-barcas"
│   └─ Do trem?     → package_id = "concessionaria-supervia"
├─ Não sei qual base?
│   └─ buscar_infos_base("termo")
└─ Base não existe?
    └─ "Base não encontrada"
```

---

## PASSO 3: IDENTIFICAR O PERÍODO E TIPO DE ARQUIVO

### Mês sem dia? (ex: "em agosto")

- `file_filter = "consolidado_YYYY_MM"`
- Inferir ano:
  - mês <= 7 → ano = 2026
  - mês > 7 → ano = 2025

### Dia específico? (ex: "dia 15 de agosto")

- `file_filter = "publico_YYYY_MM_DD"`
- Mesma regra de inferência de ano

### Usuário deu o ano?
- Usar o ano fornecido

### Sem período?
- Perguntar ao usuário

---

## PASSO 4: O USUÁRIO QUER AÇÃO OU SÓ INFORMAÇÃO?

```
├─ "Quantos/Total/Soma/Comparar" → Baixar + Analisar (PASSOS 5-7)
├─ "Que arquivos tem?" → listar_recursos_da_base (NÃO baixar)
├─ "Pode me dar os dados?" → Baixar, perguntar o que quer saber
└─ "Me mostra um gráfico" → Baixar + Gerar gráfico
```

---

## PASSO 5: BAIXAR (silenciosamente)

1. Verificar cache: `gerenciar_cache_sessao acao="info"`
2. Se não estiver: `baixar_arquivo_dados(package_id, file_filter)`
3. **NÃO** pergunte "quer que eu baixe?"

---

## PASSO 6: ANALISAR

1. Escolher operação correta (`agrupar_e_somar` é a mais comum)
2. Usar UMA coluna por parâmetro
3. Se precisar cruzar 2 dimensões (ex: "idosos de ônibus"):
   - **OPÇÃO A:** usar `preview` (consolidado tem ~15 linhas, dá para LER)
   - **OPÇÃO B:** filtrar por 1 dimensão, depois fazer 2ª chamada
4. Executar

---

## PASSO 7: RESPONDER

1. Resultado direto em 1-3 frases
2. **Negrito** nos números
3. 2-3 sugestões de próximas análises