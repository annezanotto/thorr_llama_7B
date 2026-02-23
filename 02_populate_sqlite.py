# Gera produtos: Veículo, Imóvel, Pessoal.
# Gera clientes e 1000 contratos.
# Respeita: máximo 15 contratos ativos por cliente e “na maioria” 1–2 contratos por cliente (distribuição enviesada).
# Gera parcelas (PRICE ou SAC) e pagamentos (com casos pagos, pendentes e atraso → inadimplência).
# Gera garantias apenas para Veículo e Imóvel (Pessoal não).
# Execute: python 02_populate_sqlite.py (cria financiamento.db na mesma pasta).

import sqlite3
import random
import math
from datetime import date, timedelta

DB_PATH = "financiamento.db"
CREATE_SQL_PATH = "01_create_db_sqlite.sql"

random.seed(42)

# ---------- Helpers ----------
def iso(d: date) -> str:
    return d.isoformat()

def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 0)))

def gen_cpf(i: int) -> str:
    # CPF fictício (11 dígitos) - apenas para dados sintéticos
    return str(10000000000 + i)

def pick_weighted(weights):
    # weights: list of (value, weight)
    total = sum(w for _, w in weights)
    r = random.uniform(0, total)
    upto = 0.0
    for v, w in weights:
        upto += w
        if upto >= r:
            return v
    return weights[-1][0]

def money(x: float) -> float:
    # arredonda para centavos
    return round(x + 1e-9, 2)

# ---------- Amortização ----------
def schedule_price(principal, monthly_rate, n):
    # Prestação constante (Price)
    if monthly_rate == 0:
        pmt = principal / n
    else:
        pmt = principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)

    bal = principal
    out = []
    for k in range(1, n + 1):
        juros = bal * monthly_rate
        amort = pmt - juros
        # ajuste última parcela por arredondamento
        if k == n:
            amort = bal
            pmt = amort + juros
        bal -= amort
        out.append((money(pmt), money(amort), money(juros)))
    return out

def schedule_sac(principal, monthly_rate, n):
    # Amortização constante (SAC)
    amort_const = principal / n
    bal = principal
    out = []
    for k in range(1, n + 1):
        juros = bal * monthly_rate
        pmt = amort_const + juros
        if k == n:
            amort = bal
            pmt = amort + juros
        else:
            amort = amort_const
        bal -= amort
        out.append((money(pmt), money(amort), money(juros)))
    return out

# ---------- Main ----------
def main():
    # Conecta
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON;")
    cur = con.cursor()

    # Cria schema
    with open(CREATE_SQL_PATH, "r", encoding="utf-8") as f:
        cur.executescript(f.read())
    con.commit()

    # Insere produtos
    produtos = [
        ("Veículo", 0.018, 60),  # ~1.8% a.m.
        ("Imóvel",  0.010, 360), # ~1.0% a.m.
        ("Pessoal", 0.028, 48),  # ~2.8% a.m.
    ]
    cur.executemany(
        "INSERT INTO ProdutosFinanciamento (nome_produto, taxa_juros_base, prazo_maximo) VALUES (?,?,?)",
        produtos
    )
    con.commit()

    # Busca ids de produtos
    cur.execute("SELECT produto_id, nome_produto, taxa_juros_base, prazo_maximo FROM ProdutosFinanciamento")
    prod_rows = cur.fetchall()
    prod_by_name = {r[1]: {"produto_id": r[0], "taxa": r[2], "prazo_max": r[3]} for r in prod_rows}

    # Queremos 1000 contratos com maioria de clientes tendo 1-2 contratos
    # Estratégia:
    # - cria um pool de clientes com “capacidade de contratos” enviesada: muitos com 1-2, poucos com 3-15.
    # - depois aloca 1000 contratos respeitando <= 15 ATIVOS por cliente (e total também não explode).
    target_contracts = 1000

    # Distribuição do total de contratos por cliente (intencionalmente enviesada)
    # (valor, peso)
    contracts_per_client_dist = [
        (1, 55),
        (2, 25),
        (3, 8),
        (4, 4),
        (5, 3),
        (6, 2),
        (7, 1.2),
        (8, 0.8),
        (9, 0.5),
        (10, 0.3),
        (12, 0.15),
        (15, 0.05),
    ]

    planned = []
    total = 0
    while total < target_contracts:
        c = pick_weighted(contracts_per_client_dist)
        planned.append(c)
        total += c

    # Ajuste para bater exatamente 1000
    while total > target_contracts:
        i = random.randrange(len(planned))
        if planned[i] > 1:
            planned[i] -= 1
            total -= 1

    num_clients = len(planned)

    # Gera clientes
    first_names = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela", "João",
                   "Karen", "Luiz", "Marina", "Nicolas", "Otávio", "Paula", "Rafael", "Sofia", "Tiago", "Vitória"]
    last_names = ["Silva", "Souza", "Oliveira", "Pereira", "Lima", "Gomes", "Ribeiro", "Alves", "Fernandes", "Carvalho"]

    clients = []
    for i in range(1, num_clients + 1):
        nome = f"{random.choice(first_names)} {random.choice(last_names)}"
        cpf = gen_cpf(i)
        endereco = f"Rua {random.choice(last_names)}, {random.randint(10, 9999)}"
        telefone = f"+55 51 9{random.randint(1000,9999)}-{random.randint(1000,9999)}"
        renda = money(random.uniform(1800, 25000))
        clients.append((nome, cpf, endereco, telefone, renda))

    cur.executemany(
        "INSERT INTO Clientes (nome, cpf, endereco, telefone, renda_mensal) VALUES (?,?,?,?,?)",
        clients
    )
    con.commit()

    # Mapa cliente_id
    cur.execute("SELECT cliente_id FROM Clientes ORDER BY cliente_id")
    cliente_ids = [r[0] for r in cur.fetchall()]

    # Para cada cliente, cria planned[i] contratos.
    # Regra: no máximo 15 contratos ATIVOS por cliente.
    # Vamos marcar alguns como Pago/Inadimplente, então ATIVOS por cliente tende a ficar <= total.
    today = date.today()
    start_date = today - timedelta(days=365 * 4)  # últimos 4 anos

    contratos_insert = []
    # guardamos para depois gerar parcelas/pagamentos/garantias
    contratos_meta = []  # (contrato_id, cliente_id, produto_nome, principal, taxa_mensal, n, data_contrat, status, sistema)

    # Primeiro inserimos contratos (sem parcelas)
    for idx, cliente_id in enumerate(cliente_ids):
        qtd = planned[idx]

        # prob. de status por contrato (global)
        # maioria ativos, alguns pagos, poucos inadimplentes
        status_weights = [("Ativo", 70), ("Pago", 25), ("Inadimplente", 5)]

        # controle de ativos por cliente
        ativos_count = 0

        for _ in range(qtd):
            produto_nome = pick_weighted([("Veículo", 45), ("Imóvel", 20), ("Pessoal", 35)])
            p = prod_by_name[produto_nome]
            taxa_base = p["taxa"]
            prazo_max = p["prazo_max"]

            # taxa aplicada: base +/- variação
            taxa_aplicada = max(0.0, random.gauss(taxa_base, taxa_base * 0.12))

            # valor e entrada
            if produto_nome == "Imóvel":
                valor_total = random.uniform(120000, 1500000)
                entrada = valor_total * random.uniform(0.05, 0.35)
                prazo = random.randint(60, min(360, prazo_max))
            elif produto_nome == "Veículo":
                valor_total = random.uniform(35000, 250000)
                entrada = valor_total * random.uniform(0.05, 0.40)
                prazo = random.randint(12, min(60, prazo_max))
            else:  # Pessoal
                valor_total = random.uniform(2000, 80000)
                entrada = valor_total * random.uniform(0.0, 0.10)
                prazo = random.randint(6, min(48, prazo_max))

            valor_total = money(valor_total)
            entrada = money(entrada)
            principal = money(valor_total - entrada)

            data_contrat = rand_date(start_date, today)

            sistema = pick_weighted([("PRICE", 65), ("SAC", 35)])

            # define status com ajuste para garantir <=15 ativos
            status = pick_weighted(status_weights)
            if status == "Ativo":
                ativos_count += 1
                if ativos_count > 15:
                    # força não ativo
                    status = pick_weighted([("Pago", 80), ("Inadimplente", 20)])
                    ativos_count -= 1

            contratos_insert.append((
                cliente_id,
                p["produto_id"],
                valor_total,
                entrada,
                iso(data_contrat),
                money(taxa_aplicada),
                status,
                prazo,
                sistema
            ))

    cur.executemany(
        """
        INSERT INTO Contratos
          (cliente_id, produto_id, valor_total, valor_entrada, data_contratacao,
           taxa_juros_aplicada, status, prazo_meses, sistema_amortizacao)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        contratos_insert
    )
    con.commit()

    # Recupera contratos inseridos com dados para gerar parcelas
    cur.execute("""
        SELECT c.contrato_id, c.cliente_id, p.nome_produto, c.valor_total, c.valor_entrada,
               c.taxa_juros_aplicada, c.prazo_meses, c.data_contratacao, c.status, c.sistema_amortizacao
        FROM Contratos c
        JOIN ProdutosFinanciamento p ON p.produto_id = c.produto_id
        ORDER BY c.contrato_id
    """)
    all_contracts = cur.fetchall()

    parcelas_insert = []
    pagamentos_insert = []
    garantias_insert = []

    for (contrato_id, cliente_id, prod_nome, valor_total, valor_entrada,
         taxa_mensal, n, data_contrat_str, status, sistema) in all_contracts:

        principal = float(valor_total) - float(valor_entrada)
        monthly_rate = float(taxa_mensal)

        # cronograma
        if sistema == "PRICE":
            sched = schedule_price(principal, monthly_rate, int(n))
        else:
            sched = schedule_sac(principal, monthly_rate, int(n))

        data_contrat = date.fromisoformat(data_contrat_str)

        # Define quantas parcelas já “passaram” no tempo (para decidir pagos/pendentes/inadimplência)
        # Considera 1ª parcela 30 dias após contratação.
        first_due = data_contrat + timedelta(days=30)
        # número de vencimentos que já ocorreram
        months_passed = max(0, (today.year - first_due.year) * 12 + (today.month - first_due.month))
        months_passed = min(months_passed + 1, int(n))  # +1 para incluir mês corrente

        # Decide comportamento:
        # - Pago: tudo pago
        # - Ativo: uma fração paga, resto pendente
        # - Inadimplente: algumas vencidas ficam pendentes (sem pagamento) para caracterizar atraso
        if status == "Pago":
            paid_up_to = int(n)
            delinquent_from = None
        elif status == "Ativo":
            paid_up_to = random.randint(max(0, months_passed - 6), months_passed)  # pode estar em dia ou levemente atrás
            delinquent_from = None
        else:  # Inadimplente
            # deixa algumas vencidas sem pagar
            paid_up_to = max(0, months_passed - random.randint(2, 8))
            delinquent_from = paid_up_to + 1

        # Gera parcelas e pagamentos (pagamento somente se parcela status = Pago)
        for k in range(1, int(n) + 1):
            due_date = first_due + timedelta(days=30 * (k - 1))
            (valor_parcela, valor_amort, valor_juros) = sched[k - 1]

            if status == "Pago":
                st = "Pago"
            elif status == "Ativo":
                st = "Pago" if k <= paid_up_to else "Pendente"
            else:  # Inadimplente
                if k <= paid_up_to:
                    st = "Pago"
                else:
                    # se já venceu, fica pendente; se ainda não venceu, pendente também
                    st = "Pendente"

            parcelas_insert.append((
                contrato_id, k, iso(due_date),
                valor_parcela, valor_amort, valor_juros, st
            ))

    # Inserir parcelas primeiro
    cur.executemany("""
        INSERT INTO Parcelas
          (contrato_id, numero_parcela, data_vencimento, valor_parcela, valor_amortizacao, valor_juros, status_pagamento)
        VALUES (?,?,?,?,?,?,?)
    """, parcelas_insert)
    con.commit()

    # Agora cria pagamentos para parcelas pagas
    # (um pagamento por parcela paga; valor_pago pode ser igual ao valor_parcela com pequena variação)
    cur.execute("""
        SELECT parcela_id, data_vencimento, valor_parcela, status_pagamento
        FROM Parcelas
    """)
    parcelas_rows = cur.fetchall()

    formas = ["PIX", "Boleto", "Débito", "TED", "Cartão"]
    for (parcela_id, venc_str, valor_parcela, st) in parcelas_rows:
        if st != "Pago":
            continue
        venc = date.fromisoformat(venc_str)
        # paga perto do vencimento (antes ou poucos dias depois)
        pay_date = venc + timedelta(days=random.randint(-3, 5))
        # valor pago ~ valor parcela (pode ter centavos de diferença)
        valor_pago = money(float(valor_parcela) * random.uniform(0.999, 1.001))
        pagamentos_insert.append((parcela_id, iso(pay_date), valor_pago, random.choice(formas)))

    cur.executemany("""
        INSERT INTO PagamentosRealizados (parcela_id, data_pagamento, valor_pago, forma_pagamento)
        VALUES (?,?,?,?)
    """, pagamentos_insert)
    con.commit()

    # Garantias: para Veículo e Imóvel (1 por contrato)
    cur.execute("""
        SELECT c.contrato_id, p.nome_produto, c.valor_total
        FROM Contratos c
        JOIN ProdutosFinanciamento p ON p.produto_id = c.produto_id
    """)
    for contrato_id, prod_nome, valor_total in cur.fetchall():
        if prod_nome == "Pessoal":
            continue
        if prod_nome == "Veículo":
            tipo_bem = "Carro"
            desc = f"Veículo {random.choice(['Sedan','SUV','Hatch','Pickup'])} - ano {random.randint(2010, 2025)}"
            aval = money(float(valor_total) * random.uniform(0.60, 1.05))
        else:
            tipo_bem = "Casa"
            desc = f"Imóvel {random.choice(['Casa','Apartamento'])} - {random.randint(40, 250)} m²"
            aval = money(float(valor_total) * random.uniform(0.70, 1.10))
        garantias_insert.append((contrato_id, tipo_bem, desc, aval))

    cur.executemany("""
        INSERT INTO Garantias (contrato_id, tipo_bem, descricao_bem, valor_avaliado)
        VALUES (?,?,?,?)
    """, garantias_insert)
    con.commit()

    # Checagens rápidas
    cur.execute("SELECT COUNT(*) FROM Contratos")
    print("Contratos:", cur.fetchone()[0])

    cur.execute("""
        SELECT MAX(cnt) FROM (
          SELECT cliente_id, SUM(CASE WHEN status='Ativo' THEN 1 ELSE 0 END) AS cnt
          FROM Contratos
          GROUP BY cliente_id
        )
    """)
    print("Máx. contratos ATIVOS por cliente:", cur.fetchone()[0])

    cur.execute("""
        SELECT
          SUM(CASE WHEN status='Ativo' THEN 1 ELSE 0 END) AS ativos,
          SUM(CASE WHEN status='Pago' THEN 1 ELSE 0 END) AS pagos,
          SUM(CASE WHEN status='Inadimplente' THEN 1 ELSE 0 END) AS inad
        FROM Contratos
    """)
    print("Status (Ativo/Pago/Inad):", cur.fetchone())

    con.close()
    print("OK. Banco gerado em:", DB_PATH)

if __name__ == "__main__":
    main()

