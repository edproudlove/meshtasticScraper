# Usefull functions for parsing scraped data etc
import re
import random
import string

# Meshtastic cli version 2.3.13 changed theese imports:
try:
    import meshtastic.mesh_pb2 as mesh_pb2
    import meshtastic.portnums_pb2 as portnums_pb2
except ImportError:
    from meshtastic.protobuf import mesh_pb2, portnums_pb2


def remove_ansi_escape(output):
    ''' Function removes ansi escape charictors 
    -> theese produce the color in terminal output in device firmware > 2.3.15'''
    # Regex pattern to match ANSI escape codes
    # ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    ansi_escape = re.compile(r'(?:\x1b[@-_][0-?]*[ -/]*[@-~])') #More thorough
    
    # Remove ANSI escape codes and null characters
    cleaned_output = ansi_escape.sub('', output)
    cleaned_output = cleaned_output.replace('\x00', '')

    # Considering adding '\x1b[0m' to the output to ensure the terminal is always white (asi escape reset)

    return cleaned_output



def findOccourance(listToSearch, tragetString):
    ''' Finds and replaces the target string in the listToSearch '''

    for i in range(len(listToSearch)):
        if tragetString in listToSearch[i]:
            # First half replaces what we are looking for with '', second removes anything in "(),"
            returnString = listToSearch[i].replace(tragetString, '').translate({ord(c): None for c in '(),'})         

            # Hacky again - after removing the above it thinks msg= is the time (searching for ms) 
            # So if it still includes an '=' after replacaing the part we are searching for its wrong 
            if '=' in returnString:
                continue
            else:
                return returnString.replace('\r', '')

    # If its not there return N/A
    return 'N/A'


# https://github.com/meshtastic/python/blob/master/meshtastic/mesh_interface.py -> line 530
def sendTraceRoute(client, dest, hopLimit):
    ''' 
    Instead of using client.sendTraceRoute() (MeshInterface.sendTraceRoute())
    -> This fuction does exactly the same but with out the timeout or onResponse() 
    Both of theese are done in the main() loop or in meshScraper - just look at the serial output to see if we got a response
    
    (basically a copy of the python cli function without the timeout or waiting for a response to get ACK=True)
    '''
    r = mesh_pb2.RouteDiscovery()
    client.sendData(
        r,
        destinationId=dest,
        portNum=portnums_pb2.PortNum.TRACEROUTE_APP,
        wantResponse=True,
        channelIndex=0,
        hopLimit=hopLimit,
    )

def generate_test_id():
    ''' Generates a random string of letters and numbers that is 12 long '''

    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return random_string


