from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib import parse
from urllib.parse import urlparse, parse_qs
import crud_clientes
import crud_periodos          # NUEVO

import json

port = 3000
crudClientes = crud_clientes.crud_clientes()
crudPeriodos = crud_periodos.crud_periodos()      # NUEVO

class miServidor(SimpleHTTPRequestHandler):

    def _cabeceras_cors(self):                    # NUEVO (por si abres el HTML con file://)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def do_OPTIONS(self):                         # NUEVO
        self.send_response(204)
        self._cabeceras_cors()
        self.end_headers()

    def do_POST(self):
        longitud = int(self.headers['Content-Length'])
        datos = self.rfile.read(longitud)
        datos = datos.decode("utf-8")
        datos = parse.unquote(datos)
        datos = json.loads(datos)

        if urlparse(self.path).path == "/periodos":          # NUEVO
            respuesta = crudPeriodos.administrar(datos)
        else:                                                # clientes (como lo tenías)
            respuesta = {'msg': crudClientes.administrar(datos)}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self._cabeceras_cors()
        self.end_headers()
        self.wfile.write(json.dumps(respuesta, default=str).encode("utf-8"))

    def do_GET(self):
        urlParse = urlparse(self.path)
        qs = parse_qs(urlParse.query)

        if urlParse.path == "/clientes":
            buscar = qs.get('buscar', [''])[0]
            print(buscar)
            datos = crudClientes.consultar(buscar)
            self.send_response(200)
            self.send_header("Content-type", "text/json")
            self._cabeceras_cors()
            self.end_headers()
            self.wfile.write(json.dumps(datos, default=str).encode("utf-8"))

        elif self.path == "/":
            self.path = "/index.html"
            return SimpleHTTPRequestHandler.do_GET(self)

        else:                                                # NUEVO: archivos estáticos
            return SimpleHTTPRequestHandler.do_GET(self)

print(f"Servidor corriendo en el puerto {port}")
server = HTTPServer(("localhost", port), miServidor)
server.serve_forever()
