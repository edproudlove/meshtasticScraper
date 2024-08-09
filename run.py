# An example of how data can be collected using MeshScraper()
# Settings in config.ini including the antenna type and txPower -> can be written into a metadata file 
# CONTINUOUS=True mode will loop indefinetley - making a new file evrey interval

import sys 
import serial
import time
import asyncio
import os
import datetime
import configparser
import subprocess

from serial.tools import list_ports
from bleak import BleakScanner
from time import strftime, localtime
from mesh_scraper import MeshScraper
from utils import sendTraceRoute

import meshtastic
from meshtastic.ble_interface import BLEInterface

# print("meshtastic module location:", os.path.dirname(meshtastic.__file__))

# -> maybe just put it into the mesh scraper class and use it from there
config = configparser.ConfigParser()
config.read('config.ini')

SCRAPE_INTERVAL = config.getint('SETTINGS', 'interval', fallback=600)
RESPONSE_WAIT = config.getint('SETTINGS', 'response', fallback=120)
CONTINUOUS = config.getboolean('SETTINGS', 'continuous', fallback=False)
HOP_LIMIT = config.getint('SETTINGS', 'hoplimit', fallback=3)

BAND = config.get('NODE_CONFIG', 'band', fallback='EU_868')  #Make dynamic
TX_POWER = config.getint('NODE_CONFIG', 'txPower', fallback=27)

async def setup_node():
    """ 
    Code to find the name and BLE address of the node connected via serial 
    returns: the ble-address to setup the BleakDevice 
    """
    print("Node Setup")

    # Determine the path to the virtual environment's bin or Scripts directory based on OS
    # Reqiured to run terminal commands such as $ meshtastic --reset-nodedb
    if sys.platform == "win32":
        # For Windows
        venv_scripts_path = os.path.join(os.path.dirname(sys.executable), 'Scripts')
        MESHTSTIC_GLOABLE_PATH = os.path.join(venv_scripts_path, 'meshtastic.exe')
    else:
        # For macOS/Linux
        venv_bin_path = os.path.dirname(sys.executable)
        MESHTSTIC_GLOABLE_PATH = os.path.join(venv_bin_path, 'meshtastic')

    # Verify if the binary exists
    if not os.path.isfile(MESHTSTIC_GLOABLE_PATH):
        raise FileNotFoundError(f"{MESHTSTIC_GLOABLE_PATH} not found")

    # Run a subprocess command using the binary path
    try:
        resp = subprocess.getoutput(f'{MESHTSTIC_GLOABLE_PATH} --info') 
        respSplit = resp.split('\n')[2].split(' ')
    except Exception as e:
        print(f"Failed to connect to a device over Serial -> Meshtastic CLI not configured correctly, path: {MESHTSTIC_GLOABLE_PATH}")
        print(e)
        sys.exit(1)

    name = respSplit[1] + '_' + respSplit[2] 

    print(f"Node Name: {name}")

    bleAdr = ''
    devices = await BleakScanner.discover()
    for device in devices:
        if device.name == name:
            bleAdr = device.address

    if bleAdr != '':
        print(f'Node BLE adr: {bleAdr}')
    else: 
        print(f'Cannot find BLE adr for {name} - Ensure nothing is connected already via Bluetooth')
        sys.exit(1)

    # Reccomended to reset NodeDB.
    # -> requires a restart to use Ble and Serial??
    print('Setting txPower')
    resp = subprocess.getoutput(f'{MESHTSTIC_GLOABLE_PATH} --set lora.tx_power {TX_POWER}')
    time.sleep(20)

    print('Resetting Node DB')
    resp = subprocess.getoutput(f'{MESHTSTIC_GLOABLE_PATH} --reset-nodedb')  #resp = subprocess.getoutput('meshtastic --reset-nodedb')  
    time.sleep(25)

    return bleAdr


def main():
    #Making a folder with the date
    folder_path = datetime.datetime.now().strftime(f"dataGathering/%Y_%m_%d/")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")

    bleAdr = asyncio.run(setup_node())

    port_dev = ''

    #Could go into meshScraper class - not handelling multiple possible serial ports
    for port in list_ports.comports():
        if port.vid is not None:
            print(f"Serial Port Found: {port.device}")
            port_dev = port.device
    
    #Check the serial connection
    if port_dev == '':
        print('Error finding a serial port for device')
        sys.exit(1)

    print('Initializing MeshScraper')
    meshScraper = MeshScraper(ser_port = port_dev)
    meshScraper.begin() #Must do this before BLE config -> can still print to terminal but wount be written into a file until init_file

    # You need to instantiate the bluetooth device after the serial thread othewise nothing comes through serial
    print('Connecting Bluetooth')

    try: 
        # If this keeps failing - try connecting via bluetooth using the app on the PC before running this script
        # Nothing can be connected to the node (via BLE) when this file is run but the PC will 'know' the node already
        client = BLEInterface(bleAdr)
    except Exception as e:
        print(e)
        print(f' Ensure nothing is connected to {bleAdr} already via Bluetooth ')
        sys.exit(1)
 
    meshScraper.base_firmware_version = client.metadata.firmware_version
    meshScraper.base_id = client.getMyNodeInfo()['user']['id'].replace('!', "0x").replace('\r', '')

    # Packets are observed by the serial thread of meshscraper after begin() but aren't written into a file until init_file()
    filename = datetime.datetime.now().strftime(f"%Y%m%d_%H%M_{BAND}.csv")
    meshScraper.init_file(filename = folder_path + filename, is_results=False)

    # Main loop
    try:
        counter = 0
        while True:
            
            # Could just do time.sleep(SCRAPE_INTERVAL) and not have a counter, but its good for debugging
            time.sleep(1)
            counter += 1
            print(counter)

            if counter % SCRAPE_INTERVAL == 0:

                # We havent found any nodes during the interval -> just move on and
                if not meshScraper.unique_id_array:
                    print(' No nodes discovered during interval ')
                    meshScraper.writeToFile(text=' ----- No Nodes Discovered -----')

                    # Put this into an END LOOP function
                    if not CONTINUOUS:
                        break
                    else:
                        #In this case it just sets up a new test - Haven't called startBleScan so dont need a reset
                        filename = datetime.datetime.now().strftime(f"%Y%m%d_%H%M_{BAND}.csv")
                        meshScraper.init_file(filename = folder_path + filename) 
                        continue

                # One results file: YYMMDD_HHMM_Band_Power_hoplimit.csv
                meshScraper.startBleScan()
                filename = datetime.datetime.now().strftime(f"%Y%m%d_%H%M_{BAND}_{TX_POWER}_{HOP_LIMIT}.csv")
                meshScraper.init_file(filename = folder_path + filename, is_results=True)

                for mesh_id in meshScraper.unique_id_array:
                    meshScraper.ble_scan_result[mesh_id]['START_TIME'] = time.time()
                    meshScraper.ble_scan_result[mesh_id]['TR_TIMESTAMP'] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

                    # Needs to be in this format to be send via ble client
                    mesh_id = mesh_id.replace('0x', '!') 

                    print('------------------------------------------------------------------')
                    print(f'Sending TraceRoute to {mesh_id}, Of Nodes: {meshScraper.unique_id_array}')

                    try: 
                        # client.sendTraceRoute(dest=mesh_id, hopLimit=HOP_LIMIT)
                        sendTraceRoute(client=client, dest=mesh_id, hopLimit=HOP_LIMIT)
                    
                    except Exception as e:
                        print(f'TraceRoute Failed: Timed out: {mesh_id}: Exception {e}')

                    time.sleep(1)

                # Wait for the responce from any TraceRoute for n seconds -> if they are all accounted for end early
                StartTime = time.time()
                while time.time() < (StartTime + RESPONSE_WAIT):
                    time.sleep(0.25)
                    if all(sub_dict['ACK'] for sub_dict in meshScraper.ble_scan_result.values()):
                        break
                               
                # Write all the responces into the file -> Do this in endBleScan
                meshScraper.endBleScan() 

                # If not looping - just end it
                if not CONTINUOUS:
                    break

                # Otherwise make a new file to start again
                filename = datetime.datetime.now().strftime(f"%Y%m%d_%H%M_{BAND}.csv")
                meshScraper.init_file(filename = folder_path + filename)

                
        # Break will trigger this
        print('Terminating MeshScraper (Not in Continuous mode)')
        client.close()
        meshScraper.close()
                    
    except KeyboardInterrupt:
        print('\nTerminating Stream')
        client.close()
        meshScraper.close()

if __name__ == '__main__':
    main()
    
        

    