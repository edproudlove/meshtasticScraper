# Meshtastic Scraper

## HARDWARE SETUP
1. Install firmware to board: https://flasher.meshtastic.org (or other method)
2. Connect to board via bluetooth using the meshtastic app on the same PC that it is connect to via serial (may require 'forgetting' the device on PC bluetooth settings if you have already connected to it via bluetooth on the PC before the reset or firmware flash)

3. Set lora.region to EU_868 (or relevent region - remember to change config.ini / filename)
4. Disconnect bluetooth to node 
5. Should be ready: update config.ini accordingly and in terminal run: python3 run.py

## SOFTWARE SETUP
1. Create the pip venv: (change meshScrapeEnv to whatever name you want)
```
$ python3 -m venv meshScraperEnv
```

2. Activate it
```
$ source meshScraperEnv/bin/activate
```

3. INSTALL packadges into it
```
$ pip install -r requirements.txt
```

4. Make a new directory and clone the git repo:
```
$ git clone https://github.com/edproudlove/meshtasticScraper.git
```

5. with the env activated run the run.py file:
```
$ python3 run.py
```

### COMPATABLE BOARD FIRMWARE VERSIONS (Which firmware versions the run.py code works for - only considering Beta/Stable versions)
- 2.3.10 (2.3.10.d19607b) -> ✅ WORKS
- 2.3.11 (2.3.11.2740a56) -> ✅ WORKS 
- 2.3.12 (2.3.12.24458a7) -> ✅ WORKS  
- 2.3.13 (2.3.13.83f5ba0) -> ✅ WORKS 

###### Version 2.3.15 and above add colour to the serial debug - requires removal using utils.remove_ansi_escape()
- 2.3.15 (2.3.15.deb7c27) -> ✅ WORKS
- 2.4.0 (2.4.0.46d7b82) ->  ✅ WORKS
- 2.4.1 (2.4.1.394e0e1) ->  ✅ WORKS

### PYTHON MESHTASTIC CLI VERSIONS (Will have a reccomended version in the requirements.txt): 
- 2.3.11 -> ❌ FAILS 
- 2.3.12 -> ❌ FAILS (client.sendTraceRotue() and client.sendData() do not have a hoplimit argument as input)
- 2.3.13 -> ❌ FAILS (client.sendTraceRotue() and client.sendData() do not have a hoplimit argument as input)

###### In version 2.3.13 and below client.sendTraceRotue() and client.sendData() do not have a hoplimit argument as input - if you don't specify the hoplimit 
- 2.3.14 -> ✅ WORKS (sendTraceRoute hoplimit fixed in the changelogs: https://github.com/meshtastic/python/releases)

## TODO LOG 

#### DONE/OUTDATED
- Find the Bluetooth device we are connected to over serial and clear its nodeDB 
- The BLE will send traceRoutes to each Node in meshScraper.unique_id_arr         
- Response will be input into a NEW file (need to change the self.filename)       
- Make finding the BLE scanner dynamic                                            
- Add a Continuous mode or just run it once                                         
- Don't need to wait the entire response time if all the Nodes have been communicated with - end early if all are accounted for
- Change the RX power antenna etc                                                 
- Add in how long we waited for a response for each Node - not being put into the results anymore but still in mesh_scraper                         
- Will it always accept Bluetooth connection? -> Requires the PC connected first if the node has been reset/new firmware -> also requires lora.region set (in hardware tutorial)
- Fix the Time-Out of the BLE interface is unreliable -> if we get a response tell the BLE to move on
- Implement own timeouts / sendTraceRoute - Dont use CLI ^^
- Flash most recent firmware and go through every step to make documentation / tutorial + conda/env stuff setup from fresh PC
- Add a test ID because - it's hard to tell what file and results are a pair

#### DOING
- Document which firmware versions the code will work for -> same for versions of Python CLI
- Logging rather than prints - remove meshtastic and bleak logs
- DEBUG settings for if it needs to be printed: Debug or Standby Mode 

#### TODO:
- How should the device be configured? On running the script could send a config.yml: https://meshtastic.org/docs/software/python/cli/ -> meshtastic --configure example_config.yaml
- Improve modularity -> can just clone from GitHub and run it (install.sh etc)
- Implement sendText instead of traceroute? 
- Find / set band dynamically 
- Handle multiple serial ports