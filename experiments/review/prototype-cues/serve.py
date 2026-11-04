"""Serve only the throwaway prototype files; no media or repository access."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
ROOT = Path(__file__).resolve().parent
FILES = {'/': 'index.html', '/index.html': 'index.html', '/live.html': 'live.html', '/live.js': 'live.js', '/recordings.json': 'recordings.json'}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        name = FILES.get(urlsplit(self.path).path)
        if name is None:
            self.send_error(404)
            return
        data = (ROOT / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json'}[Path(name).suffix])
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.end_headers()
        self.wfile.write(data)
if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--bind',default='127.0.0.1');p.add_argument('--port',type=int,default=8075);args=p.parse_args()
    print(f'Prototype: http://{args.bind}:{args.port}/live.html',flush=True)
    ThreadingHTTPServer((args.bind,args.port),Handler).serve_forever()
