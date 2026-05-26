> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Armazenamento de Banco de Dados e Migrações

Este diretório gerencia a camada de persistência de dados da aplicação de coach do Counter-Strike. Ele utiliza SQLAlchemy como Object-Relational Mapper (ORM) e Alembic para uma gestão robusta da evolução do esquema do banco de dados e migrações.

## Visão Geral Técnica

O motor de armazenamento foi projetado para garantir a integridade dos dados e a consistência do esquema em diferentes ambientes de implantação. Ao usar o Alembic, o sistema mantém um histórico linear de alterações no banco de dados, permitindo atualizações e rollbacks sem interrupções. O esquema é otimizado para consultas de alto desempenho em estatísticas de partidas, métricas de desempenho de jogadores e metadados táticos.

## Componentes Principais

### Migrações Alembic
O subdiretório **`migrations/`** contém a lógica para a evolução do banco de dados:
- **`env.py`**: O ponto de entrada para o ambiente Alembic, configurando a conexão com o banco de dados e o contexto da migração.
- **`script.py.mako`**: Um arquivo de template usado pelo Alembic para gerar novos scripts de migração.
- **`versions/`**: Uma coleção de scripts de migração incrementais.
    - **`b609a11e13cc_baseline_schema.py`**: Estabelece as tabelas iniciais (Jogadores, Partidas, Rodadas, etc.).
    - **`5d5764ef9f26_add_rating_components.py`**: Um exemplo de atualização incremental que adiciona campos complexos de cálculo de rating ao banco de dados.

## Estrutura do Diretório

```text
backend/storage/
├── migrations/             # Motor de migração Alembic
│   ├── env.py              # Configuração do ambiente
│   ├── script.py.mako      # Template de script de migração
│   └── versions/           # Versões incrementais do esquema
├── README.md               # Documentação em inglês
├── README_IT.md            # Versão em italiano
└── README_PT.md            # Esta documentação
```

## Uso

### Aplicando Migrações
Para atualizar o banco de dados para a versão mais recente, execute o seguinte comando a partir da raiz do projeto:
```bash
alembic upgrade head
```

### Criando uma Nova Migração
Quando os modelos SQLAlchemy no backend forem atualizados, gere um novo script de migração usando:
```bash
alembic revision --autogenerate -m "descrição das mudanças"
```

### Rollbacks
Para reverter para uma versão anterior:
```bash
alembic downgrade -1
```

Os parâmetros de conexão do banco de dados são normalmente carregados de variáveis de ambiente ou do arquivo central `settings.json`.
