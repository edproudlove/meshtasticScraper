#Usefull functions for parsing scraped data etc

# What to implement 
# 0. Find the Bluetooth device we are connected too over serial and clear its nodeDB -> DONE
# 1. At a given point / time I want to begin the BLE traceroute stuff                -> DONE
# 2. The BLE will send traceRoutes to each Node in meshScraper.unique_id_arr         -> DONE
# 3. Responce will be input into a NEW file (need to change the self.filename)
# 4. Could have a sign for if the traceroute has began, -> start a timer, if we do not recive a traceRoute with the relevent id then ACK = 0
#           -> SORT OF: By resetting the nodeDB the timeout should shorten, still need to eliminate false negatives (below)
# 5. the Time Out of the BLE interface is unreliable -> if we get a response tell the BLE to move on (Raise Exception - Don't Know how to do that)
# 6. Make finding the BLE scanner dynamic                                            -> DONE
# 7. change the RX power antenna etc (Maybe the point Below)
# 8. How should the device be configured ... on running the script could send a config 
# 9. Make the code modular -> can just download from github and run it (pip install etc)
# 10. continous mode or just run it once....
# 11. READINGS and RESULTS in ONE file -> append results to the end

def findOccourance(listToSearch, tragetString):
    for i in range(len(listToSearch)):
        if tragetString in listToSearch[i]:
            # First half replaces what we are looking for with '', second removes anything in "(),"
            returnString = listToSearch[i].replace(tragetString, '').translate({ord(c): None for c in '(),'})            
            # Hacky again - If after removing all the above, it things msg= is the time (searching for ms) - so if it still includes an '=' its wrong 
            if '=' in returnString:
                continue
            else:
                return returnString.replace('\r', '') #If it includes '\r' remove it

    #If its not there return N/A
    return 'N/A'