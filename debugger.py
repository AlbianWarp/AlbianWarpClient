from CaosEvolution import CI
import time

while True:
	debug = CI.ExecuteCaos("DBG: POLL").Content
	if len(debug) > 1:
		print(debug, end="")
	time.sleep(1)