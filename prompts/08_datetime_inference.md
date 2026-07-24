# Inferência Temporal

---

## Referências Diretas

Utilize **get_current_date()** para mapear período temporal.

Caso a data obtida pela chamada da função seja referente, por exemplo, a 10 de Julho de 2026, o seu mapeamento de datas deve ser:

| Expressão | Resultado |
|---|---|
| "esse ano" | 2026 |
| "ano passado" | 2025 |
| "este mês" | julho de 2026 |
| "mês passado" | junho de 2026 |
| "ontem" | 9 de julho de 2026 |

---

## Quando Mês Sem Ano

**Regra:**
- SE mês_mencionado ≤ 7 (julho) → usar 2026
- SE mês_mencionado > 7 → usar 2025

**Exemplos:**
- "em janeiro" → 2026 (pois janeiro ≤ julho)
- "em agosto" → 2025 (pois agosto > julho)
- "em julho" → 2026 (pois julho ≤ julho)

---

## Exceção

Se usuário mencionar ano explicitamente, use o ano mencionado.

**Exemplos:**
- "em janeiro de 2024" → 2024
- "em agosto de 2026" → 2026
- "em 2023" → 2023