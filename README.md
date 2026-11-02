# Laboratório de Engenharia de Sistemas — Redis FIFO com Python

**Tema:** Mensageria, processamento assíncrono, concorrência e observabilidade.

**Stack:** Python 3.11 · Redis · Docker Compose · HTML5 · JavaScript

**Ambiente:** macOS Big Sur 11.7.11 — Intel x86_64

**Nível:** Intermediário → Avançado

---

## 1. Objetivo do laboratório

Implementar e analisar uma fila FIFO (*First In, First Out*) utilizando Redis como infraestrutura de mensageria e Python para publicação e processamento de mensagens.

O laboratório permitirá observar:

- A publicação de mensagens em uma fila.
- O consumo assíncrono por um ou mais workers.
- A transferência atômica de mensagens entre listas Redis.
- A confirmação de processamento por meio de ACK.
- O comportamento do backlog quando a taxa de entrada supera a capacidade de processamento.
- A diferença entre ordem de retirada e ordem de conclusão.
- As limitações de confiabilidade de uma implementação baseada em Redis Lists.

**Resultado esperado:** um sistema funcional de processamento assíncrono com dashboard de observabilidade atualizado aproximadamente a cada segundo.

## 2. Arquitetura do laboratório

```text
              PRODUTOR PYTHON
                    |
                    | RPUSH
                    v
          +-------------------+
          | Redis             |
          | fila:pendentes    |
          +-------------------+
                    |
                    | BLMOVE
                    v
          +-------------------+
          | Redis             |
          | fila:processando  |
          +-------------------+
                    |
                    v
              CONSUMIDOR
                    |
                    | Processamento
                    | ACK (Lua)
                    v
          +-------------------+
          | Redis             |
          | metricas:pedidos  |
          +-------------------+
                    |
                    | HGETALL / LLEN
                    v
             PAINEL HTTP
                    |
                    v
          http://localhost:8080
```

O Redis atua como intermediário entre produtores e consumidores, desacoplando a publicação do processamento.

O consumidor utiliza uma operação bloqueante para aguardar mensagens sem realizar consultas repetitivas e desnecessárias.

## 3. Preparação do ambiente

### Etapa 1 — Acessar o projeto

Abra o terminal e entre no diretório do laboratório:

```bash
cd ~/python/redis_fifo_python
```

Confirme os arquivos disponíveis:

```bash
ls -la
```

Arquivos esperados:

| Arquivo | Responsabilidade |
|---|---|
| `common.py` | Conexão Redis e definição das chaves |
| `produtor.py` | Publicação de mensagens |
| `consumidor.py` | Processamento e confirmação |
| `painel_simples.py` | API HTTP e dashboard |
| `docker-compose.yml` | Infraestrutura Redis |
| `requirements.txt` | Dependências Python |

O arquivo `painel.py` baseado em Streamlit não será utilizado.

### Etapa 2 — Iniciar o Redis

Execute:

```bash
docker compose up -d
```

Verifique se o contêiner está ativo:

```bash
docker compose ps
```

Teste a comunicação:

```bash
docker compose exec redis redis-cli PING
```

**Resultado esperado:**

```text
PONG
```

Se o comando retornar `PONG`, o Redis está respondendo corretamente.

### Etapa 3 — Preparar o Python

Como você já possui um ambiente virtual, ative-o:

```bash
source venv/bin/activate
```

Se o diretório do ambiente virtual for `.venv`, utilize:

```bash
source .venv/bin/activate
```

Confirme:

```bash
python3 --version
```

Resultado esperado:

```text
Python 3.11.10
```

Instale somente a biblioteca Redis:

```bash
python3 -m pip install "redis>=5,<8"
```

Não instale Streamlit, Pandas ou PyArrow.

### Etapa 4 — Verificar a conexão Python com Redis

Execute:

```bash
python3 -c "from common import client; print(client().ping())"
```

**Resultado esperado:**

```text
True
```

Se retornar `True`, a aplicação Python está conectada ao Redis.

---

## 4. Execução do laboratório

Abra três terminais no diretório do projeto. Ative o ambiente virtual em cada um deles.

### Terminal 1 — Observabilidade

Inicie o dashboard:

```bash
python3 painel_simples.py
```

Abra no navegador:

**http://localhost:8080**

O painel apresentará quatro indicadores:

| Indicador | Significado |
|---|---|
| Publicadas | Total de mensagens enviadas |
| Concluídas | Total de mensagens confirmadas |
| Aguardando | Mensagens disponíveis para consumo |
| Processando | Mensagens retiradas, ainda sem ACK |

Os gráficos apresentam a taxa de publicação, a taxa de conclusão e a profundidade das filas.

### Terminal 2 — Processamento

Inicie um consumidor:

```bash
python3 consumidor.py --tempo 0.8
```

O parâmetro `--tempo 0.8` representa o tempo simulado de processamento de cada mensagem, em segundos.

Capacidade teórica aproximada:

**1 ÷ 0,8 = 1,25 mensagem/segundo**

O consumidor permanecerá aguardando novas mensagens quando a fila estiver vazia.

### Terminal 3 — Publicação

Execute:

```bash
python3 produtor.py --quantidade 100 --intervalo 0.2
```

Parâmetros:

- `--quantidade 100`: publica 100 mensagens.
- `--intervalo 0.2`: aguarda 200 milissegundos entre publicações.

Taxa aproximada de entrada:

**1 ÷ 0,2 = 5 mensagens/segundo**

### Resultado esperado

Durante a publicação:

- O contador de mensagens publicadas aumenta.
- A fila de pendentes cresce.
- O consumidor processa mensagens continuamente.
- A taxa de publicação supera a capacidade de conclusão.

Após o produtor terminar:

- A publicação de novas mensagens é interrompida.
- O consumidor continua trabalhando.
- O backlog diminui progressivamente.
- A fila eventualmente fica vazia, se não houver novas mensagens ou falhas.

Esses resultados pressupõem uma fila inicialmente vazia e um consumidor funcionando normalmente.

---

## 5. Experimento A — Análise de throughput e backlog

**Objetivo:** compreender o comportamento de um sistema quando a taxa de chegada supera sua capacidade de processamento.

Taxa de chegada:

`λ = 5 mensagens/s`

Capacidade de processamento:

`μ = 1,25 mensagem/s`

Taxa aproximada de crescimento do backlog:

`λ - μ = 3,75 mensagens/s`

Durante 20 segundos, o crescimento esperado é de aproximadamente:

`3,75 × 20 = 75 mensagens`

Essa estimativa desconsidera pequenas variações de execução e comunicação.

**Perguntas para análise:**

1. Por que a fila cresce mesmo quando o consumidor está funcionando?
2. O que acontece quando a taxa de chegada supera permanentemente a capacidade de processamento?
3. Como estimar o tempo necessário para esvaziar o backlog?
4. Qual a relação entre throughput, latência e utilização dos workers?

## 6. Experimento B — Concorrência com múltiplos consumidores

Abra um quarto terminal e execute:

```bash
python3 consumidor.py --tempo 0.8
```

Agora existem dois consumidores concorrentes.

Capacidade teórica agregada:

`2 × 1,25 = 2,5 mensagens/s`

Execute novamente o produtor:

```bash
python3 produtor.py --quantidade 100 --intervalo 0.2
```

Observe como a capacidade de processamento aumenta e a taxa de crescimento do backlog diminui.

**Ponto arquitetural importante:** a ordem FIFO de retirada não garante a ordem FIFO de conclusão quando múltiplos consumidores trabalham simultaneamente.

Uma mensagem retirada primeiro pode terminar depois de outra mensagem retirada posteriormente.

## 7. Experimento C — Inspeção das estruturas Redis

### Consultar mensagens aguardando

```bash
docker compose exec redis redis-cli \
  LLEN 'fila:{pedidos}:pendentes'
```

### Consultar mensagens em processamento

```bash
docker compose exec redis redis-cli \
  LLEN 'fila:{pedidos}:processando'
```

### Consultar métricas acumuladas

```bash
docker compose exec redis redis-cli \
  HGETALL 'metricas:{pedidos}'
```

### Visualizar as primeiras mensagens pendentes

```bash
docker compose exec redis redis-cli \
  LRANGE 'fila:{pedidos}:pendentes' 0 2
```

Esses comandos permitem comparar as métricas apresentadas no dashboard com o estado real das estruturas de dados no Redis.

---

## 8. Experimento D — Simulação de falha

**Objetivo:** identificar limitações de confiabilidade no processamento de mensagens.

1. Inicie o produtor.
2. Inicie um consumidor com processamento mais demorado.
3. Enquanto uma mensagem estiver em processamento, interrompa o consumidor com `Ctrl+C`.
4. Consulte as listas `PENDENTES` e `PROCESSANDO`.
5. Reinicie o consumidor.
6. Verifique se a mensagem interrompida foi automaticamente recuperada.

**Resultado esperado:** uma mensagem transferida para `PROCESSANDO` pode permanecer nessa lista após a interrupção do consumidor.

A implementação atual não possui mecanismo automático de recuperação de mensagens abandonadas.

Isso demonstra por que a transferência atômica entre listas, isoladamente, não garante entrega *at-least-once*.

## 9. Semântica de mensageria e garantias de processamento

### FIFO — First In, First Out

A primeira mensagem inserida é a primeira selecionada para retirada, considerando a operação de consumo e a ordem da lista.

### ACK — Acknowledgment

Confirmação de que uma mensagem foi processada com sucesso.

No laboratório, o ACK utiliza um script Lua para remover a mensagem da lista de processamento e incrementar o contador de conclusões somente quando a remoção ocorre.

### At-most-once

Uma mensagem pode ser perdida em caso de falha, mas o mecanismo não realiza reentregas.

### At-least-once

O sistema tenta garantir que mensagens sejam processadas pelo menos uma vez, admitindo reentregas e possíveis duplicações.

Exige recuperação de mensagens não confirmadas e políticas de retry.

### Exactly-once

Semântica em que os efeitos de negócio de uma mensagem ocorrem exatamente uma vez.

Não é garantida automaticamente pelo Redis Lists, Redis Streams ou por um ACK isolado. Normalmente exige mecanismos adicionais, como idempotência, deduplicação e coordenação transacional.

### Backpressure

Mecanismo utilizado para controlar ou limitar a entrada de trabalho quando a capacidade de processamento está saturada.

### DLQ — Dead Letter Queue

Fila destinada a mensagens que não puderam ser processadas após as tentativas previstas.

### Idempotência

Propriedade que permite repetir uma operação sem produzir efeitos de negócio adicionais indevidos.

É essencial em sistemas com possibilidade de reentrega de mensagens.

---

## 10. Limitações e evolução arquitetural

Esta implementação é adequada para fins didáticos, mas ainda não representa uma infraestrutura completa de mensageria para produção.

Evoluções recomendadas:

| Prioridade | Evolução | Objetivo |
|---|---|---|
| P0 | Recuperação de mensagens abandonadas | Evitar mensagens presas após falhas |
| P0 | Idempotência | Controlar efeitos de reprocessamento |
| P1 | Retry com backoff | Tratar falhas transitórias |
| P1 | Dead Letter Queue | Isolar mensagens problemáticas |
| P1 | Métricas de latência e idade da fila | Identificar degradação |
| P2 | Limites de backlog | Aplicar backpressure |
| P2 | Redis Streams | Utilizar consumer groups e ACK nativo |
| P2 | Prometheus e Grafana | Evoluir a observabilidade |

O Redis foi configurado com AOF para o laboratório, mas isso não garante durabilidade absoluta nem alta disponibilidade.

A política de expiração `EXPIRE` aplica-se à chave Redis inteira, não individualmente às mensagens de uma lista.

O dashboard atual mantém seu histórico no navegador. Portanto, os gráficos de taxa dependem da frequência de atualização e não representam um histórico persistente de métricas.

## 11. Critérios de conclusão

O laboratório será considerado concluído quando você conseguir:

- [ ] Inicializar o Redis pelo Docker Compose.
- [ ] Validar a conexão com Python.
- [ ] Publicar 100 mensagens.
- [ ] Processar mensagens com um consumidor.
- [ ] Observar o crescimento e a redução do backlog.
- [ ] Executar dois consumidores simultaneamente.
- [ ] Inspecionar as listas Redis pelo CLI.
- [ ] Simular uma interrupção do consumidor.
- [ ] Identificar mensagens não confirmadas.
- [ ] Explicar as limitações de entrega e recuperação.

## 12. Encerramento e limpeza

Interrompa o produtor, os consumidores e o dashboard utilizando `Ctrl+C`.

Para parar o Redis preservando os volumes:

```bash
docker compose down
```

Para remover também os volumes de dados:

```bash
docker compose down -v
```

**Atenção:** o segundo comando remove os volumes do projeto, incluindo as mensagens e métricas persistidas no Redis.

---

## 13. Próximo nível — Redis Streams

Após concluir o laboratório, a evolução natural será implementar a mesma arquitetura com Redis Streams:

- `XADD` — publicação.
- `XGROUP CREATE` — criação de grupo.
- `XREADGROUP` — consumo.
- `XACK` — confirmação.
- `XPENDING` — inspeção de mensagens pendentes.
- `XAUTOCLAIM` — recuperação de mensagens não confirmadas.

O objetivo será comparar as garantias de processamento, a concorrência, a recuperação de falhas e a complexidade operacional de Redis Lists e Redis Streams.

**Competências desenvolvidas:** sistemas distribuídos, mensageria assíncrona, estruturas de dados Redis, processamento concorrente, observabilidade, tolerância a falhas e análise de desempenho.