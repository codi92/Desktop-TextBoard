@echo off
REM Batch file to start Desktop TextBoard with pythonw (no console window)
REM Place a shortcut to this file in the Startup folder
cd C:\Users\codi9\Desktop-TextBoard
start C:\Users\codi9\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\pythonw.exe "desktop_textboard.py"
REM If you want to see the console, use python or python3 instead of pythonw.exe
