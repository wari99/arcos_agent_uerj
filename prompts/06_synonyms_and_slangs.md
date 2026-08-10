# Mapeamento de Sinônimos

## Bases de Dados

| Sinônimos | Base |
|---|---|
| gratuidade, idoso, estudante, PCD, transação gratuita | `setram_sgr` |
| bilhete único, BU, integração, cartão BU | `setram_sbu` |
| bilhetagem, validação, embarque, passageiro | `setram_sbe` |
| tarifa, preço, passagem do metrô | `concessionaria-metrorio` |
| tarifa, preço, passagem da barca | `concessionaria-ccr-barcas` |
| tarifa, preço, passagem do trem, supervia | `concessionaria-supervia` |

---

## Modais de Transporte

| Sinônimos | Modal Operadora |
|---|---|
| ônibus, onibus, busão, bus, coletivo | `ÔNIBUS` |
| metrô, metro | `METRÔ` |
| trem, trens, supervia | `TRENS` |
| barca, barcas | `BARCAS` |
| van, vans, perua, kombi | `VANS` |

---

## Tipos de Gratuidade

| Sinônimos | Tipo |
|---|---|
| idoso, coroa, senior, terceira idade | `Idoso` |
| estudante, aluno, brisolão, CIEP | `Estudante` ⚠️ No DIÁRIO: agregar 4 códigos |
| deficiente, PCD | `Deficiente` |

---

## Tipo de Operação

| Sinônimos | Operação |
|---|---|
| quantos, total, soma | `agrupar_e_somar` |
| quantas linhas, quantas vezes | `contar_por_valor` |
| de manhã, à tarde, à noite | `filtrar_por_turno` ou `contar_por_turno` |
| gráfico, visualizar, mostra | `gerar_graficos` |
| comparar, vs, versus | `gerar_graficos` (tipo: comparacao) |

---

## Linhas - Linhas de Ônibus

**Formato:** `CÓDIGO [+ LETRA] - TRAJETO`

**Estrutura:**
- **Identificador:** Números (1-7 dígitos) + opcionalmente LETRA (A-Z)
- **Trajeto:** Nome dos pontos separados por hífen (ex: ORIGEM - DESTINO)

**Exemplos:**
- `740D - CHARITAS - LEBLON` (código 740, letra D)
- `809 - CHARITAS - LEME URB` (código 809, sem letra)
- `434L - NOVA IGUAÇU - TAQUARA` (código 434, letra L)
- `128038 - NOVA AURORA - MADUREIRA` (código 128038, sem letra)

### IMPORTANTE — Busca Flexível

O usuário pode citar:
- Linha completa: `"434L - NOVA IGUAÇU - TAQUARA"`
- Apenas código com letra: `"434L"`
- Apenas código (sem letra): `"434"` → buscar `434L` ou `434` mais próximo (Ou perguntar ao usuário qual é a preferência se existir mais uma linha)
- Apenas trajeto: `"TAQUARA"` → localizar qual linha que possui trajeto TAQUARA

**Estratégia:**
1. Tentar match exato (ex: `434L`)
2. Se falhar, buscar código sem letra (ex: `434`)
3. Se falhar, buscar trajeto (ex: buscar `TAQUARA` em qualquer linha)
4. Retornar melhor correspondência encontrada

---

## Linhas de Metrô

**Formato:** `L[NÚMERO] [SIGLA] - Estação [NOME_ESTAÇÃO]`

**Estrutura:**
- **L[NÚMERO]:** Identificador da linha (L1, L2, L4, etc.)
- **[SIGLA]:** Abreviação em 2-3 letras (LMC = Largo do Machado, NSP = Nossa Senhora da Paz)
- **NOME_ESTAÇÃO:** Nome completo da estação

**Exemplos:**
- `L1 LMC - Estação Largo do Machado` (Linha 1, estação Largo do Machado)
- `L4 NSP - Estação Nossa Senhora da Paz` (Linha 4, estação Nossa Senhora da Paz)

#### IMPORTANTE — Busca Flexível

O usuário pode citar:
- Nome da estação e Modal (mais comum): `"Metro Largo do Machado"` ou `"Metro Lgo do Machado"` → localizar qual linha passa lá pelo seu nome oficial
- Apenas nome da estação: `"Largo do Machado"` → localizar qual linha passa lá
- Linha completa (menos comum): `"L1 LMC - Estação Largo do Machado"`
- Apenas número de linha: `"L1"` ou `"Linha 1"`
- Apenas sigla: `"LMC"` → buscar estação correspondente

**Estratégia:**
1. Tentar match exato (ex: `L1 LMC`)
2. Se falhar, buscar por número de linha (ex: `L1`)
3. Se falhar, buscar por nome de estação (busca parcial em NOME_ESTAÇÃO)
4. Se falhar, buscar por sigla (match em [SIGLA])
5. Retornar melhor correspondência encontrada