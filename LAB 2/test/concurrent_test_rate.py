import threading
import socket
import time
import sys

def make_request(host, port, path="/"):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode('utf-8'))
        resp = b""
        while True:
            data = s.recv(4096)
            if not data:
                break
            resp += data
        s.close()
        return True, resp
    except Exception as e:
        print("Request error:", e)
        return False, None

def worker(host, port, path, results, idx, delay=0.0):
    time.sleep(delay)
    ok, resp = make_request(host, port, path)
    results[idx] = ok

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python concurrent_test_rate.py <host> <port> <num_requests> <client_type>")
        print("client_type: low | high (sub limit / above limit)")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    num_requests = int(sys.argv[3])
    client_type = sys.argv[4]

    threads = []
    results = [False] * num_requests

    # Setam delay intre cereri in functie de tipul clientului
    delay = 0.25 if client_type == "low" else 0.05

    start = time.time()
    for i in range(num_requests):
        t = threading.Thread(target=worker, args=(host, port, "/", results, i, i * delay))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    end = time.time()

    success = sum(1 for r in results if r)
    print(f"Client '{client_type}': Requests={num_requests}, Success={success}, Time elapsed={end - start:.3f} sec")
