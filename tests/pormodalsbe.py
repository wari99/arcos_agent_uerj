import pandas as pd

df = pd.read_csv('/Users/path.csv', sep=';')

df['Qtd. Transações'] = df['Qtd. Transações'].astype(int)

resultado = df.groupby('Modal Operadora')['Qtd. Transações'].sum().sort_values(ascending=False)

print("Transações por Modal Operadora:\n")
for modal, total in resultado.items():
    print(f"{modal} - {total:,} transações")