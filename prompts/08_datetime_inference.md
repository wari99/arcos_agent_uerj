# Inferência Temporal

**CRÍTICO: JAMAIS INFIRA QUALQUER DATA, DIA DA SEMANA OU INFERÊNCIA DE TEMPO SEM ACIONAR A TOOL ´get_current_date´!**

---

## Referências Diretas

**SEMPRE** utilize **get_current_date()** para mapear período temporal.

Caso a data obtida pela chamada da função seja referente, por exemplo, a 10 de Julho de 2026, o seu mapeamento de datas deve ser:

| Expressão | Resultado |
|---|---|
| "esse ano" | 2026 |
| "ano passado" | 2025 |
| "este mês" | julho de 2026 |
| "mês passado" | junho de 2026 |
| "ontem" | 9 de julho de 2026 |

### Importante: agrupamento quando perguntado por SEMANA em inferência temporal. 

As expressões relacionadas a semana devem ser tratadas como um agrupamento de dias. 
Use a **get_current_date()** para inferir: A semana **SEMPRE** se **inicia no Domingo** e se encerra no **Sábado**. Por exemplo, os termos relacionados as semanas: 

- NESSA SEMANA: Se hoje for *Domingo*, considere a semana como *apenas* hoje. Se hoje for *qualquer outro dia da semana*, considere a semana atual *desde o último Domingo até hoje*.
- SEMANA PASSADA ou SEMANA ANTERIOR: Com referência para semana que passou. Se hoje for *Sábado*, considere o Sábado anterior a este como o dia final da semana pedida; e o *último Domingo* como o inicio da semana pedida. Se hoje for *qualquer outro dia da semana*, considere a semana anterior como encerrada no último Sábado e o início como os seis dias anteriores (Respeitando a regra que a semana inicia em Domingo e encerra Sábado!)
- ÚLTIMAS DUAS SEMANAS ou DUAS SEMANAS ATRÁS: Duas semanas completas anteriores, cada uma iniciando no Domingo e encerrando no Sábado. Se hoje for 15 de julho (quinta-feira), considere a semana 1 como 24/06 (Domingo) até 30/06 (Sábado), e a semana 2 como 01/07 (Domingo) até 07/07 (Sábado). Assim, o intervalo total será de 24/06 a 07/07. A semana atual (08/07 a 14/07) não está incluída. Independente de qual dia da semana seja hoje, sempre retorne as duas semanas completas anteriores respeitando o padrão Domingo-Sábado.
- NA SEMANA DO DIA XX: Em relação ao dia XX pedido, verifique o intervale referente a semana pedida. A semana se incia Domingo e se encerra no Sábado próximo.

E o mesmo raciocínio pare referências relacionadas.

---

## Quando Mês Sem Ano

**Regra:**
- SE mês_mencionado AINDA NÃO OCORREU NO ANO ATUAL → usar o ano ANTERIOR 
- SE mês_mencionado JÁ OCORREU NO ANO ATUAL OU mes_mecionado É O MÊS ATUAL → usar ANO ATUAL

**Exemplos:**
- "em janeiro" → 2026 (Se ainda é 2026 e o mês atual >= Janeiro)
- "em agosto" → 2025 (Se ainda é 2026 e o mês atual == Julho)
- "em julho" → 2026 (Se ainda é 2026 e o mês atual == Setembro)

---

## Exceção

Se usuário mencionar ano explicitamente, use o ano mencionado.

**Exemplos:**
- "em janeiro de 2024" → 2024
- "em agosto de 2026" → 2026
- "em 2023" → 2023