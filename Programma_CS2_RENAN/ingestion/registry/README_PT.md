# Registro de Arquivos de Demo e Gerenciamento de Ciclo de Vida

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/ingestion/registry/`

## Introducao

Este pacote fornece o rastreamento de arquivos de demo e o gerenciamento de
ciclo de vida para o subsistema de ingestao.  Sua responsabilidade central e
responder a uma unica pergunta: "esta demo ja foi ingerida?"  A classe
`DemoRegistry` mantem um arquivo JSON persistente que registra o conjunto de
nomes de demos processados.  O `DemoLifecycleManager` cuida das tarefas
pos-ingestao, especificamente a limpeza baseada em tempo de arquivos de demo
arquivados.

Juntos estes componentes asseguram que nenhuma demo seja ingerida duas vezes
(deduplicacao) e que espaco em disco seja recuperado automaticamente apos um
periodo de retencao configuravel.

## Inventario de Arquivos

| Arquivo | Finalidade | API Publica Principal |
|---------|------------|----------------------|
| `__init__.py` | Marcador de pacote (vazio) | -- |
| `registry.py` | Registro persistente de deduplicacao de demos | `DemoRegistry(registry_path)` |
| `lifecycle.py` | Limpeza de arquivos de demo baseada em tempo | `DemoLifecycleManager(raw_dir, processed_dir)` |
| `schema.sql` | Reservado para futuro registro baseado em SQL | -- |
| `README.md` | Documentacao (Ingles) | -- |
| `README_IT.md` | Documentacao (Italiano) | -- |
| `README_PT.md` | Documentacao (Portugues) | -- |

## Arquitetura e Conceitos

### `DemoRegistry` -- Motor de Deduplicacao

A classe `DemoRegistry` e a unica fonte de verdade sobre quais demos ja foram
processadas.  Ela persiste seu estado como um arquivo JSON em disco e fornece
acesso thread-safe e cross-process-safe.

**Construtor:** `DemoRegistry(registry_path: Path)`

**Estrutura de dados interna:** Um `set` Python de strings de nomes de demos
(`self._processed`).  O set e serializado em JSON como uma lista sob a chave
`"processed_demos"` e desserializado de volta para set no carregamento (F6-20)
para verificacoes de pertinencia O(1).

**Metodos publicos:**

| Metodo | Descricao |
|--------|-----------|
| `is_processed(demo_name: str) -> bool` | Retorna `True` se a demo ja foi ingerida. Lookup de set O(1). |
| `mark_processed(demo_name: str)` | Adiciona a demo ao set de processados e persiste em disco. Sem efeito se ja presente. |

**Modelo de concorrencia (R3-08):**

O registro usa uma estrategia de locking em dois niveis:

1. **Thread lock** (`threading.Lock`) -- protege o set em memoria
   `_processed` contra acesso concorrente dentro do mesmo processo.
2. **File lock** (`filelock.FileLock`) -- protege o arquivo JSON contra acesso
   concorrente entre processos.  O arquivo de lock e criado em
   `<registry_path>.lock`.

A ordem de aquisicao dos locks e sempre thread lock primeiro, depois file lock.
Esta ordenacao consistente previne deadlocks.

**Padrao de escrita atomica (R3-H04):**

Escritas usam uma estrategia write-ahead para prevenir corrupcao:

1. Cria um backup do registro existente (`.json.backup`).
2. Escreve o novo estado em um arquivo temporario (`tempfile.mkstemp()`).
3. Substitui atomicamente o arquivo original via `os.replace()`.
4. Se qualquer etapa falhar, o arquivo temporario e limpo e a excecao se
   propaga.

**Recuperacao de backup:**

Se o arquivo de registro primario estiver corrompido (erro de JSON decode), o
loader `_execute_registry_load()` tenta restaurar a partir do arquivo
`.json.backup`.  O backup e validado quanto a integridade estrutural antes de
ser confiado (deve ser um dict com uma lista `"processed_demos"`).  Somente se
tanto o primario quanto o backup estiverem indisponiveis o registro e resetado
para vazio -- isso e logado no nivel CRITICAL pois significa que todo o
historico de ingestao foi perdido.

### `DemoLifecycleManager` -- Limpeza de Disco

O `DemoLifecycleManager` gerencia a politica de retencao para arquivos de demo
arquivados.  Apos uma demo ser ingerida com sucesso, a pipeline a move para o
`processed_dir`.  Com o tempo, esses arquivos arquivados se acumulam e consomem
espaco em disco.

**Construtor:** `DemoLifecycleManager(raw_dir: Path, processed_dir: Path)`

**Metodos publicos:**

| Metodo | Descricao |
|--------|-----------|
| `cleanup_old_demos(days: int = 30)` | Remove arquivos `.dem` em `processed_dir` mais antigos que `days` dias. |

A logica de limpeza (`_purge_expired_demos()`) itera sobre todos os arquivos
`*.dem` no diretorio alvo, verifica o `st_mtime` de cada arquivo, e remove
arquivos que excedem o limiar de retencao.  Cada remocao e logada no nivel
INFO.

### `schema.sql` -- Reservado

O arquivo `schema.sql` esta reservado para uma futura migracao do registro
baseado em JSON para registro baseado em SQL.  Atualmente vazio.  Quando
implementado, definira uma tabela `demo_file_records` com colunas para caminho
do arquivo, hash, tamanho, tipo de fonte, estado de lifecycle, codigo de erro,
contador de retry e timestamps.

## Integracao

### Consumidores Upstream

| Consumidor | Uso |
|------------|-----|
| `ingestion/pipelines/user_ingest.py` | Chama `is_processed()` antes da ingestao, `mark_processed()` apos sucesso |
| `ingestion/pipelines/json_tournament_ingestor.py` | Processamento batch com verificacoes no registro |
| `run_ingestion.py` | Gerenciamento de registro no nivel do orquestrador |
| `core/session_engine.py` (IngestionWatcher) | Thread daemon que dispara pipelines e consulta o registro |

### Dependencias

| Dependencia | Finalidade |
|-------------|------------|
| `filelock` | Locking de arquivo cross-process (terceiros) |
| `observability/logger_setup.get_logger()` | Logging estruturado |

## Diagrama de Estados do Lifecycle

```
  [Novo Arquivo]
      |
      v
  is_processed()?
      |
  +---+---+
  |       |
  Nao     Sim --> pula
  |
  v
  Pipeline executa
      |
  +---+---+
  |       |
  OK    FALHA --> permanece em source_dir para retry
  |
  v
  mark_processed()
      |
  v
  Arquivado em processed_dir
      |
      v  (apos periodo de retencao)
  cleanup_old_demos() --> removido
```

## Notas de Desenvolvimento

- **F6-20 (conversao de set):** O formato JSON salva `processed_demos` como
  uma lista para compatibilidade de serializacao.  No carregamento, a lista e
  imediatamente convertida em um `set` para verificacoes de pertinencia O(1).
  Isso e importante porque o registro pode conter milhares de entradas e e
  verificado a cada tentativa de ingestao.
- **R3-08 (thread safety):** O `_lock` (threading.Lock) e o `_file_lock`
  (FileLock) sao sempre adquiridos na mesma ordem para prevenir deadlocks.  O
  thread lock e adquirido primeiro, depois o file lock.
- **R3-H04 (escritas atomicas):** O metodo `_save_inner()` usa
  `tempfile.mkstemp()` + `os.replace()` para garantir que o arquivo de registro
  nunca fique em um estado de escrita parcial.  Isso e critico porque um crash
  durante a escrita corromperia todo o historico de ingestao.
- **Seguranca de backup:** Antes de cada escrita, uma copia do registro atual
  e criada em `<path>.json.backup`.  O backup e validado na recuperacao para
  prevenir restauracao a partir de um backup corrompido.
- **Retencao padrao:** O periodo de retencao padrao de 30 dias e um
  compromisso conservador entre espaco em disco e a possibilidade de
  reanalisar demos recentes.  Pode ser sobrescrito via o parametro `days`.
- **Sem dependencia de banco de dados:** O registro usa intencionalmente um
  arquivo JSON plano em vez de SQLite.  Isso evita o acoplamento ao sistema
  tri-database e mantem o registro autocontido e portavel.
