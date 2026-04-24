# Contribuindo para o Macena CS2 Analyzer

Obrigado pelo seu interesse em contribuir. Este documento descreve como
propor alteracoes, os padroes que seu codigo deve atender e o processo de revisao.

> **[English](CONTRIBUTING.md)** | **[Italiano](CONTRIBUTING_IT.md)** | **[Portugues](CONTRIBUTING_PT.md)**

## Licenca

Ao enviar um pull request, voce concorda que sua contribuicao e licenciada sob
a mesma dupla licenca do projeto (Proprietaria / Apache 2.0). Veja [LICENSE](LICENSE).

## Primeiros Passos

```bash
# 1. Faca fork e clone o repositorio
git clone https://github.com/<seu-fork>/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI-main

# 2. Crie e ative um ambiente virtual (Python 3.10+)
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# 3. Instale as dependencias
pip install -r requirements.txt

# 4. Instale os hooks de pre-commit
pre-commit install

# 5. Verifique que tudo funciona
python tools/headless_validator.py   # Deve retornar exit 0
python -m pytest Programma_CS2_RENAN/tests/ tests/ --tb=short
```

## Processo de Pull Request

1. **Crie um branch a partir de `main`** — nomeie seu branch como `feature/<topico>` ou `fix/<topico>`.
2. **Uma alteracao logica por commit** — mantenha commits atomicos e significativos.
3. **Todos os hooks de pre-commit devem passar** — `pre-commit run --all-files`.
4. **Todos os testes devem passar** — `python -m pytest Programma_CS2_RENAN/tests/ tests/`.
5. **O headless validator deve passar** — `python tools/headless_validator.py` (exit 0).
6. **A cobertura nao deve diminuir** — o limiar atual e 40%, aumentando incrementalmente.
7. **Abra um PR para `main`** com uma descricao clara do que e por que.

## Padroes de Codigo

- **Python 3.10+** com type hints nas interfaces publicas.
- **Black** formatter (comprimento de linha 100). **isort** para ordenacao de imports.
- **Sem numeros magicos** — extrair para constantes nomeadas ou config.
- **Logging estruturado** via `get_logger("cs2analyzer.<modulo>")`.
- **Sem falhas silenciosas** — erros devem emergir imediata e explicitamente.
- **Cada tick e sagrado** — decimacao de ticks e estritamente proibida.
- Docstrings apenas onde a logica nao e obvia. Sem documentacao boilerplate.

## Mensagens de Commit

- Use mensagens semanticas no modo imperativo (ex. "Fix stale checkpoint handling").
- Mantenha a primeira linha abaixo de 72 caracteres.
- Referencie numeros de issues quando aplicavel (`Fixes #42`).

## O Que Aceitamos

- Correcoes de bugs com testes comprovando a correcao.
- Melhorias de desempenho com benchmarks.
- Novas funcionalidades alinhadas com a visao do projeto (coaching IA para jogadores de CS2).
- Melhorias na documentacao.
- Melhorias na cobertura de testes.

## O Que Nao Aceitamos

- Alteracoes que quebram testes existentes ou o headless validator.
- Alteracoes de formatacao puramente cosmeticas fora dos arquivos que voce esta modificando.
- Dependencias sem justificativa clara e verificacao de compatibilidade de licenca.
- Codigo que introduz vulnerabilidades de seguranca (veja OWASP Top 10).

## Reportando Problemas

Use o tracker de [GitHub Issues](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/issues).
Inclua:

- Passos para reproduzir (ou um arquivo demo minimo se aplicavel).
- Comportamento esperado vs real.
- Versao do Python, SO e hardware relevante (modelo de GPU se relacionado a ML).

## Vulnerabilidades de Seguranca

Consulte [SECURITY.md](SECURITY.md) para diretrizes de divulgacao responsavel.

## Perguntas?

Abra uma discussao ou issue. Valorizamos qualidade acima de velocidade.
