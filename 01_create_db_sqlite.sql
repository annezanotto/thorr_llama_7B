PRAGMA foreign_keys = ON;

-- Drop (opcional)
DROP TABLE IF EXISTS PagamentosRealizados;
DROP TABLE IF EXISTS Parcelas;
DROP TABLE IF EXISTS Garantias;
DROP TABLE IF EXISTS Contratos;
DROP TABLE IF EXISTS ProdutosFinanciamento;
DROP TABLE IF EXISTS Clientes;

-- 1) Clientes
CREATE TABLE Clientes (
  cliente_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  nome            TEXT    NOT NULL,
  cpf             TEXT    NOT NULL UNIQUE,
  endereco        TEXT,
  telefone        TEXT,
  renda_mensal    REAL    NOT NULL CHECK (renda_mensal >= 0)
);

-- 2) ProdutosFinanciamento
CREATE TABLE ProdutosFinanciamento (
  produto_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  nome_produto     TEXT NOT NULL UNIQUE,            -- Veículo, Imóvel, Pessoal
  taxa_juros_base  REAL NOT NULL CHECK (taxa_juros_base >= 0),
  prazo_maximo     INTEGER NOT NULL CHECK (prazo_maximo > 0)
);

-- 3) Contratos
CREATE TABLE Contratos (
  contrato_id           INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id            INTEGER NOT NULL,
  produto_id            INTEGER NOT NULL,
  valor_total           REAL    NOT NULL CHECK (valor_total > 0),
  valor_entrada         REAL    NOT NULL CHECK (valor_entrada >= 0 AND valor_entrada <= valor_total),
  data_contratacao      TEXT    NOT NULL, -- ISO: YYYY-MM-DD
  taxa_juros_aplicada   REAL    NOT NULL CHECK (taxa_juros_aplicada >= 0),
  status                TEXT    NOT NULL CHECK (status IN ('Ativo','Pago','Inadimplente')),
  prazo_meses           INTEGER NOT NULL CHECK (prazo_meses > 0),
  sistema_amortizacao   TEXT    NOT NULL CHECK (sistema_amortizacao IN ('PRICE','SAC')),

  FOREIGN KEY (cliente_id) REFERENCES Clientes(cliente_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (produto_id) REFERENCES ProdutosFinanciamento(produto_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- 4) Parcelas
CREATE TABLE Parcelas (
  parcela_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  contrato_id       INTEGER NOT NULL,
  numero_parcela    INTEGER NOT NULL CHECK (numero_parcela > 0),
  data_vencimento   TEXT    NOT NULL, -- ISO: YYYY-MM-DD
  valor_parcela     REAL    NOT NULL CHECK (valor_parcela >= 0),
  valor_amortizacao REAL    NOT NULL CHECK (valor_amortizacao >= 0),
  valor_juros       REAL    NOT NULL CHECK (valor_juros >= 0),
  status_pagamento  TEXT    NOT NULL CHECK (status_pagamento IN ('Pendente','Pago')),

  FOREIGN KEY (contrato_id) REFERENCES Contratos(contrato_id) ON UPDATE CASCADE ON DELETE CASCADE,
  UNIQUE (contrato_id, numero_parcela)
);

-- 5) Garantias
CREATE TABLE Garantias (
  garantia_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  contrato_id     INTEGER NOT NULL UNIQUE,
  tipo_bem        TEXT    NOT NULL CHECK (tipo_bem IN ('Carro','Casa')),
  descricao_bem   TEXT,
  valor_avaliado  REAL    NOT NULL CHECK (valor_avaliado > 0),

  FOREIGN KEY (contrato_id) REFERENCES Contratos(contrato_id) ON UPDATE CASCADE ON DELETE CASCADE
);

-- 6) PagamentosRealizados
CREATE TABLE PagamentosRealizados (
  pagamento_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  parcela_id       INTEGER NOT NULL,
  data_pagamento   TEXT    NOT NULL, -- ISO: YYYY-MM-DD
  valor_pago       REAL    NOT NULL CHECK (valor_pago > 0),
  forma_pagamento  TEXT    NOT NULL,

  FOREIGN KEY (parcela_id) REFERENCES Parcelas(parcela_id) ON UPDATE CASCADE ON DELETE CASCADE
);

-- Índices úteis
CREATE INDEX idx_contratos_cliente   ON Contratos(cliente_id);
CREATE INDEX idx_contratos_produto   ON Contratos(produto_id);
CREATE INDEX idx_contratos_status    ON Contratos(status);

CREATE INDEX idx_parcelas_contrato   ON Parcelas(contrato_id);
CREATE INDEX idx_parcelas_vencimento ON Parcelas(data_vencimento);
CREATE INDEX idx_parcelas_status     ON Parcelas(status_pagamento);

CREATE INDEX idx_pagto_parcela       ON PagamentosRealizados(parcela_id);
CREATE INDEX idx_pagto_data          ON PagamentosRealizados(data_pagamento);
