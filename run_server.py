import uvicorn
import socket
import sys
import os

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    
    print("=" * 65)
    print("[*] AlphabetAI Attendance System Server Starting...")
    print("=" * 65)
    print(f"Local Access:   http://localhost:{port}")
    print(f"Android Access: http://{local_ip}:{port}")
    print("=" * 65)
    print("Ensure your Android device and this PC are on the same Wi-Fi.")
    print("=" * 65 + "\n")
    
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, reload=False)
