
import argparse
import json
import time
from datetime import datetime, timezone
from uuid import uuid4

import redis


def main():
    parser = argparse.ArgumentParser(
        description="Publisher Redis Pub/Sub"
    )

    parser.add_argument(
        "--canal",
        default="pedido.criado"
    )
    parser.add_argument(
        "--quantidade",
        type=int,
        default=10
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=1.0
    )

    args = parser.parse_args()

    if args.quantidade < 1 or args.intervalo < 0:
        parser.error(
            "Quantidade deve ser positiva e "
            "intervalo não pode ser negativo"
        )

    r = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True
    )

    r.ping()

    try:
        for sequencia in range(
            1, args.quantidade + 1
        ):
            evento = {
                "id": str(uuid4()),
                "tipo": args.canal,
                "sequencia": sequencia,
                "publicado_em": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            destinatarios = r.publish(
                args.canal,
                json.dumps(evento)
            )

            # Contadores didáticos para observabilidade.
            with r.pipeline(transaction=True) as pipe:
                pipe.hincrby(
                    "lab:pubsub:metricas",
                    "publicados",
                    1
                )
                pipe.hincrby(
                    "lab:pubsub:publicados:canal",
                    args.canal,
                    1
                )
                pipe.execute()

            print(
                f"Publicado #{sequencia} | "
                f"canal={args.canal} | "
                f"destinatários={destinatarios}"
            )

            if sequencia < args.quantidade:
                time.sleep(args.intervalo)

    finally:
        r.close()


if __name__ == "__main__":
    main()
