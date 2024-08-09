# Meshtastic Scraper

## HARDWARE TUTORIAL FROM SCRATCH
1. Install firmware to board: https://flasher.meshtastic.org (or other method)
2. Connect to board via bluetooth using the meshtastic app on the same PC that it is connect to via serial
- ^ may require 'forgetting' the device on bluetooth settings if you have already connected to it on the PC before the reset/firmware flash

3. Set lora.region to EU_868 (or relevent region)
4. Disconnect bluetooth to node 
5. Should be ready: update config.ini accordingly and in terminal run: python3 run.py


## SOFTWARE TUTORIAL FROM SCRATCH
1. CREATE the pip venv:
`$ python3 -m venv meshScraperEnv`

2. ACTIVATE IT
`$ source meshScraperEnv/bin/activate`

3. INSTALL packadges into it
`$ pip install -r requirements.txt`

4. Make a new directory and clone the git repo:
`$ git clone https://github.com/edproudlove/meshtasticScraper.git`

5. with the env activated run the run.py file:
`$ python3 run.py`


### COMPATABLE BOARD FIRMWARE VERSIONS (Which firmware versions the run.py code works for - only using Beta/Stable versions)
- 2.3.10 (2.3.10.d19607b) -> ✅ WORKS Occasionally getting strange outputs in the serial data - may have just been a one off
- 2.3.11 (2.3.11.2740a56) -> ✅ WORKS 
- 2.3.12 (2.3.12.24458a7) -> ✅ WORKS  
- 2.3.13 (2.3.13.83f5ba0) -> ✅ WORKS 

###### Version 2.3.15 and above add colour to the serial debug - requires removal using utils.remove_ansi_escape()
- 2.3.15 (2.3.15.deb7c27) -> ✅ WORKS
- 2.4.0 (2.4.0.46d7b82) ->  ✅WORKS

### PYTHON MESHTASTIC CLI VERSIONS (Will have a reccomended version in the requirements.txt): 
- 2.3.11 -> ❌ FAILS (client.sendTraceRotue() and client.sendData() do not have a hoplimit argument as input)
- 2.3.12 -> ❌ FAILS (client.sendTraceRotue() and client.sendData() do not have a hoplimit argument as input)
- 2.3.13 -> ❌ FAILS (client.sendTraceRotue() and client.sendData() do not have a hoplimit argument as input)

- 2.3.14 -> ✅ WORKS sendTraceRoute hoplimit fixed in the changelogs: https://github.com/meshtastic/python/releases


### TODO LOG 

#### DONE/OUTDATED
- Find the Bluetooth device we are connected to over serial and clear its nodeDB 
- The BLE will send traceRoutes to each Node in meshScraper.unique_id_arr         
- Response will be input into a NEW file (need to change the self.filename)       
- Make finding the BLE scanner dynamic                                            
- Continuous mode or just run it once....                                        
- Don't need to wait the entire response time if all the Nodes have been communicated with... (some sort of success)
- Implement my own timeouts / sendTraceRoute                                                     
- Change the RX power antenna etc                                                 
- Add in how long we waited for a response for each Node?                         
- Will it always accept Bluetooth connection? What about the pin/restarts? Requires the PC connected first if the node has been reset/new firmware -> also requires lora.region set
- Change file formatting
- Could have a sign for if the traceroute has begun, -> start a timer, if we do not receive a traceRoute with the relevant id then ACK = 0
- Fix the Time-Out of the BLE interface is unreliable -> if we get a response tell the BLE to move on -> Sometimes it hangs for a long time 

#### DOING
- Document which firmware versions the code will work for (2.4.0 etc) -> same for versions of Python CLI
- Flash most recent firmware and go through every step to make documentation / tutorial
  -> add conda/env stuff setup from fresh PC

#### TODO:
- How should the device be configured ... on running the script could send a config.yml 
- Make the code modular -> can just download from GitHub and run it (pip install/ .sh etc) or tutorial
- Logging rather than prints -> need to get rid of the meshtastic logs 
- DEBUG settings for if it needs to be printed: Debug or Standby Mode 
- Implement sendText instead because traceroute is only working for my nodes?
- Might need a file ID or test ID because it's hard to tell what file and results are a pair
- Sort out config imports into both files
