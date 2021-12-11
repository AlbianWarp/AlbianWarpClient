venv\Scripts\pyinstaller.exe --onefile AlbianWarpClient.py --icon aw.ico --distpath AlbianWarpClient_64bit/
Remove-Item -Recurse -Force build
venv32\Scripts\pyinstaller.exe --onefile AlbianWarpClient.py --icon aw.ico --distpath AlbianWarpClient_32bit/
Remove-Item -Recurse -Force build
copy "example_albianwarp.cfg" "AlbianWarpClient_64bit/albianwarp.cfg"
copy "example_albianwarp.cfg" "AlbianWarpClient_32bit/albianwarp.cfg"
Compress-Archive -Update AlbianWarpClient_64bit/ AlbianWarpClient_64bit.zip
Compress-Archive -Update AlbianWarpClient_32bit/ AlbianWarpClient_32bit.zip