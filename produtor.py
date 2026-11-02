"""Produz pedidos em ordem FIFO e incrementa as métricas atomicamente."""
import argparse
import json
import random
import time
from datetime import datetime, timezone
from uuid import uuid4
from common import client, PENDENTES, METRICAS


def main():
    parser = argparse.ArgumentParser(description="Produtor Redis FIFO")
    parser.add_argument("--quantidade", type=int, default=100)
    parser.add_argument("--intervalo", type=float, default=0.2, help="Segundos entre mensagens")
    args = parser.parse_args()
    if args.quantidade < 1 or args.intervalo < 0:
        parser.error("Quantidade deve ser positiva e intervalo não pode ser negativo")

    r = client()
    r.ping()
    for seq in range(1, args.quantidade + 1):
        pedido = {
            "id": str(uuid4()),
            "sequencia": seq,
            "criado_em": datetime.now(timezone.utc).isoformat(),
            "valor": round(random.uniform(40, 500), 2),
        }
        payload = json.dumps(pedido, ensure_ascii=False)
        # MULTI/EXEC: o contador só sobe junto com a inclusão na fila.
        with r.pipeline(transaction=True) as pipe:
            pipe.rpush(PENDENTES, payload)
            pipe.hincrby(METRICAS, "publicados", 1)
            pipe.execute()
        print(f"[ENTROU] pedido seq={seq} id={pedido['id'][:8]}", flush=True)
        time.sleep(args.intervalo)
    print(f"Produção finalizada: {args.quantidade} mensagens.")


if __name__ == "__main__":
    main()
