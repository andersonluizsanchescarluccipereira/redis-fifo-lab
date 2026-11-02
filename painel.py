
"""Dashboard Redis FIFO sem Streamlit ou Pandas."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

from common import client, PENDENTES, PROCESSANDO, METRICAS

HOST = "127.0.0.1"
PORT = 8080

HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Redis FIFO - Monitoramento</title>
<style>
body {
    background: #0b1220;
    color: #e5e7eb;
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 25px;
}
h1 { color: #38bdf8; }
.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 15px;
    margin-bottom: 25px;
}
.card, .grafico {
    background: #172033;
    border-radius: 12px;
    padding: 20px;
}
.numero {
    font-size: 32px;
    font-weight: bold;
    color: #38bdf8;
}
.grafico { margin-bottom: 20px; }
canvas {
    width: 100%;
    height: 240px;
    display: block;
}
.legenda { color: #94a3b8; font-size: 13px; }
#status { margin-bottom: 20px; }
</style>
</head>
<body>

<h1>Redis FIFO - Dashboard</h1>
<p id="status">Conectando ao Redis...</p>

<div class="cards">
    <div class="card">
        <p>Publicadas</p>
        <div class="numero" id="publicados">0</div>
    </div>
    <div class="card">
        <p>Concluídas</p>
        <div class="numero" id="concluidos">0</div>
    </div>
    <div class="card">
        <p>Aguardando</p>
        <div class="numero" id="pendentes">0</div>
    </div>
    <div class="card">
        <p>Processando</p>
        <div class="numero" id="processando">0</div>
    </div>
</div>

<div class="grafico">
    <h2>Entradas e saídas por segundo</h2>
    <p class="legenda">
        Azul: entradas | Verde: conclusões
    </p>
    <canvas id="taxas"></canvas>
</div>

<div class="grafico">
    <h2>Profundidade da fila</h2>
    <p class="legenda">
        Amarelo: aguardando | Roxo: processando
    </p>
    <canvas id="fila"></canvas>
</div>

<script>
const historico = [];
let anterior = null;
let atualizando = false;

function desenhar(id, series) {
    const canvas = document.getElementById(id);
    const largura = canvas.clientWidth;
    const altura = 240;
    const dpr = window.devicePixelRatio || 1;

    canvas.width = Math.round(largura * dpr);
    canvas.height = Math.round(altura * dpr);

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, largura, altura);

    const margem = 35;
    const areaW = largura - margem - 12;
    const areaH = altura - 2 * margem;

    const maximo = Math.max(
        1,
        ...historico.flatMap(p => series.map(s => p[s.campo]))
    ) * 1.15;

    ctx.strokeStyle = "#334155";
    ctx.fillStyle = "#94a3b8";
    ctx.font = "11px Arial";

    for (let i = 0; i <= 4; i++) {
        const y = margem + areaH * i / 4;
        ctx.beginPath();
        ctx.moveTo(margem, y);
        ctx.lineTo(largura - 12, y);
        ctx.stroke();
        ctx.fillText(
            (maximo * (1 - i / 4)).toFixed(1),
            2, y + 4
        );
    }

    for (const serie of series) {
        ctx.strokeStyle = serie.cor;
        ctx.lineWidth = 2.5;
        ctx.beginPath();

        historico.forEach((p, i) => {
            const x = margem + (
                historico.length > 1
                    ? i * areaW / (historico.length - 1)
                    : areaW / 2
            );
            const y = margem + areaH *
                (1 - p[serie.campo] / maximo);

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });

        ctx.stroke();
    }
}

function renderizar() {
    desenhar("taxas", [
        {campo: "entradas", cor: "#38bdf8"},
        {campo: "saidas", cor: "#22c55e"}
    ]);

    desenhar("fila", [
        {campo: "pendentes", cor: "#facc15"},
        {campo: "processando", cor: "#a78bfa"}
    ]);
}

async function atualizar() {
    if (atualizando) return;
    atualizando = true;

    try {
        const resposta = await fetch(
            "/api/metricas",
            {cache: "no-store"}
        );

        if (!resposta.ok) throw new Error("HTTP " + resposta.status);

        const dados = await resposta.json();
        const agora = Date.now();

        document.getElementById("publicados").textContent =
            dados.publicados;
        document.getElementById("concluidos").textContent =
            dados.concluidos;
        document.getElementById("pendentes").textContent =
            dados.pendentes;
        document.getElementById("processando").textContent =
            dados.processando;

        let entradas = 0;
        let saidas = 0;

        if (anterior) {
            const segundos = Math.max(
                (agora - anterior.tempo) / 1000, 0.001
            );

            entradas = Math.max(
                0, dados.publicados - anterior.publicados
            ) / segundos;

            saidas = Math.max(
                0, dados.concluidos - anterior.concluidos
            ) / segundos;
        }

        anterior = {...dados, tempo: agora};

        historico.push({
            entradas,
            saidas,
            pendentes: dados.pendentes,
            processando: dados.processando
        });

        if (historico.length > 120) historico.shift();

        renderizar();

        document.getElementById("status").textContent =
            "Redis conectado - atualização a cada segundo";

    } catch (erro) {
        document.getElementById("status").textContent =
            "Erro: " + erro.message;
    } finally {
        atualizando = false;
    }
}

window.addEventListener("resize", renderizar);
atualizar();
setInterval(atualizar, 1000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            conteudo = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)
            return

        if self.path == "/api/metricas":
            try:
                r = client()

                with r.pipeline(transaction=False) as pipe:
                    pipe.hgetall(METRICAS)
                    pipe.llen(PENDENTES)
                    pipe.llen(PROCESSANDO)
                    totais, pendentes, processando = pipe.execute()

                dados = {
                    "publicados": int(totais.get("publicados", 0)),
                    "concluidos": int(totais.get("concluidos", 0)),
                    "pendentes": pendentes,
                    "processando": processando
                }

                self.responder_json(200, dados)

            except Exception as exc:
                self.responder_json(503, {"erro": str(exc)})
            return

        self.send_error(404)

    def responder_json(self, status, dados):
        conteudo = json.dumps(dados).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)


if __name__ == "__main__":
    servidor = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Dashboard disponível em http://{HOST}:{PORT}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\\nEncerrando dashboard...")
    finally:
        servidor.server_close()
