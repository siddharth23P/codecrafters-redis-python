import socket
import selectors, socket

sel = selectors.DefaultSelector()

def accept(server):
    conn, _ = server.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, handle)
    
def handle(conn):
    data = conn.recv(1024)
    if not data:
        sel.unregister(conn)
        conn.close()
        return
    conn.sendall(b"+PONG\r\n")
    
def main():
    print("Running Redis Server")
    server = socket.create_server(("localhost", 6379), reuse_port=True)
    server.setblocking(False)
    sel.register(server,selectors.EVENT_READ, accept)
    while True:
        for key, _ in sel.select():
            key.data(key.fileobj)
        

if __name__ == "__main__":
    main()
