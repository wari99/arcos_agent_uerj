# Mapeamento de Sinônimos

---

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

## Linhas de Ônibus

**Formato:** "CÓDIGO - PONTO_A - PONTO_B"

**Exemplos:**
- "128003 - S. JOÃO - CAXIAS (MATADOURO)"
- "434L - NOVA IGUAÇU - TAQUARA"