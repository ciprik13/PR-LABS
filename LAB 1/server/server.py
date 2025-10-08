import socket
import os
import sys
import urllib.parse

PORT = 8080
HOST = 'localhost'

MIME_TYPES = {
    '.html': 'text/html',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
}

def get_content_type(file_path):
    _, extension = os.path.splitext(file_path)
    return MIME_TYPES.get(extension.lower(), 'application/octet-stream')

def generate_directory_listing(dir_path, url_path):
    items = sorted(os.listdir(dir_path))
    html = f"<html><body><h1>My Library {url_path}</h1><ul>"
    
    if url_path != '/':
        html += "<li><a href='..'>../</a></li>"
    
    for item in items:
        item_path = os.path.join(dir_path, item)
        encoded_item = urllib.parse.quote(item)
        if os.path.isdir(item_path):
            html += f"<li><a href='{encoded_item}/'>{item}/</a></li>"
        else:
            html += f"<li><a href='{encoded_item}'>{item}</a></li>"
    
    html += "</ul></body></html>"
    return html.encode('utf-8')

def start_server(content_dir, host=HOST, port=PORT):
    if not os.path.isdir(content_dir):
        print(f"Error: Directory '{content_dir}' does not exist!")
        sys.exit(1)
    
    content_dir = os.path.abspath(content_dir)
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    
    print(f"Server started on http://{host}:{port}")
    print(f"Serving files from: {content_dir}/")
    
    try:
        while True:
            client_connection, client_address = server_socket.accept()
            
            try:
                request = client_connection.recv(1024).decode('utf-8')
                request_parts = request.split('\n')[0].split()
                
                if len(request_parts) >= 2:
                    path = urllib.parse.unquote(request_parts[1])
                    print(f"Request: {path}")
                    
                    if path == '/':
                        path = '/'
                    
                    file_path = os.path.join(content_dir, path.lstrip('/'))
                    
                    if not file_path.startswith(content_dir):
                        response = "HTTP/1.1 403 Forbidden\r\n\r\n"
                        client_connection.sendall(response.encode('utf-8'))
                    
                    elif os.path.isdir(file_path):
                        file_content = generate_directory_listing(file_path, path)
                        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(file_content)}\r\n\r\n"
                        client_connection.sendall(response.encode('utf-8') + file_content)
                    
                    elif os.path.isfile(file_path):
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        
                        content_type = get_content_type(file_path)
                        response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(file_content)}\r\n\r\n"
                        client_connection.sendall(response.encode('utf-8') + file_content)
                    
                    else:
                        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 Not Found</h1>"
                        client_connection.sendall(response.encode('utf-8'))
            
            except Exception as e:
                print(f"Error: {e}")
            
            finally:
                client_connection.close()
    
    except KeyboardInterrupt:
        print("\nServer stopped")
        server_socket.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python server.py <content_directory>")
        sys.exit(1)
    
    start_server(sys.argv[1])