import socket
import os
import sys
import urllib.parse
import threading
import time

PORT = 8080
HOST = "0.0.0.0"

MIME_TYPES = {
    '.html': 'text/html',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
}

request_counter = {}
counter_lock = threading.Lock()

def get_content_type(file_path):
    _, extension = os.path.splitext(file_path)
    return MIME_TYPES.get(extension.lower())

def generate_directory_listing(dir_path, url_path):
    items = sorted(os.listdir(dir_path))
    html = f"<html><head><title>Directory listing for {url_path}</title></head><body>"
    html += f"<h2>Directory listing for {url_path}</h2>"
    html += "<table border='1'><tr><th>File / Directory</th><th>Hits</th></tr>"

    if url_path != '/':
        parent_path = os.path.dirname(url_path.rstrip('/'))
        if not parent_path:
            parent_path = '/'
        html += f"<tr><td><a href='{parent_path}'>../</a></td><td></td></tr>"

    for item in items:
        if item.startswith("."):
            continue

        item_path = os.path.join(dir_path, item)
        encoded_item = urllib.parse.quote(item)
        display_name = item + '/' if os.path.isdir(item_path) else item
        link = f"{encoded_item}/" if os.path.isdir(item_path) else encoded_item

        with counter_lock:
            hits = request_counter.get(item_path, 0)

        html += f"<tr><td><a href='{link}'>{display_name}</a></td><td>{hits}</td></tr>"

    html += "</table></body></html>"
    return html.encode('utf-8')

def handle_client(client_connection, client_address, content_dir, simulate_delay=True):
    try:
        request = client_connection.recv(1024).decode('utf-8')
        if not request:
            client_connection.close()
            return

        first_line = request.split('\n')[0]
        parts = first_line.split()
        if len(parts) < 2:
            client_connection.close()
            return

        path = urllib.parse.unquote(parts[1])
        if simulate_delay:
            time.sleep(1)

        print(f"[{threading.current_thread().name}] Request from {client_address}: {path}")

        file_path = os.path.join(content_dir, path.lstrip('/'))
        if not file_path.startswith(content_dir):
            response = "HTTP/1.1 403 Forbidden\r\n\r\nForbidden".encode('utf-8')
            client_connection.sendall(response)
            return

        if os.path.isdir(file_path):
            with counter_lock:
                request_counter[file_path] = request_counter.get(file_path, 0) + 1
            content = generate_directory_listing(file_path, path)
            response_headers = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(content)}\r\n\r\n".encode('utf-8')
            client_connection.sendall(response_headers + content)

        elif os.path.isfile(file_path):
            content_type = get_content_type(file_path)
            if content_type is None:
                response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 Not Found</h1>".encode('utf-8')
                client_connection.sendall(response)
                return

            with counter_lock:
                request_counter[file_path] = request_counter.get(file_path, 0) + 1

            with open(file_path, 'rb') as f:
                content = f.read()

            response_headers = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(content)}\r\n\r\n".encode('utf-8')
            client_connection.sendall(response_headers + content)

        else:
            response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 Not Found</h1>".encode('utf-8')
            client_connection.sendall(response)

    except Exception as e:
        print(f"[{threading.current_thread().name}] Error: {e}")
    finally:
        client_connection.close()

def start_server(content_dir, host=HOST, port=PORT, simulate_delay=True):
    if not os.path.isdir(content_dir):
        print(f"Error: Directory '{content_dir}' does not exist!")
        sys.exit(1)

    content_dir = os.path.abspath(content_dir)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(50)

    print(f"Multithreaded server started on http://{host}:{port}")
    print(f"Serving files from: {content_dir}")

    try:
        while True:
            client_connection, client_address = server_socket.accept()
            t = threading.Thread(target=handle_client, args=(client_connection, client_address, content_dir, simulate_delay), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server_socket.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python server_multithreaded.py <content_directory> [port]")
        sys.exit(1)

    port = PORT
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])

    start_server(sys.argv[1], port=port, simulate_delay=True)
