@echo off
rem Build of the SAPI-1 port: build\fxs4.com (CP/M), build\fxs4.hex (Intel HEX, from 0100h), build\fxs4.sym.
rem "build.cmd diag": build\fxs4diag.com, .hex - nothing is drawn while it runs (only the start screen
rem and palette changes), to find the cause of snow on a real CGA-1V.
rem PASMO can be set in the environment, default E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe.
setlocal
cd /d "%~dp0"
if "%PASMO%"=="" set PASMO=E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe
set NAME=fxs4
set DIAG=0
if /i "%1"=="diag" (
	set NAME=fxs4diag
	set DIAG=1
)
if not exist build mkdir build
python tools\make_tables.py || exit /b 1
pushd sapi
"%PASMO%" --equ DIAG=%DIAG% --bin fxs4_sapi.asm ..\build\%NAME%.com ..\build\%NAME%.sym || (popd & exit /b 1)
"%PASMO%" --equ DIAG=%DIAG% --hex fxs4_sapi.asm ..\build\%NAME%.hex || (popd & exit /b 1)
popd
python tools\check_port.py %NAME% || exit /b 1
