from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("Метод:", self.command)
        print("Ціль запиту:", self.path)
        print("Заголовки:\n", self.headers)

        path = urlsplit(self.path).path
        pages = {
            "/": "Вітаємо! Це навчальний HTTP-сервер.",
            "/test": "Тестова сторінка.",
            "/info": "Сервер створено засобами стандартної бібліотеки Python.",
        }

        status = 200 if path in pages else 404
        text = pages.get(path, "Сторінку не знайдено.")
        body = text.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
