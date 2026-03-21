> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge Base — Sistema de Ajuda In-App

> **Autoridade:** Regra 3 (Frontend & UX)

## Introducao

O modulo `knowledge_base` fornece um sistema de documentacao in-app leve e somente
leitura que serve conteudo de ajuda voltado ao usuario dentro do Macena CS2 Analyzer.
Ele le arquivos Markdown do diretorio de recursos `data/docs/`, indexa-os pelo nome
do arquivo e expoe uma API simples de busca textual que as camadas de UI consomem.

Este modulo e **completamente separado** do sistema de conhecimento RAG/COPER
localizado em `backend/knowledge/`. Os dois modulos nao compartilham codigo, dados
nem estado em tempo de execucao. Seus nomes sao semelhantes, mas suas
responsabilidades sao disjuntas:

| Modulo | Finalidade | Tecnologia |
|--------|-----------|------------|
| `backend/knowledge/` | Conhecimento RAG para coaching + Experience Bank + busca vetorial | SBERT embeddings, FAISS, SQLite |
| `backend/knowledge_base/` | **Documentacao de ajuda in-app** (este modulo) | Arquivos Markdown, busca textual por substring |

## Inventario de Arquivos

| Arquivo | Linhas | Finalidade | Exportacoes Principais |
|---------|--------|-----------|------------------------|
| `__init__.py` | 1 | Marcador de pacote | — |
| `help_system.py` | ~83 | Busca, indexacao e consulta de documentacao Markdown | `HelpSystem`, `get_help_system()` |

## Arquitetura e Conceitos

### Classe HelpSystem

`HelpSystem` e a unica classe neste modulo. Ela desempenha tres responsabilidades:

1. **Construcao do indice** — Na instanciacao (ou quando `refresh_index()` e chamado),
   varre o diretorio de documentos, le cada arquivo `.md`, extrai o primeiro heading
   `# ` como titulo do topico e armazena o conteudo completo em um dicionario em
   memoria indexado pelo stem do nome do arquivo (ex.: `getting_started.md` se torna
   o ID de topico `getting_started`).

2. **Recuperacao de topicos** — `get_topic(topic_id)` retorna um unico dicionario
   de topico com as chaves `title`, `content` e `path`. `get_all_topics()` retorna
   uma lista de todos os topicos indexados para popular o menu lateral.

3. **Busca textual** — `search_topics(query)` realiza correspondencia por substring
   case-insensitive em titulos e conteudos. Correspondencias em titulos recebem uma
   pontuacao de 10; correspondencias em conteudos recebem uma pontuacao de 1. Os
   resultados sao retornados ordenados por pontuacao de relevancia decrescente.

### Padrao Singleton (C-54)

O modulo segue o padrao **lazy singleton** identificado como C-54 no codebase:

```python
# Nenhum I/O de arquivo no momento do import
_help_system = None

def get_help_system() -> HelpSystem:
    global _help_system
    if _help_system is None:
        _help_system = HelpSystem()
    return _help_system
```

Isso evita leituras de disco durante o import do modulo, o que e critico porque o
modulo do sistema de ajuda pode ser importado por telas que nunca sao realmente
visitadas durante uma sessao.

### Fonte de Dados: `data/docs/`

Os arquivos Markdown residem no diretorio de recursos `Programma_CS2_RENAN/data/docs/`,
resolvido em tempo de execucao via `get_resource_path("data/docs")` de `core/config.py`.
Essa resolucao e compativel com PyInstaller: ao executar a partir de um bundle
congelado, le da pasta de extracao temporaria `_MEIPASS` em vez da arvore de codigo
fonte.

Topicos de documentacao atuais:

| Arquivo | Topico | Resumo do Conteudo |
|---------|--------|---------------------|
| `getting_started.md` | Getting Started | Wizard de configuracao, caminhos de demo, vinculacao Steam/FACEIT, regra 10/10, modos de ingestao |
| `features.md` | Feature Guide | Dashboard, Skill Radar, RAP AI Coach, Tactical Viewer, Advanced Analytics |
| `troubleshooting.md` | Troubleshooting | Correcoes de travamento neural, deteccao de demo, problemas de inicializacao da UI, otimizacao de desempenho |

### Topicos de Fallback

Tanto a tela de ajuda Qt quanto a Kivy definem listas hardcoded `_FALLBACK_TOPICS`
que sao utilizadas quando `help_system.py` falha ao ser importado ou quando
`get_help_system()` levanta uma excecao. Os topicos de fallback cobrem: Getting
Started, Demo Analysis, AI Coach, Steam Integration, Navigation e Troubleshooting.
Isso garante que a tela de ajuda nunca fique completamente vazia, mesmo em ambientes
degradados.

### Pontuacao de Busca

O algoritmo de busca e intencionalmente simples (sem stemming, sem correspondencia
fuzzy, sem tokenizacao). As pontuacoes sao atribuidas da seguinte forma:

| Local da Correspondencia | Pontuacao |
|--------------------------|-----------|
| O titulo contem a substring da query | +10 |
| O conteudo contem a substring da query | +1 |

Os resultados sao ordenados por pontuacao total decrescente. Um topico que corresponde
tanto no titulo quanto no conteudo recebe uma pontuacao combinada de 11.

## Integracao

### Qt Help Screen (`apps/qt_app/screens/help_screen.py`)

O consumidor UI principal. Implementa um layout de dois paineis:

- **Painel esquerdo** (240px fixo): Input de busca (`QLineEdit`) + lista de topicos (`QListWidget`)
- **Painel direito** (flexivel): Visualizador de conteudo rolavel (`QLabel` dentro de `QScrollArea`)

A tela importa `get_help_system` com um guard try/except e define
`_HELP_AVAILABLE = True/False`. Em `on_enter()`, tenta carregar os topicos do sistema
de ajuda e recorre a `_FALLBACK_TOPICS` em caso de falha. A busca e realizada no lado
do cliente filtrando a lista de topicos ja carregada.

### Kivy Help Screen (`apps/desktop_app/help_screen.py`)

O consumidor Kivy legado. Utiliza `MDScreen` com widgets `MDListItem` para a barra
lateral de topicos e um `MDLabel` para exibicao do conteudo. Segue o mesmo padrao
de import-guard e fallback da tela Qt, mas popula uma lista vazia em vez de topicos
de fallback quando o sistema de ajuda nao esta disponivel.

### Adicionando Novos Topicos de Ajuda

Para adicionar um novo topico de documentacao a ajuda in-app:

1. Criar um novo arquivo `.md` em `Programma_CS2_RENAN/data/docs/` (ex.: `economy_tips.md`)
2. Iniciar o arquivo com um heading `# Titulo` — este se torna o titulo do topico na barra lateral
3. Escrever o conteudo em Markdown padrao (o visualizador renderiza texto simples, nao HTML rico)
4. Chamar `get_help_system().refresh_index()` se o app ja estiver em execucao, ou reiniciar

Nenhuma alteracao de codigo e necessaria. O indice e reconstruido dinamicamente a partir do filesystem.

## Notas de Desenvolvimento

- **Thread safety:** `HelpSystem` nao e thread-safe. Foi projetado para acesso
  single-threaded apenas pela UI. Tanto a tela Qt quanto a Kivy o chamam a partir do
  thread principal/UI.
- **Nenhuma operacao de escrita:** O sistema de ajuda nunca modifica arquivos no disco.
  E estritamente um indexador de somente leitura.
- **Encoding:** Todos os arquivos sao lidos como UTF-8 (`encoding="utf-8"`).
- **Tratamento de erros:** Falhas de leitura de arquivos individuais sao capturadas e
  impressas em stderr (`print()`). Isso devera ser migrado para logging estruturado
  em uma futura iteracao.
- **Invalidacao de cache:** O cache e reconstruido apenas quando `refresh_index()` e
  chamado explicitamente. Nao existe mecanismo de file-watcher ou auto-refresh.
- **Renderizacao de conteudo:** A tela de ajuda Qt exibe o conteudo como texto simples
  via `QLabel.setText()`. A formatacao Markdown (cabecalhos, listas, links) nao e
  renderizada — o conteudo aparece como esta. Uma melhoria futura poderia utilizar
  `QTextBrowser` com `setMarkdown()` para renderizacao rica.
- **Limitacoes da busca:** A correspondencia por substring significa que buscar por
  "demo" tambem correspondera a "demonstration" e "demographics". Nao ha consciencia
  de limites de palavras.
- **Compatibilidade PyInstaller:** O diretorio de documentos e resolvido via
  `get_resource_path()`, garantindo funcionamento tanto em desenvolvimento quanto em
  builds congeladas. O diretorio `data/docs/` deve ser incluido na lista `datas` do
  arquivo spec do PyInstaller para que o sistema de ajuda funcione em builds distribuidas.
