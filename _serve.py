"""多线程本地静态服务器（python -m http.server 是单线程的，
多模块并发加载 + iframe 嵌套会把服务堵死，导致 E2E 假性挂起）。"""
import http.server, socketserver, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


with Server(('127.0.0.1', PORT), Handler) as httpd:
    print('serving on %d (threaded)' % PORT, flush=True)
    httpd.serve_forever()
