# Inferência Temporal

**Regra:** nunca infira data, dia da semana ou período sem chamar `get_current_date()`. Nunca presuma que um arquivo existe.

## Fluxo obrigatório
1. `get_current_date()` → data atual.
2. Nenhuma referência temporal na pergunta → perguntar ("Qual mês, dia ou intervalo?"). Referência parcial (mês sem ano, dia sem mês) → completar pelas regras abaixo.
3. Calcular datas absolutas pelas regras abaixo.
4. Montar o filtro: mensal → `consolidado_YYYY_MM`; diário → `publico_YYYY_MM_DD`.
5. `listar_recursos_da_base(package_id, termo_busca=filtro)`. Confirmar existência por `recursos_encontrados` e percorrer as páginas até `tem_proxima_pagina = false`.
6. Existe → `baixar_arquivo_dados`. Não existe → não dar número; informar "Busquei na base X com filtro Y e não encontrei o período Z", listar os períodos disponíveis (`listar_recursos_da_base` com termo mais amplo, ex: `consolidado_2026`, percorrendo todas as páginas) e perguntar qual usar.7. Intervalos (semanas, vários meses): verificar cada dia ou mês, uma chamada por arquivo. Informar os ausentes antes de agregar.

## Regras de cálculo (exemplo: hoje = quarta, 15/07/2026)
| Expressão | Resultado |
|---|---|
| este ano / ano passado | 2026 / 2025 |
| este mês / mês passado | 07/2026 / 06/2026 |
| hoje | 15/07/2026 (o arquivo do dia pode ainda não existir; verificar) |
| ontem | 14/07/2026 |
| esta semana | último domingo até hoje (12/07 a 15/07); se hoje for domingo, só hoje |
| semana passada | domingo a sábado anteriores à semana atual (05/07 a 11/07) |
| últimas duas semanas | duas semanas completas anteriores (28/06 a 11/07) |
| semana do dia XX | domingo a sábado que contém XX (20/07 → 19/07 a 25/07) |
| mês sem ano | já ocorreu no ano ou é o atual → ano atual; ainda não ocorreu → ano anterior (agosto → 2025) |
| dia sem mês | dia já passou no mês atual → mês atual; ainda não → mês anterior (dia 20 → 20/06/2026) |
| ano explícito | usar o ano informado |

Semanas vão de domingo a sábado. A semana em andamento nunca entra em "semana passada" ou "últimas duas semanas". Não existe arquivo semanal.

## Validação
- Dia inválido (ex: 30/02) → informar e sugerir a data correta.
- Data futura → informar e indicar a data máxima disponível.
- Na resposta, citar período, base e tipo de arquivo.