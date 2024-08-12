# An example of how data can be collected using MeshScraper()
# Settings in config.ini including the antenna type, txPower -> can be written into a metadata file if required 
# CONTINUOUS=True mode will loop indefinetley - making a new file evrey interval

import sys 
import serial
import time
import asyncio
import os
import datetime
import configparser
import subprocess
import logging

from serial.tools import list_ports
from bleak import BleakScanner
from time import strftime, localtime
from mesh_scraper import MeshScraper
from utils import sendTraceRoute, generate_test_id

import meshtastic
from meshtastic.ble_interface import BLEInterface

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
    returns: the BLE address to setup the BleakDevice (python meshtastic bluetooth client )
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

    # Run a subprocess terminal command using the binary path
    try:
        resp = subprocess.getoutput(f'{MESHTSTIC_GLOABLE_PATH} --info') 
        respSplit = resp.split('\n')[2].split(' ')
    except Exception as e:
        print(f"Failed to connect to a device over Serial -> Meshtastic CLI not configured correctly, path: {MESHTSTIC_GLOABLE_PATH}: Exception: {e}")
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

    # Reccomended to reset NodeDB -> Often requires a restart to use Ble and Serial together
    print('Setting txPower')
    resp = subprocess.getoutput(f'{MESHTSTIC_GLOABLE_PATH} --set lora.tx_power {TX_POWER}')
    time.sleep(20)

    print('Resetting Node DB')
    resp = subprocess.getoutput(f'{MESHTSTIC_GLOABLE_PATH} --reset-nodedb') 
    time.sleep(25)

    return bleAdr


def main():
    '''
    Main loop

    Will listen to the network for SCRAPE_INTERVAL seconds and record all network traffic to:
    /dataGathering/%Y_%m_%d/YYMMDD_HHMM_testID_Band.csv (folder created below)

    After the interval a Trace Route is sent to each unique ID found during the scraping process, 
    wether or not we recived a response is recorded in:
    /dataGathering/%Y_%m_%d/YYMMDD_HHMM_testID_Band_Power_hoplimit.csv

    Outcome: pairs of files with the same testID showing before and after the TraceRoute response
    '''

    # Making a folder with the date -> Alter as needed
    folder_path = datetime.datetime.now().strftime(f"dataGathering/%Y_%m_%d/")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")

    bleAdr = asyncio.run(setup_node())

    # Not currently handelling multiple serial ports connected to the PC at once: https://github.com/meshtastic/python/blob/master/meshtastic/util.py -> findPorts()
    # May have to just hardcode the correct one if you have several
    port_dev = ''
    for port in list_ports.comports():
        if port.vid is not None:
            print(f"Serial Port Found: {port.device}")
            port_dev = port.device

    if port_dev == '':
        print('Could not find a serial port for device')
        sys.exit(1)

    print('Initializing MeshScraper')
    meshScraper = MeshScraper(ser_port=port_dev)

    # Must instantiate the bluetooth device after the serial thread othewise nothing comes through serial
    meshScraper.begin() 

    print('Connecting Bluetooth')
    try: 
        # If this keeps failing: try connecting to the nodes bluetooth using the meshtastic app on the PC before running this script,
        # Nothing can be connected to the node (via BLE) when this file is run but the PC will 'know' the node already
        client = BLEInterface(bleAdr)
    except Exception as e:
        print(f'Ensure nothing is connected to {bleAdr} already via Bluetooth. Exception: {e} ')
        sys.exit(1)
 
    meshScraper.base_firmware_version = client.metadata.firmware_version
    meshScraper.base_id = client.getMyNodeInfo()['user']['id'].replace('!', "0x").replace('\r', '')

    # Packets are observed by the serial thread of meshscraper after begin() but aren't written into a file until init_file()
    test_id = generate_test_id() #Matching pre and post rx data will have the same test_id
    filename = datetime.datetime.now().strftime(f"%Y%m%d_%H%M_{test_id}_{BAND}.csv")
    meshScraper.init_file(filename = folder_path + filename)

    # Main loop
    try:
        counter = 0
        while True:

            # Recomended to do time.sleep(SCRAPE_INTERVAL) and not have a counter in 'production', but its good for debugging
            time.sleep(1)
            counter += 1
            print(counter)

            if counter % SCRAPE_INTERVAL == 0:

                # We havent found any nodes during the interval -> Create new file and start again if in CONTINUOUS mode
                if not meshScraper.unique_id_array:
                    print(' No nodes discovered during interval ')
                    meshScraper.writeToFile(text=' ----- No Nodes Discovered -----')

                    if not CONTINUOUS:
                        break

                    else:
                        # Setup a new test - Haven't called startBleScan() so dont need a reset
                        test_id = generate_test_id() 
                        filename = datetime.datetime.now().strftime(f"%Y%m%d_%H%M_{test_id}_{BAND}.csv")
                        meshScraper.init_file(filename = folder_path + filename) 
                        continue

                # Sending TraceRoutes -> First setup results file
                meshScraper.startBleScan()
                filename = datetime.datetime.now().strftime(f"%Y%m%d_%H%M_{test_id}_{BAND}_{TX_POWER}_{HOP_LIMIT}.csv")
                meshScraper.init_file(filename = folder_path + filename, is_results=True)

                for mesh_id in meshScraper.unique_id_array:
                    meshScraper.ble_scan_result[mesh_id]['START_TIME'] = time.time()
                    meshScraper.ble_scan_result[mesh_id]['TR_TIMESTAMP'] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

                    # Needs to be in this format to be send via ble client
                    mesh_id = mesh_id.replace('0x', '!') 
                    print('------------------------------------------------------------------')
                    print(f'Sending TraceRoute to {mesh_id}, Of Nodes: {meshScraper.unique_id_array}')

                    try: 
                        sendTraceRoute(client=client, dest=mesh_id, hopLimit=HOP_LIMIT)
                    
                    except Exception as e:
                        print(f'TraceRoute Failed: Timed out: {mesh_id}: Exception {e}')

                    time.sleep(1)

                # Wait for the responce from any TraceRoute for RESPONSE_WAIT seconds -> if they are all accounted for end early
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
                test_id = generate_test_id() 
                filename = datetime.datetime.now().strftime(f"%Y%m%d_%H%M_{test_id}_{BAND}.csv")
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