
import argparse
import json
from datetime import datetime

import redis


def main():
    parser = argparse.ArgumentParser(
        description="Subscriber Redis Pub/Sub"
    )

    parser.add_argument("--nome", required=True)

    grupo = parser.add_mutually_exclusive_group(
        required=True
    )
    grupo.add_argument("--canal")
    grupo.add_argument("--padrao")

    args = parser.parse_args()

    # Conexão para métricas, independente da assinatura.
    r = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True
    )

    r.ping()
    pubsub = r.pubsub()

    if args.canal:
        pubsub.subscribe(args.canal)
        destino = args.canal
    else:
        pubsub.psubscribe(args.padrao)
        destino = args.padrao

    print(f"[{args.nome}] Assinatura: {destino}")
    print("Aguardando eventos... Ctrl+C para sair")

    try:
        for mensagem in pubsub.listen():
            if mensagem["type"] not in (
                "message", "pmessage"
            ):
                continue

            evento = json.loads(mensagem["data"])
            canal = mensagem["channel"]

            recebido_em = (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )

            print(
                f"[{args.nome}] "
                f"{recebido_em} | "
                f"{canal} | "
                f"ID={evento['id']} | "
                f"seq={evento['sequencia']}"
            )

            # Métricas auxiliares do laboratório.
            # Não são ACKs do Pub/Sub.
            with r.pipeline(transaction=True) as pipe:
                pipe.hincrby(
                    "lab:pubsub:recebidos",
                    args.nome,
                    1
                )
                pipe.hincrby(
                    "lab:pubsub:recebidos:canal",
                    canal,
                    1
                )
                pipe.execute()

    except KeyboardInterrupt:
        print(f"\n[{args.nome}] Desconectado")

    finally:
        pubsub.close()
        r.close()


if __name__ == "__main__":
    main()
