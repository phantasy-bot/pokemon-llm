import struct
import socket

def _flush_socket(sock) -> None:
    """
    Drain any pending data from sock so that our next recv()
    only sees the fresh response to the command we send.
    
    Handles dead sockets gracefully to prevent exceptions during cleanup.
    """
    # Store original timeout and use non-blocking via timeout=0
    try:
        original_timeout = sock.gettimeout()
    except (OSError, socket.error):
        return  # Socket already dead, nothing to flush
    
    try:
        sock.settimeout(0)  # Non-blocking mode via zero timeout
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
        except (BlockingIOError, socket.timeout, OSError):
            # No more data to read, or socket error - both OK for flush
            pass
    except (OSError, socket.error):
        # Socket died during flush - acceptable
        pass
    finally:
        # Go back to original timeout mode
        try:
            sock.settimeout(original_timeout)
        except (OSError, socket.error):
            pass  # Socket may have died


def readrange(sock, address: str, length: str) -> bytes:
    _flush_socket(sock)
    cmd = f"READRANGE {address} {length}\n".encode('utf-8')
    sock.sendall(cmd)
    hdr = sock.recv(4)
    if len(hdr) < 4:
        raise RuntimeError("socket closed during READRANGE header")
    size = struct.unpack(">I", hdr)[0]
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise RuntimeError("socket closed mid-dump")
        data.extend(chunk)
    return bytes(data)


def send_command(sock, cmd: str) -> str:
    _flush_socket(sock)
    sock.sendall((cmd.strip() + "\n").encode('utf-8'))
    data = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("socket closed before full response")
        data.extend(chunk)
        if b"\n" in chunk:
            break
    return data.decode('utf-8').rstrip("\n")
