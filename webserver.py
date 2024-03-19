from http.server import BaseHTTPRequestHandler, HTTPServer # Importamos librerías para manejar solicitudes HTTP y servidor
import re # Importamos librería para expresiones regulares
import redis # Importamos librería para interactuar con la base de datos Redis
from http.cookies import SimpleCookie # Importamos librería para manejar cookies
import uuid # Importamos librería para generar identificadores únicos
from urllib.parse import parse_qsl, urlparse # Importamos funciones para analizar URLs
from bs4 import BeautifulSoup # Importamos librería para analizar contenido HTML
# Diccionario que mapea patrones de URL a métodos manejadores
mappings = {
        (r"^/books/(?P<book_id>\d+)$", "get_books"),
        (r"^/$", "index"),
        (r"^/search", "search")
        }

r = redis.StrictRedis(host="localhost", port=6379, db=0)

class WebRequestHandler(BaseHTTPRequestHandler):
     
    @property
    def url(self):
        return urlparse(self.path)

    @property 
    def query_data(self):
        return dict(parse_qsl(self.url.query))

    def search(self):
        query_key = self.query_data.get('q')
        if query_key:
            # Realizar búsqueda en Redis
            matching_books = r.smembers(query_key)
            if matching_books:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                # Mostrar el formulario de búsqueda en la parte superior
                response = b"""
                    <form action="/Nombre del libro a consultar:" method="GET">
                        <label for="q">Nombre del libro a consultar:</label>
                        <input type="text" name="q"/>
                        <input type="submit" value="Buscar ahora"/>
                    </form>
                    <h1>Resultados de la busqueda:</h1>
                    <ul>
                """
                for book_id in matching_books:
                    book_info = r.get(f"book: {book_id.decode()}")
                    if book_info:
                        soup = BeautifulSoup(book_info, 'html.parser')
                        title = soup.find('h2').text
                        response += f"<li><a href='/books/{book_id.decode()}'>{title}</a></li>".encode()
                response += b"</ul>"
                self.wfile.write(response)
                return

        # Si no se encuentran coincidencias
        self.send_response(404)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        # Mostrar el formulario de búsqueda en la parte superior
        error_message = f"""
        <form action="/Nombre del libro a consultar:" method="GET">
            <label for="q">Nombre del libro a consultar: </label>
            <input type="text" name="q" value="{query_key}"/> <!-- Mostrar el término buscado -->
            <input type="submit" value="Buscar ahora"/>
        </form>
        <h1>Al parecer no existe ningun libro registrado en el sitio llamado llamado '{query_key}'</h1>
        """.encode()
        self.wfile.write(error_message)

    def cookies(self):
        return SimpleCookie(self.headers.get("Cookie"))

    def get_session(self):
        cookies = self.cookies()
        session_id = None
        if not cookies:
            session_id = uuid.uuid4()
        else:
            session_id = cookies["session_id"].value
        return session_id
            
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie()
        cookies["session_id"] = session_id
        cookies["session_id"]["max-age"] = 10
        self.send_header("Set-Cookie", cookies.output(header=""))

    def do_GET(self):
        self.url_mapping_response()

    def url_mapping_response(self):
        for pattern, method in mappings:
            match = self.get_params(pattern, self.path)
            if match is not None:
                md = getattr(self, method)
                md(**match)
                return

        self.send_response(404)
        self.end_headers()
        error = f"<h1> Not found </h1>".encode("utf-8")
        self.wfile.write(error)

    def get_params(self, pattern, path):
        match = re.match(pattern, path)
        if match:
            return match.groupdict()

    def get_books(self, book_id):
        session_id = self.get_session()
        book_recommendation = self.get_book_recommendation( str(session_id), book_id)
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        self.end_headers()
        
        book_info = r.get(f"book: {book_id}") or "<h1> El libro que usted esta intentando consultar no esta registrado en el sitio </h1>".encode("utf-8")
        self.wfile.write(book_info)  
        
        response = f"""
        <p> Numero de la Session: {session_id} </p>
        <p> Si te gusto este libro puede que te interese consultar este otro: </p>
        <ul>
        """
        
        if isinstance(book_recommendation, list):
            for recommendation in book_recommendation:
                book_info = r.get(f"book: {recommendation}") 
                soup = BeautifulSoup(book_info, 'html.parser')
                title = soup.find('h2').text
                response += f"<li><a href='/books/{recommendation}'> Te invitamos a consultar el libro: {title}</a></li>"
        else:
            response += f"<li><a href='/'>{book_recommendation} regresa al menú de inicio</a></li>"
        
        response += "</ul>"
        self.wfile.write(response.encode("utf-8"))        
            
    def get_book_recommendation(self, session_id, book_id):
        r.rpush(session_id, book_id)
        books = r.lrange(session_id, 0, 10)
        print(session_id, books)

        all_books = [ i+1 for i in range(10) ]
        new = [b for b in all_books if b not in
               [int(vb.decode()) for vb in books]]

        if len(new) != 0:
            if len(new) < 1:
                return new[0]
            return new[:1]
        else:
            return "Felicidades acabas de consultar absolutamente todos los libros del sitio"

    def index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        with open('html/index.html') as f:
            response = f.read()
        self.wfile.write(response.encode("utf-8"))

if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()
