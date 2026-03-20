#!/usr/bin/env python3
"""Генерация Python gRPC stubs из rust_core/proto/system_control.proto.
Запуск из корня репозитория: python scripts/generate_proto.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_DIR = ROOT / "rust_core" / "proto"
OUT_DIR = ROOT / "ai_core" / "jarvis_ai" / "proto"
PROTO_FILE = PROTO_DIR / "system_control.proto"

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{PROTO_DIR.parent}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        str(PROTO_FILE),
    ]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("Generated:", list(OUT_DIR.glob("*.py")))

if __name__ == "__main__":
    main()
