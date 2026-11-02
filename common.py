"""Chaves com a mesma hash tag {pedidos}, compatíveis com Redis Cluster."""
import os
import redis

PENDENTES = "fila:{pedidos}:pendentes"
PROCESSANDO = "fila:{pedidos}:processando"
METRICAS = "metricas:{pedidos}"


def client():
    return redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_connect_timeout=5,
        health_check_interval=15,
    )
