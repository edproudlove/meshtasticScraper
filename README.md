# Meshtastic Scraper

DONE/OUTDATED
0. Find the Bluetooth device we are connected too over serial and clear its nodeDB -> DONE
1. At a given point / time I want to begin the BLE traceroute stuff                -> DONE
2. The BLE will send traceRoutes to each Node in meshScraper.unique_id_arr         -> DONE
3. Responce will be input into a NEW file (need to change the self.filename)       -> OUTDATED
6. Make finding the BLE scanner dynamic                                            -> DONE
10. continous mode or just run it once....                                         -> DONE
11. READINGS and RESULTS in ONE file -> append results to the end                  -> DONE with 3. 
16. Don't need to wait the entire response time if all the Nodes have been communicated with... (some sort of succsess) -> DONE
14. Implement my own timeouts                                                      -> DONE
7. Change the RX power antenna etc                                                 -> DONE (Would prefer itto be done in a .yml file)
15. Add in how long we waited for a reponse for each Node?                         -> DONE
18. Will it always accept bluetooth conection? what about the pin/restarts         -> DONE: Requires the PC connected first if the node has been reset/new firmware -> also requires lora.region set


DOING
4. Could have a sign for if the traceroute has began, -> start a timer, if we do not recive a traceRoute with the relevent id then ACK = 0
        -> SORT OF: By resetting the nodeDB the timeout should shorten, still need to eliminate false negatives (below)
        -> Removed timeouts from the meshtatsic.BLEInterface.sendTraceRotue(), this will only work on my machine -> Still need to make this dynamic (After an install/git pull)
5. The Time-Out of the BLE interface is unreliable -> if we get a response tell the BLE to move on -> Sometimes it hangs for a long time 
        -> Think this is fixed by 4. but am not sure what was causing it in the first place (shouldnt have been hapening before 4 either)
12. Document which firmware versions the code will work for (2.4.0 etc) - > same for verions of python CLI
19. Flash most recent firmware and go through every step to make documentation / tutorial
        -> add conda/env stuff setup from fresh pc




TODO:
8. How should device be configured ... on running the script could send a config.yml 
9. Make the code modular -> can just download from github and run it (pip install/ .sh etc)
13. Could make a branch of the Python CLI -> or replicate it in a diffrent file? ( How to handle the changes made to the python cli?)
17. Logging rather than prints -> need to get rid of the meshtatsic logs -> DEBGUG settings for if it needs to be printed
20. Debug or Standby Mode 
21. Implemnt sendText instead becuase traceroute is only working for my nodes?


### COMPATABLE BOARD FIRMWARE VERSIONS (Which firmware versions the run.py code works for - only using Beta/Stable versions)
2.3.10 (2.3.10.d19607b) -> NOT RECOMENDED: Was getting strange outputs in the serial data - may have just been a one off
2.3.11 (2.3.11.2740a56) -> WORKS
2.3.12 (2.3.12.24458a7) -> WORKS 
2.3.13 (2.3.13.83f5ba0) -> WORKS

Version 2.3.15 and above add colour to the serial debug - requires removal using utils.remove_ansi_escape()
2.3.15 (2.3.15.deb7c27) -> WORKS
2.4.0 (2.4.0.46d7b82) -> WORKS

### PYTHON MESHTASTIC CLI VERSIONS (Will have a reccomended version in the requirements.txt): 
2.3.12 -> NOT RECCOMENDED (Cannot set hoplimit of traceroutes in this version -> will accept it as an argument tho)


## TUTORIAL FROM SCRATCH
1. Install firmware to board 
2. Connect to board via bluetooth using the meshtastic app on the same PC that it is connect to via serial
        ^ may require 'forgetting' the device on bluetooth settings first
3. Set lora.region to EU_868 (or relevent region)
4. Disconnect bluetooth to node 
5. should be ready: update config.ini accordingly and in terminal run: python3 run.py
