@echo off
cd /d "%~dp0\.."
if not exist "ai_core\jarvis_ai\proto" mkdir "ai_core\jarvis_ai\proto"
if exist "ai_core\venv\Scripts\python.exe" (
  ai_core\venv\Scripts\python.exe -m grpc_tools.protoc -I rust_core --python_out=ai_core\jarvis_ai\proto --grpc_python_out=ai_core\jarvis_ai\proto rust_core\proto\system_control.proto
) else (
  python -m grpc_tools.protoc -I rust_core --python_out=ai_core\jarvis_ai\proto --grpc_python_out=ai_core\jarvis_ai\proto rust_core\proto\system_control.proto
)
echo Done. Check ai_core\jarvis_ai\proto for *_pb2.py
