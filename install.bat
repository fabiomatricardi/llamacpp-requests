echo off
echo Downloading the Language model...
wget.exe https://hf-mirror.com/bartowski/Qwen_Qwen3-0.6B-GGUF/resolve/main/Qwen_Qwen3-0.6B-Q8_0.gguf -nv --show-progress
echo Unzipping the llama.cpp binaries...
tar -xf llama-b5410-bin-win-cpu-x64.zip
echo Creating Virtual environment
python -m venv venv
echo Activating venv
call .\venv\Scripts\activate.bat
echo Installing dependencies
pip install easygui pypdf requests
start cmd.exe /c llama-server.exe -m Qwen_Qwen3-0.6B-Q8_0.gguf -c 12000 -ngl 0
python qwen3-0.6_v4.py
PAUSE
