venv\Scripts\pyinstaller.exe --onefile AlbianWarpClient.py --icon aw.ico --distpath AlbianWarpClient_64bit/
rm -rf build
venv32\Scripts\pyinstaller.exe --onefile AlbianWarpClient.py --icon aw.ico --distpath AlbianWarpClient_32bit/
rm -rf build
copy "example_albianwarp.cfg" "AlbianWarpClient_64bit/albianwarp.cfg"
copy "example_albianwarp.cfg" "AlbianWarpClient_32bit/albianwarp.cfg"
