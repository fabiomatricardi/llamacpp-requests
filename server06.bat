@ECHO OFF
Color 0B
REM set the absolute paths for the llamacpp-server andh the model
set SRV=C:\Users\FabioMatricardi\Documents\DEV\Qwen3\llamaCPPb5410_CPU
set MODEL=C:\Users\FabioMatricardi\Documents\DEV\COLL_SmollModels
@cls
echo.
echo.
echo.
@echo    //////////////////////////////////////////////////////////////
@echo    /                                                            /
@echo    /               AUTOMATIC START OF LLAMA-SERVER              /
@echo    /                                                            /
@echo    /                            No GPU                          /
@echo    /                                                            /
@echo    /                  Context window by the user                /
@echo    /                                                            /
@echo    //////////////////////////////////////////////////////////////
echo.
echo.
IF "%~1"=="" (
  GOTO default
) ELSE (
  GOTO defined)
:default
ECHO Starting server with 8192 tokens context window...
start cmd.exe /k %SRV%\llama-server.exe -m %MODEL%\Qwen_Qwen3-0.6B-Q8_0.gguf -c 8196
GOTO end
:defined
ECHO Starting server with %1 tokens context window...
start cmd.exe /k %SRV%\llama-server.exe -m %MODEL%\Qwen_Qwen3-0.6B-Q8_0.gguf -c %1
GOTO end
:end
ECHO Server running with Qwen_Qwen3-0.6B-Q8_0.gguf