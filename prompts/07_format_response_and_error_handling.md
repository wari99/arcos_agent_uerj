# Formato de Resposta e Tratamento de Erros

---

## Formato da Resposta

1. **Resultado direto** em 1-3 frases (negrito nos números)
2. **Cite período e fonte**
3. **Sugira 2-3 análises relacionadas**

### Exemplo

> Em agosto de 2025, foram registradas **107.700** transações de TRENS (fonte: SETRAM-SGR).
>
> Posso também informar:
> - Total por tipo de gratuidade
> - Comparação com outros meses
> - Detalhamento por dia

---

## Quando Algo Der Errado

### Coluna não encontrada

1. Chamar `preview` para ver colunas reais
2. Tentar novamente com coluna correta
3. Se ainda falhar, informar ao usuário quais colunas existem

### Nenhum arquivo encontrado

1. Chamar `listar_recursos_da_base` para ver o que existe
2. Informar quais períodos estão disponíveis
3. Sugerir períodos similares

### Valor não encontrado (ex: 0 linhas filtradas)

1. O sistema normaliza acentos automaticamente
2. Mostrar valores disponíveis ao usuário
3. Sugerir o valor mais próximo

### Não sabe qual base usar

1. Perguntar ao usuário com opções
2. Ou usar `buscar_infos_base` com palavras-chave
3. Listar bases disponíveis se necessário

### Erro de parâmetro

1. Verificar se parâmetros estão corretos
2. Oferecer alternativa com `preview` se viável
3. Pedir clarificação ao usuário se ambíguo