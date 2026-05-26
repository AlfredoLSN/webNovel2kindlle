from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from webnovel2kindle.epub import build_epub, cover_from_response, epub_file_name
from webnovel2kindle.scraper.centralnovel import parse_chapter_page, parse_novel_page
from webnovel2kindle.scraper.client import FetchError, HttpClient

DEFAULT_OUTPUT_DIR = Path("dist")
LOGO_PATH = Path(__file__).resolve().parents[2] / "logo.png"


class WebNovelServer(ThreadingHTTPServer):
    daemon_threads = True


class UiHandler(BaseHTTPRequestHandler):
    server_version = "webnovel2kindle-ui/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._send_html(INDEX_HTML)
            return
        if self.path == "/logo.png" and LOGO_PATH.exists():
            self._send_bytes(LOGO_PATH.read_bytes(), "image/png")
            return

        self._send_json({"error": "Pagina nao encontrada."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        routes = {
            "/api/scan": self._scan,
            "/api/export": self._export,
        }
        handler = routes.get(urlparse(self.path).path)
        if handler is None:
            self._send_json({"error": "Rota nao encontrada."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json()
            response = handler(payload)
        except UiError as exc:
            self._send_json({"error": str(exc)}, status=exc.status)
            return
        except Exception as exc:  # pragma: no cover - last-resort web boundary
            self._send_json(
                {"error": f"Erro inesperado: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._send_json(response)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _scan(self, payload: dict[str, object]) -> dict[str, object]:
        url = _payload_url(payload)
        novel = _fetch_novel(url)
        return {
            "title": novel.title,
            "url": novel.url,
            "chapter_count": novel.chapter_count,
            "metadata": {
                "author": novel.metadata.author,
                "status": novel.metadata.status,
                "type": novel.metadata.novel_type,
                "release_year": novel.metadata.release_year,
                "cover_url": novel.metadata.cover_url,
                "genres": list(novel.metadata.genres),
            },
            "volumes": [
                {
                    "index": index,
                    "title": volume.title,
                    "chapter_count": len(volume.chapters),
                }
                for index, volume in enumerate(novel.volumes, start=1)
            ],
        }

    def _export(self, payload: dict[str, object]) -> dict[str, object]:
        url = _payload_url(payload)
        volume_index = _payload_volume(payload)
        output_dir = _payload_output_dir(payload)

        client = HttpClient()
        novel = _fetch_novel(url, client=client)
        if not novel.volumes:
            raise UiError("Nenhum volume encontrado nessa obra.")
        if volume_index < 1 or volume_index > len(novel.volumes):
            raise UiError(f"Volume invalido. Escolha de 1 a {len(novel.volumes)}.")

        volume = novel.volumes[volume_index - 1]
        chapters = []
        try:
            for chapter in volume.chapters:
                chapter_html = client.get_html(chapter.url)
                chapters.append(parse_chapter_page(chapter_html))
        except FetchError as exc:
            raise UiError(str(exc), HTTPStatus.BAD_GATEWAY) from exc

        cover = None
        if novel.metadata.cover_url:
            try:
                cover_data, content_type = client.get_bytes(novel.metadata.cover_url)
                cover = cover_from_response(cover_data, content_type, novel.metadata.cover_url)
            except FetchError:
                cover = None

        output_path = output_dir / epub_file_name(novel, volume)
        build_epub(novel, volume, chapters, output_path, cover)
        return {
            "message": "EPUB gerado com sucesso.",
            "path": str(output_path),
            "title": f"{novel.title} - {volume.title}",
            "chapter_count": len(chapters),
        }

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("content-length", "0"))
        if length <= 0:
            return {}

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise UiError("JSON invalido.", HTTPStatus.BAD_REQUEST) from exc

        if not isinstance(payload, dict):
            raise UiError("O corpo da requisicao precisa ser um objeto JSON.")
        return payload

    def _send_html(self, content: str) -> None:
        body = content.encode("utf-8")
        self._send_bytes(body, "text/html; charset=utf-8")

    def _send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class UiError(RuntimeError):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(message)
        self.status = status


def run_server(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    server = WebNovelServer((host, port), UiHandler)
    url = f"http://{host}:{server.server_port}"
    if open_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()

    print(f"Interface aberta em {url}")
    print("Pressione Ctrl+C para parar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nInterface encerrada.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Interface web local do webnovel2kindle.")
    parser.add_argument("--host", default="127.0.0.1", help="Host da interface.")
    parser.add_argument("--port", default=8765, type=int, help="Porta da interface.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Nao abrir o navegador automaticamente.",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, open_browser=not args.no_browser)


def _fetch_novel(url: str, client: HttpClient | None = None):
    if not _is_centralnovel_url(url):
        raise UiError("Por enquanto a interface aceita apenas links da Central Novel.")

    try:
        html = (client or HttpClient()).get_html(url)
    except FetchError as exc:
        raise UiError(str(exc), HTTPStatus.BAD_GATEWAY) from exc

    return parse_novel_page(html, url)


def _payload_url(payload: dict[str, object]) -> str:
    url = payload.get("url")
    if not isinstance(url, str) or not url.strip():
        raise UiError("Informe o link da obra.")
    return url.strip()


def _payload_volume(payload: dict[str, object]) -> int:
    volume = payload.get("volume")
    if isinstance(volume, int):
        return volume
    if isinstance(volume, str) and volume.isdigit():
        return int(volume)
    raise UiError("Escolha um volume para exportar.")


def _payload_output_dir(payload: dict[str, object]) -> Path:
    output_dir = payload.get("output_dir")
    if output_dir is None or output_dir == "":
        return DEFAULT_OUTPUT_DIR
    if not isinstance(output_dir, str):
        raise UiError("A pasta de saida precisa ser texto.")
    return Path(output_dir)


def _is_centralnovel_url(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return hostname == "centralnovel.com" or hostname.endswith(".centralnovel.com")


INDEX_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>webnovel2kindle</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f4ef;
      --surface: #ffffff;
      --ink: #1e2428;
      --muted: #66717a;
      --line: #d9ddd9;
      --accent: #2b7a78;
      --accent-dark: #185e5c;
      --warn: #9d3d37;
      --soft: #e7f0ed;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }

    main {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 0 0 22px;
      border-bottom: 1px solid var(--line);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
      min-width: 0;
    }

    .brand img {
      width: 48px;
      height: 48px;
      object-fit: contain;
    }

    h1, h2, p { margin: 0; }

    h1 {
      font-size: clamp(1.5rem, 4vw, 2rem);
      font-weight: 750;
      letter-spacing: 0;
    }

    .subtitle {
      margin-top: 4px;
      color: var(--muted);
      font-size: 0.96rem;
    }

    .status {
      min-height: 38px;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      color: var(--muted);
      font-size: 0.94rem;
      text-align: right;
    }

    .status.busy::before {
      content: "";
      width: 14px;
      height: 14px;
      margin-right: 8px;
      border: 2px solid var(--line);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(280px, 360px) 1fr;
      gap: 24px;
      align-items: start;
      padding-top: 28px;
    }

    section {
      min-width: 0;
    }

    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }

    .form {
      display: grid;
      gap: 14px;
    }

    label {
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 0.88rem;
      font-weight: 650;
    }

    input, select {
      width: 100%;
      height: 42px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 11px;
      color: var(--ink);
      background: #fff;
      font: inherit;
    }

    input:focus, select:focus {
      outline: 3px solid rgba(43, 122, 120, 0.18);
      border-color: var(--accent);
    }

    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 4px;
    }

    button {
      height: 42px;
      border: 1px solid transparent;
      border-radius: 6px;
      padding: 0 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    button.primary {
      background: var(--accent);
      color: #fff;
    }

    button.primary:hover { background: var(--accent-dark); }

    button.secondary {
      background: var(--soft);
      color: var(--accent-dark);
      border-color: #c7ddda;
    }

    button:disabled {
      opacity: 0.58;
      cursor: not-allowed;
    }

    .novel {
      display: grid;
      grid-template-columns: 112px 1fr;
      gap: 18px;
      align-items: start;
      margin-bottom: 18px;
    }

    .cover {
      width: 112px;
      aspect-ratio: 2 / 3;
      border-radius: 6px;
      object-fit: cover;
      background: var(--soft);
      border: 1px solid var(--line);
    }

    .cover.empty {
      display: grid;
      place-items: center;
      color: var(--muted);
      font-weight: 750;
      font-size: 0.82rem;
      text-align: center;
      padding: 10px;
    }

    .novel h2 {
      font-size: 1.35rem;
      letter-spacing: 0;
      line-height: 1.2;
      margin-bottom: 10px;
    }

    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .chip {
      min-height: 28px;
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0 10px;
      color: var(--muted);
      background: #fbfbf9;
      font-size: 0.86rem;
    }

    .volume-list {
      display: grid;
      gap: 8px;
    }

    .volume-row {
      display: grid;
      grid-template-columns: 48px 1fr auto;
      gap: 12px;
      align-items: center;
      min-height: 48px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }

    .volume-row strong {
      overflow-wrap: anywhere;
    }

    .index {
      color: var(--accent-dark);
      font-weight: 800;
    }

    .count {
      color: var(--muted);
      font-size: 0.88rem;
      white-space: nowrap;
    }

    .empty-state {
      min-height: 260px;
      display: grid;
      place-items: center;
      border: 1px dashed #c5cbc7;
      border-radius: 8px;
      color: var(--muted);
      text-align: center;
      padding: 28px;
    }

    .message {
      margin-top: 14px;
      color: var(--muted);
      overflow-wrap: anywhere;
    }

    .message.error { color: var(--warn); }

    @keyframes spin { to { transform: rotate(360deg); } }

    @media (max-width: 820px) {
      main { width: min(100% - 24px, 680px); padding-top: 18px; }
      header { align-items: flex-start; flex-direction: column; }
      .status { justify-content: flex-start; text-align: left; }
      .layout { grid-template-columns: 1fr; }
    }

    @media (max-width: 520px) {
      .actions { grid-template-columns: 1fr; }
      .novel { grid-template-columns: 84px 1fr; }
      .cover { width: 84px; }
      .volume-row { grid-template-columns: 40px 1fr; }
      .count { grid-column: 2; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div class="brand">
        <img src="/logo.png" alt="">
        <div>
          <h1>webnovel2kindle</h1>
          <p class="subtitle">Central Novel para EPUB</p>
        </div>
      </div>
      <div id="status" class="status">Pronto</div>
    </header>

    <div class="layout">
      <section class="panel">
        <form id="form" class="form">
          <label>
            Link da obra
            <input id="url" name="url" type="url" required placeholder="https://centralnovel.com/series/...">
          </label>
          <label>
            Volume
            <select id="volume" name="volume" disabled>
              <option value="">Analise uma obra primeiro</option>
            </select>
          </label>
          <label>
            Pasta de saida
            <input id="outputDir" name="outputDir" value="dist">
          </label>
          <div class="actions">
            <button id="scanButton" class="secondary" type="button">Analisar</button>
            <button id="exportButton" class="primary" type="submit" disabled>Gerar EPUB</button>
          </div>
        </form>
        <p id="message" class="message"></p>
      </section>

      <section id="results">
        <div class="empty-state">Cole um link da Central Novel para ver os volumes.</div>
      </section>
    </div>
  </main>

  <script>
    const form = document.querySelector("#form");
    const urlInput = document.querySelector("#url");
    const volumeSelect = document.querySelector("#volume");
    const outputDirInput = document.querySelector("#outputDir");
    const scanButton = document.querySelector("#scanButton");
    const exportButton = document.querySelector("#exportButton");
    const statusNode = document.querySelector("#status");
    const messageNode = document.querySelector("#message");
    const resultsNode = document.querySelector("#results");

    let scannedUrl = "";

    scanButton.addEventListener("click", scanNovel);
    form.addEventListener("submit", exportVolume);

    async function scanNovel() {
      const url = urlInput.value.trim();
      if (!url) return setMessage("Informe o link da obra.", true);

      setBusy(true, "Analisando obra...");
      setMessage("");
      try {
        const data = await request("/api/scan", { url });
        scannedUrl = url;
        renderNovel(data);
        setMessage(`${data.volumes.length} volume(s), ${data.chapter_count} capitulo(s).`);
      } catch (error) {
        renderEmpty();
        setMessage(error.message, true);
      } finally {
        setBusy(false);
      }
    }

    async function exportVolume(event) {
      event.preventDefault();
      const url = urlInput.value.trim() || scannedUrl;
      const volume = volumeSelect.value;
      if (!url || !volume) return setMessage("Analise a obra e escolha um volume.", true);

      setBusy(true, "Gerando EPUB...");
      setMessage("Baixando capitulos e montando o arquivo.");
      try {
        const data = await request("/api/export", {
          url,
          volume,
          output_dir: outputDirInput.value.trim()
        });
        setMessage(`${data.message} ${data.path}`);
      } catch (error) {
        setMessage(error.message, true);
      } finally {
        setBusy(false);
      }
    }

    async function request(path, payload) {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Falha na requisicao.");
      return data;
    }

    function renderNovel(data) {
      const cover = data.metadata.cover_url
        ? `<img class="cover" src="${escapeAttr(data.metadata.cover_url)}" alt="">`
        : `<div class="cover empty">Sem capa</div>`;
      const meta = [
        data.metadata.author,
        data.metadata.status,
        data.metadata.type,
        data.metadata.release_year,
        ...data.metadata.genres
      ].filter(Boolean);

      volumeSelect.innerHTML = data.volumes
        .map(volume => {
          const label = escapeHtml(volume.index + ". " + volume.title);
          return `<option value="${volume.index}">${label}</option>`;
        })
        .join("");
      volumeSelect.disabled = data.volumes.length === 0;
      exportButton.disabled = data.volumes.length === 0;

      resultsNode.innerHTML = `
        <div class="panel">
          <div class="novel">
            ${cover}
            <div>
              <h2>${escapeHtml(data.title)}</h2>
              <div class="meta">
                ${meta.map(item => `<span class="chip">${escapeHtml(item)}</span>`).join("")}
                <span class="chip">${data.chapter_count} capitulo(s)</span>
              </div>
            </div>
          </div>
          <div class="volume-list">
            ${data.volumes.map(volume => `
              <div class="volume-row">
                <span class="index">#${volume.index}</span>
                <strong>${escapeHtml(volume.title)}</strong>
                <span class="count">${volume.chapter_count} capitulo(s)</span>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    function renderEmpty() {
      volumeSelect.innerHTML = `<option value="">Analise uma obra primeiro</option>`;
      volumeSelect.disabled = true;
      exportButton.disabled = true;
      resultsNode.innerHTML = `
        <div class="empty-state">Cole um link da Central Novel para ver os volumes.</div>
      `;
    }

    function setBusy(isBusy, label = "Pronto") {
      statusNode.textContent = isBusy ? label : "Pronto";
      statusNode.classList.toggle("busy", isBusy);
      scanButton.disabled = isBusy;
      exportButton.disabled = isBusy || volumeSelect.disabled;
    }

    function setMessage(message, isError = false) {
      messageNode.textContent = message;
      messageNode.classList.toggle("error", isError);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function escapeAttr(value) {
      return escapeHtml(value);
    }
  </script>
</body>
</html>
"""
