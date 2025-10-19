import socket
import sys
import os
import urllib.parse

def http_client(host, port, url_path, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    encoded_path = urllib.parse.quote(url_path, safe='/')
    
    request = f"GET {encoded_path} HTTP/1.1\r\n"
    request += f"Host: {host}:{port}\r\n"
    request += "Connection: close\r\n"
    request += "\r\n"
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    client_socket.sendall(request.encode('utf-8'))
    
    response = b""
    while True:
        data = client_socket.recv(4096)
        if not data:
            break
        response += data
    
    client_socket.close()
    
    header_end = response.find(b"\r\n\r\n")
    if header_end == -1:
        print("Error: Invalid HTTP response")
        return
    
    header = response[:header_end].decode('utf-8')
    body = response[header_end + 4:]
    
    content_type = ""
    for line in header.split('\r\n'):
        if line.lower().startswith('content-type:'):
            content_type = line.split(':', 1)[1].strip()
            break
    
    if 'text/html' in content_type:
        print(body.decode('utf-8'))
    elif 'image/png' in content_type or 'application/pdf' in content_type:
        filename = os.path.basename(url_path.rstrip('/'))
        if not filename:
            filename = 'index.html'
        
        filepath = os.path.join(save_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(body)
        
        print(f"File saved: {filepath} ({len(body)} bytes)")
    else:
        print(f"Unknown content type: {content_type}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python client.py <server_host> <server_port> <url_path> <save_directory>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    url_path = sys.argv[3]
    save_dir = sys.argv[4]
    
    http_client(host, port, url_path, save_dir)