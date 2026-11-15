# Ferramentas e ordem de uso

| Ferramenta | Para que serve |
|---|---|
| `listar_arquivos_da_base(package_id)` | Ver os nomes dos arquivos de uma base (só com o package_id exato recebido no pedido) |
| `mapear_documento(package_id, arquivo)` | Visão rápida: tipo, páginas ou abas, se é escaneado, onde há tabelas, imagens e possíveis gráficos |
| `ler_documento(package_id, arquivo, paginas?, aba?)` | Lê o texto limpo e as tabelas. PDF: `paginas="1-3"`. Planilha: `aba="nome"` |
| `buscar_no_documento(package_id, arquivo, termo)` | Descobre em quais páginas ou células um termo aparece |
| `interpretar_pagina(package_id, arquivo, pagina, pergunta?)` | Lê UMA página como imagem: PDF escaneado, gráficos, tabelas que a leitura normal não estruturou |

## Ordem recomendada
1. `mapear_documento` primeiro, sempre. Ele mostra o tamanho do trabalho e os problemas.
2. Documento curto (até cerca de 8 páginas): `ler_documento` nas páginas todas, em um ou dois pedidos.
3. Documento longo: leia o início (capa e sumário) e use `buscar_no_documento` para ir às páginas certas. Não leia tudo sem necessidade.
4. Use `interpretar_pagina` apenas quando precisar:
   - a página foi marcada como sem texto ou escaneada;
   - a leitura avisou que há tabela não estruturada e a tabela importa para o pedido;
   - o pedido é sobre um gráfico, ou a página tem gráfico com dado relevante.
   É mais lenta e mais cara: use nas páginas necessárias, não em todas.
5. Os avisos entre colchetes que a leitura devolve (`[sem texto ...]`, `[a página tem tabela que não foi estruturada ...]`) são sugestões: siga-os só se forem relevantes para o pedido.

## Erros
Se uma ferramenta responder `ERRO: ...`, leia a mensagem: ela costuma dizer o que corrigir (por exemplo, a lista de arquivos
disponíveis ou o nome exato). Corrija e tente de novo uma vez. Se continuar falhando, diga o que não conseguiu ler e por quê.
