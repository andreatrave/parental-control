@echo off
REM Parental Control - Service Wrapper
REM Used by NSSM or Task Scheduler to run the background monitor.
REM Update PYTHON below if "where python" shows a different path.

cd /d "%~dp0"

REM ---------- UPDATE THIS LINE IF NEEDED ----------
set PYTHON=python.exe
REM ------------------------------------------------
REM  If the above fails, replace with full path, e.g.:
REM  set PYTHON=C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe

"%PYTHON%" parental_control_service.py
