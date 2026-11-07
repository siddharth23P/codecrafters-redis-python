import socket
import selectors, socket
from .parser import RespParser, Incomplete
sel = selectors.DefaultSelector()

parser = RespParser()
buffers = {}

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
    buf = buffers.get(conn, b"") + data
    while buf:
        try: 
            cmd, used = parser.parse(buf)
        except Incomplete:
            break
        buf = buf[used:]
        conn.sendall(execute(cmd))
    buffers[conn] = buf
    
def execute(cmd):
    name, args = cmd[0].decode().lower(), cmd[1:]
    if name == "ping":
        return b"+PONG\r\n"
    if name == "echo" and args:
        arg = args[0]
        return b"$%d\r\n%s\r\n" % (len(arg), arg)
    return b"-ERR unknown command\r\n"
    
def main():
    print("Running Redis Server")
    server = socket.create_server(("localhost", 6379), reuse_port=True)
    server.setblocking(False)
    sel.register(server,selectors.EVENT_READ, accept)
    while True:
        for key, _ in sel.select():
            # print(key, _)
            key.data(key.fileobj)
        

if __name__ == "__main__":
    main()
