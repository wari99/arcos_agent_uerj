import sys

"""
Nome: Teste de turnos

Descrição: 
    Arquivo para testar a separação de turnos com horários específicos, incluindo casos críticos,
    que são os horários de transição entre turnos.

    Passando via linha de comando é possível testar um horário custom, por exemplo:
        > python3 turnos_test.py 0403 -> Testará filtro de turno para o horário 04:03
        > python3 turnos_test.py 1111 -> Testará filtro de turno para o horário 11:11

Objetivo: Garantir que a função de separação de turnos esteja funcionando corretamente para todos os horários possíveis, como foco os pertencentes aos limites.
"""

def determinar_faixa_horaria(hora: int, minuto: int = 0) -> int:
    """
    Separação de um horário obtido através de um datetime e descoberta do seu turno

    Parâmetros:
        hora: Hora do dia (0-23)
        minuto: Minuto da hora (0-59)
    
    Retorno:
        Valor inteiro representando o turno.
        0 - Madrugada (00:01 até 06:00)
        1 - Manhã (06:01 até 12:00)
        2 - Tarde (12:01 até 18:00)
        3 - Noite (18:01 até 00:00)
    """
    minutos_totais = hora * 60 + minuto
    
    if minutos_totais == 0:
        return 3 
    elif 1 <= minutos_totais <= 360:
        return 0
    elif 361 <= minutos_totais <= 720:
        return 1
    elif 721 <= minutos_totais <= 1080:
        return 2
    else:
        return 3

NOMES_TURNOS = ["Madrugada", "Manhã", "Tarde", "Noite"]


def testar_horario_custom(horario_str: str):                        
    """                                                                   
    Testa um horário específico fornecido como parâmetro                 
                                                                          
    Parâmetro: horario_str no formato HHMM (ex: "0403", "1530", "2359") 
    """                                                                   
    if len(horario_str) != 4 or not horario_str.isdigit():              
        print(f"❌ Formato inválido: '{horario_str}'")                    
        print("   Use formato HHMM (ex: 0403, 1530, 2359)")              
        sys.exit(1)                                                       
                                                                          
    try:                                                                  
        hora = int(horario_str[:2])                                     
        minuto = int(horario_str[2:])                                   
                                                                          
        if hora < 0 or hora > 23:                                        
            raise ValueError(f"Hora deve estar entre 00 e 23, obteve: {hora}") 
        if minuto < 0 or minuto > 59:                                    
            raise ValueError(f"Minuto deve estar entre 00 e 59, obteve: {minuto}") 
                                                                          
    except ValueError as e:                                              
        print(f"❌ Erro ao processar horário: {e}")                       
        sys.exit(1)
    
    turno_obtido = determinar_faixa_horaria(hora, minuto)
    nome_obtido = NOMES_TURNOS[turno_obtido]
    horario_formatado = f"{hora:02d}:{minuto:02d}"
    
    definicoes = {
        0: "Madrugada (00:01 até 06:00)",
        1: "Manhã (06:01 até 12:00)",
        2: "Tarde (12:01 até 18:00)",
        3: "Noite (18:01 até 00:00)"
    }
    
    print(f"\n⏰ Horário testado: {horario_formatado}")
    print(f" * Turno: {turno_obtido} - {nome_obtido} ({definicoes[turno_obtido]})")

if len(sys.argv) > 1:
    testar_horario_custom(sys.argv[1])

print(f"\nTESTE COM HORÁRIOS ESPECÍFICOS - CASOS CRÍTICOS\n")

CASOS_TESTE = [ 
    # MADRUGADA: 00:01 até 06:00
    (0, 0, "00:00", 3, "Noite", "Meia-noite exata"),
    (0, 1, "00:01", 0, "Madrugada", "1o minuto da madrugada"),
    (1, 0, "01:00", 0, "Madrugada", "1 da manhã"),
    (5, 59, "05:59", 0, "Madrugada", "Último minuto da madrugada"),
    (6, 0, "06:00", 0, "Madrugada", "Última hora da madrugada"),
    
    # TRANSIÇÃO MADRUGADA -> MANHÃ
    (6, 1, "06:01", 1, "Manhã", "CRÍTICO: 1o minuto minuto da manhã"),
    (6, 30, "06:30", 1, "Manhã", "Meio da transição"),
    (6, 59, "06:59", 1, "Manhã", "Último minuto antes de 07:00"),
    
    # MANHÃ: 06:01 até 12:00
    (7, 0, "07:00", 1, "Manhã", "Início da manhã"),
    (9, 30, "09:30", 1, "Manhã", "Meio da manhã"),
    (12, 0, "12:00", 1, "Manhã", "Último minuto da manhã"),
    
    # TRANSIÇÃO MANHÃ -> TARDE
    (12, 1, "12:01", 2, "Tarde", "CRÍTICO: 1o minuto minuto da tarde"),
    (12, 30, "12:30", 2, "Tarde", "Transição ao meio-dia"),
    (12, 59, "12:59", 2, "Tarde", "Último minuto antes de 13:00"),
    
    # TARDE: 12:01 até 18:00
    (13, 0, "13:00", 2, "Tarde", "Início da tarde"),
    (15, 30, "15:30", 2, "Tarde", "Meio da tarde"),
    (18, 0, "18:00", 2, "Tarde", "Último minuto da tarde"),
    
    # TRANSIÇÃO TARDE -> NOITE
    (18, 1, "18:01", 3, "Noite", "CRÍTICO: 1o minuto minuto da noite"),
    (18, 30, "18:30", 3, "Noite", "Transição ao entardecer"),
    (18, 59, "18:59", 3, "Noite", "Último minuto antes de 19:00"),
    
    # NOITE: 18:01 até 00:00
    (19, 0, "19:00", 3, "Noite", "Início da noite"),
    (21, 30, "21:30", 3, "Noite", "Meio da noite"),
    (23, 59, "23:59", 3, "Noite", "Último minuto do dia"),
]

print("RELAÇÃO DOS TESTES:\n")
print(f"{'Horário':>8} | {'Obtido':^12} | {'Esperado':^12} | Status | Descrição")
print("-"*10)

erros = []
for hora, minuto, horario_str, turno_esperado, nome_esperado, descricao in CASOS_TESTE:
    turno_obtido = determinar_faixa_horaria(hora, minuto)
    nome_obtido = NOMES_TURNOS[turno_obtido]
    
    status = "✅" if turno_obtido == turno_esperado else "❌ ERRO"
    
    print(f"{horario_str:>8} | {nome_obtido:^12} | {nome_esperado:^12} | {status:^6} | {descricao}")
    
    if turno_obtido != turno_esperado:
        erros.append({
            "horario": horario_str,
            "obtido": nome_obtido,
            "esperado": nome_esperado,
            "descricao": descricao
        })

if erros:
    print(f"\n🚨 {len(erros)} ERRO(S) ENCONTRADO(S):\n")
    for i, erro in enumerate(erros, 1):
        print(f"{i}. ❌ {erro['horario']}")
        print(f"   Obtém:   '{erro['obtido']}'")
        print(f"   Deveria: '{erro['esperado']}'")
        print(f"   Motivo:  {erro['descricao']}\n")
    print("RESULTADO: ⚠️ A FUNÇÃO DE SEPARAÇÃO DE TURNOS NÃO ESTÁ FUNCIONANDO CORRETAMENTE")
else:
    print("\nRESULTADO: ✅ TODOS OS TESTES PASSARAM!")
