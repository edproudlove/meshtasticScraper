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


DOING
4. Could have a sign for if the traceroute has began, -> start a timer, if we do not recive a traceRoute with the relevent id then ACK = 0
        -> SORT OF: By resetting the nodeDB the timeout should shorten, still need to eliminate false negatives (below)
        -> Removed timeouts from the meshtatsic.BLEInterface.sendTraceRotue(), this will only work on my machine -> Still need to make this dynamic (After an install/git pull)
5. The Time-Out of the BLE interface is unreliable -> if we get a response tell the BLE to move on -> Sometimes it hangs for a long time 
        -> Think this is fixed by 4. but am not sure what was causing it in the first place (shouldnt have been hapening before 4 either)

TODO:
8. How should device be configured ... on running the script could send a config 
9. Make the code modular -> can just download from github and run it (pip install/ .sh etc)
12. Document which firmware versions the code will work for (2.4.0 etc) - > same for verions of python CLI
13. Could make a branch of the Python CLI -> or replicate it in a diffrent file? ( How to handle the changes made to the python cli?)
15. Add in how long we waited for a reponse for each Node?
17. Logging rather than prints -> need to get rid of the meshtatsic logs -> DEBGUG settings for if it needs to be printed
18. Will it always accept bluetooth conection? what about the pin/restarts
19. Flash most recent firmware and go through every step to make documentation / tutorial


BOARD FIRMWARE VERSIONS (Which firmware versions the run.py code works for)
2.3.12 (2.3.12.24458a7) -> WORKS 
2.3.13 (2.3.13.83f5ba0) -> WORKS

PYTHON MESHTASTIC CLI VERSIONS (Will have a reccomended version in the requirements.txt): 
2.3.12 -> WORKS 
