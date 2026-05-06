# `backend/nn/experimental/` — Sandbox experimental de redes neurais

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/experimental/`
> **Status:** Sandbox ativa — código aqui é controlado por feature flags e **não** é carregado pelo pipeline de coaching padrão.

## Finalidade

Este pacote é a área de staging para arquiteturas de redes neurais que ainda não estão prontas para o pipeline de coaching de produção. O código aqui é:

- **Controlado por feature flags** (por exemplo, `USE_RAP_MODEL=True`).
- **Importável mas inerte** salvo se a flag correspondente estiver definida.
- **Não** é dependência runtime obrigatória de `coaching_service.py` — o serviço degrada para os modos tradicional / RAG quando componentes experimentais falham.

Se um módulo daqui se gradua a production-ready, ele se muda para uma localização não-experimental (tipicamente `backend/nn/<dominio>/`) e o sub-pacote experimental é atualizado para remover ou virar stub do original.

## Layout

```
experimental/
├── __init__.py
└── rap_coach/        # RAP Coach (Reasoning + Acting + Pedagogy) — veja rap_coach/README.md
```

## Sub-pacotes

| Sub-pacote | Status | Flag | Descrição |
|------------|--------|------|-----------|
| `rap_coach/` | Experimental | `USE_RAP_MODEL=True` | Rede de política multi-head de 7 camadas (perception, memory, strategy, pedagogy, communication, etc.). Usa células LTC do `ncps` com o patch de shape RAP-LTC-FIX em `memory.py`. |

Veja `rap_coach/README.md` para a arquitetura RAP completa.

## Por que "experimental" tem seu próprio pacote

Manter código experimental num sub-pacote claramente marcado compra três coisas:

1. **Revisibilidade.** Um revisor consegue dizer imediatamente se uma alteração toca código de produção ou de sandbox olhando para o caminho de import.
2. **Isolamento de testes.** O pytest no CI pode incluir ou excluir testes experimentais com base em filtro de path, sem alterar todo arquivo.
3. **Deleção segura.** Quando um experimento é abandonado, o sub-pacote inteiro pode ser removido em um único commit, sem o risco de grep-and-replace pelo resto de `nn/`.

## Adicionando uma nova arquitetura experimental

1. Crie `experimental/<seu_modulo>/` com `__init__.py`.
2. Adicione uma feature flag nos defaults de `core/config.py` (default `False`).
3. Conecte a checagem da flag no boundary do orchestrator em `training_orchestrator.py`. **Não** importe código experimental incondicionalmente em outros lugares.
4. Forneça um README documentando: finalidade, nome da flag, dependências, ponto de entrada de treinamento e critérios de graduação.
5. Adicione um smoke test que afirma que o portão da flag levanta exceção quando `False`.

## Não faça

- **Não** importe de `experimental/` em `coaching_service.py`, `correction_engine.py`, ou qualquer caminho que rode no modo de coaching padrão.
- **Não** faça shipping de uma flag com default `True` para código experimental sem aprovação explícita do owner.
- **Não** dependa de módulos experimentais em builds congelados do PyInstaller sem um caminho de fallback.

## Relacionados

- Detalhes do RAP Coach: `experimental/rap_coach/README.md`
- Sub-pacotes NN de produção: `backend/nn/README.md`
- Tratamento de feature flags: `core/config.py:get_setting()`
- Portão da flag no orchestrator: `backend/nn/training_orchestrator.py:69-73`
