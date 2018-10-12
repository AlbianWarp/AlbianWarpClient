venv\Scripts\pyinstaller.exe --add-data CAOS.dll;. --onefile AlbianWarpPythonClient.py --icon aw.ico --distpath AlbianWarpPythonClient_64bit/
rm -rf build
venv32\Scripts\pyinstaller.exe --add-data CAOS.dll;. --onefile AlbianWarpPythonClient.py --icon aw.ico --distpath AlbianWarpPythonClient_32bit/
rm -rf build
copy "albianwarp.cfg" "AlbianWarpPythonClient_64bit/albianwarp.cfg"
copy "albianwarp.cfg" "AlbianWarpPythonClient_32bit/albianwarp.cfg"
