import pandas as pd

"""
Nome: Teste de conversão .xlsx para um .csv LIMPO

Descrição: 
    Testar a limpeza de dicionários do tipo V1 a princípio. 
    Envio o Path do arquivo do dicionário e o path de onde quero salvar a versão limpa.
    Útil para poder recuperar informações de referência para arquivos das bases SBU, SBE, SGR.

Objetivo: Otimizar leitura dos arquivos de Dicionário V1
"""

path_input = r""
path_output = r""

def verificar_linhas_nao_vazias(linha):

    for valor in linha:
        texto = str(valor).strip()

        if texto != "":
            return True
        
    return False

df = pd.read_excel(path_input, sheet_name=0, header=None, dtype=str)
df = df.fillna("")
df = df[df.apply(verificar_linhas_nao_vazias, axis=1)]

df.to_csv(path_output, index=False, header=False, encoding="utf-8-sig")

print(f"Original em: {path_input} \nCsv corrigido: {path_output}")


