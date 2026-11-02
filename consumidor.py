"""Worker FIFO com transferência atômica para 'processando' e confirmação."""
import argparse
import json
import time
from common import client, PENDENTES, PROCESSANDO, METRICAS

# ACK e incremento de contador acontecem na mesma execução atômica.
ACK_SCRIPT = """
local removidos = redis.call('LREM', KEYS[1], 1, ARGV[1])
if removidos == 1 then
    redis.call('HINCRBY', KEYS[2], 'concluidos', 1)
end
return removidos
"""


def main():
    parser = argparse.ArgumentParser(description="Consumidor Redis FIFO")
    parser.add_argument("--tempo", type=float, default=0.8, help="Tempo simulado de processamento (s)")
    args = parser.parse_args()
    if args.tempo < 0:
        parser.error("Tempo não pode ser negativo")

    r = client()
    r.ping()
    ack = r.register_script(ACK_SCRIPT)
    print("Worker iniciado (Ctrl+C para parar).", flush=True)
    try:
        while True:
            # FIFO: RPUSH à direita; BLMOVE consome a ESQUERDA.
            # A transferência para PROCESSANDO é atômica no Redis.
            mensagem = r.blmove(
                PENDENTES, PROCESSANDO, timeout=2, src="LEFT", dest="RIGHT"
            )
            if mensagem is None:
                continue

            try:
                pedido = json.loads(mensagem)
                print(f"[INICIO] seq={pedido['sequencia']}", flush=True)
                # Substituir pelo trabalho real: chamada HTTP, gravação etc.
                time.sleep(args.tempo)
                removidos = ack(keys=[PROCESSANDO, METRICAS], args=[mensagem])
                if removidos != 1:
                    print("[ALERTA] ACK não localizou a mensagem; conferir processamento", flush=True)
                else:
                    print(f"[SAIU/CONCLUÍDO] seq={pedido['sequencia']}", flush=True)
            except Exception as exc:
                # Intencionalmente não confirma mensagens com falha.
                # Ficam na lista PROCESSANDO para recuperação manual/automatizada.
                print(f"[FALHA] {exc!r}. Mensagem mantida em PROCESSANDO.", flush=True)
    except KeyboardInterrupt:
        print("\nWorker encerrado. Itens em processamento exigem recuperação.")


if __name__ == "__main__":
    main()
