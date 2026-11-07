set extra=cpu
where nvidia-smi >nul 2>&1
if errorlevel 1 goto start

nvidia-smi -L >nul 2>&1
if errorlevel 1 goto start

REM Checking if user opted into cuda in config
for /F "tokens=* USEBACKQ" %%g in (`python -c "import config; print('cuda' if config.enable_cuda else 'cpu')"`) do (set extra=%%g)

if %extra% == cpu goto start

REM Checking if cuda toolkit is installed
nvcc --version >nul 2>&1
if errorlevel 1 goto download

set "ARGOS_DEVICE_TYPE=cuda"
goto start

:download
echo "To use CUDA for translation, download and install the 12.x version: https://developer.nvidia.com/cuda-toolkit-archive"
exit /b 1

:start
uv sync --extra %extra% && uv run --extra %extra% setup.py && uv run --extra %extra% main.py