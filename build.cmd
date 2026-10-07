@echo off
rem Build of the SAPI-1 port: build\fxs4.com (CP/M), build\fxs4.hex (Intel HEX, from 0100h), build\fxs4.sym.
rem PASMO can be set in the environment, default E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe.
setlocal
cd /d "%~dp0"
if "%PASMO%"=="" set PASMO=E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe
if not exist build mkdir build
python tools\make_tables.py || exit /b 1
pushd sapi
"%PASMO%" --bin fxs4_sapi.asm ..\build\fxs4.com ..\build\fxs4.sym || (popd & exit /b 1)
"%PASMO%" --hex fxs4_sapi.asm ..\build\fxs4.hex || (popd & exit /b 1)
popd
python tools\check_port.py || exit /b 1
