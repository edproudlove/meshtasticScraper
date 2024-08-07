# An example loop of how data can be collected:
# Settings in config.ini including the antenna type and txPower 
# CONTINUOUS mode will infinite loop - making a new file evry interval

import sys 
import serial
from serial.tools import list_ports
from pubsub import pub
from bleak import BleakClient, BleakScanner, BLEDevice
import time
from time import strftime, localtime
import random
import asyncio
import os
import datetime
import configparser
import subprocess

sys.path.append('/Users/ethan/Desktop/Summer_Internship_2024/Rssi_and_snr_tests/MLDataScraping/pythonmaster_v2')
import meshtastic
from meshtastic.ble_interface import BLEInterface

print("meshtastic module location:", os.path.dirname(meshtastic.__file__))

from mesh_scraper import MeshScraper

#Dont really want theese called into both -> maybe just put it into the mesh scraper class and use it from there
config = configparser.ConfigParser()
config.read('config.ini')

SCRAPE_INTERVAL = config.getint('SETTINGS', 'interval', fallback=600)
RESPONSE_WAIT = config.getint('SETTINGS', 'response', fallback=120)
CONTINUOUS = config.getboolean('SETTINGS', 'continuous', fallback=False)
HOP_LIMIT = config.getint('SETTINGS', 'hoplimit', fallback=3)

async def setup_node():
    """ 
    
    Code to find the name and BLE address of the node connected via serial 
    returns: the ble-address to setup the BleakDevice 
    
    """

    print("Setup")

    MESHTSTIC_GLOABLE_PATH = '/Users/ethan/miniforge3/bin/meshtastic'

    #Definetly need to make this moodular --> just run the install.sh or somthing
    try: 
        resp = subprocess.getoutput('/Users/ethan/miniforge3/bin/meshtastic --info') # resp = subprocess.getoutput('meshtastic --info') 
        respSplit = resp.split('\n')[2].split(' ')
    except Exception as e:
        print(f"Failed to connect to a device over Serial -> Meshtastic CLI not working ...")
        sys.exit(1)

    name = respSplit[1] + '_' + respSplit[2] 

    print(f"Node Name: {name}")

    bleAdr = ''

    devices = await BleakScanner.discover()

    for device in devices:
        # print(device)
        if device.name == name:
            bleAdr = device.address

    if bleAdr != '':
        print(f'Node BLE adr: {bleAdr}')
    else: 
        print(f'Cannot find BLE adr for {name} - Ensure nothing is connected already via Bluetooth')
        sys.exit(1)

    #Reccomended to reset NodeDB regularly as the timeout scales with the nodes
    # If you start scraping and then reset the device -> you can keep scraping the debug stuff and use the ble 
    # basically it requires a restart to use ble and serial -> not sure why?

    print('Resetting Node DB')
    resp = subprocess.getoutput('/Users/ethan/miniforge3/bin/meshtastic --reset-nodedb')  #resp = subprocess.getoutput('meshtastic --reset-nodedb')  
    time.sleep(15)

    return bleAdr

def main():
    #Making a folder with the date
    folder_path = datetime.datetime.now().strftime(f"dataGathering/%Y_%m_%d/")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")

    bleAdr = asyncio.run(setup_node())

    filename = datetime.datetime.now().strftime(f"SCRAPE_SERIAL_%Y%m%d_%H:%M:%S.csv")

    #Could go into meshScraper class - not handelling multiple possible serial ports
    for port in list_ports.comports():
        if port.vid is not None:
            print(f"Serial Port Found: {port.device}")
            port_dev = port.device

    print('Initializing MeshScraper')
    meshScraper = MeshScraper(ser_port = port_dev, filename = folder_path + filename)
    meshScraper.begin()

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

    meshScraper.init_file()

    # Main loop
    try:
        counter = 0
        while True:
            
            # could just do time.sleep(SCRAPE_INTERVAL) - no counter - but its good for debugging
            time.sleep(1)
            counter += 1
            print(counter)

            if counter % SCRAPE_INTERVAL == 0:

                if not meshScraper.unique_id_array:
                    print(' No nodes / messages discovered during interval ')
                    meshScraper.writeToFile(text='No Nodes Discovered')

                    # Put this into an END LOOP function -> maybe just do this in MeshScraper
                    if not CONTINUOUS:
                        break

                    filename = datetime.datetime.now().strftime("SCRAPE_SERIAL_%Y%m%d_%H:%M:%S.csv")
                    meshScraper.endBleScan(updated_filename = folder_path + filename) #In this case it just sets up a new test
                    

                meshScraper.startBleScan()
                for mesh_id in meshScraper.unique_id_array:

                    # Needs to be in this format to be send via ble client
                    mesh_id = mesh_id.replace('0x', '!') 

                    print('------------------------------------------------------------------')
                    print(f'Sending TraceRoute to {mesh_id}, Of Nodes: {meshScraper.unique_id_array}')

                    # The timeout can take over 15 mins and scales with hop limit and the no.nodes in the network 
                    # -> Unsure why it does this: i have changed sorce code to timeout after 20s everytime

                    try: 
                        client.sendTraceRoute(dest=mesh_id, hopLimit=HOP_LIMIT) 
                    
                    except Exception as e:
                        print(f'TraceRoute Failed: Timed out: {mesh_id}: Exception {e}')

                    time.sleep(3)
                    
        
                # Wait for the responce from any TraceRoute for n seconds -> if they are all accounted for end early
                StartTime = time.time()
                while time.time() < (StartTime + RESPONSE_WAIT):
                    time.sleep(0.25)
                    if all(meshScraper.ble_scan_result.values()):
                        break
               
                for result_mesh_id in meshScraper.ble_scan_result:
                    fileStr = f" {result_mesh_id} ACK: {meshScraper.ble_scan_result[result_mesh_id]} "
                    print(fileStr)
                    meshScraper.writeToFile(text=fileStr)

                # if we arent looping - just end it
                if not CONTINUOUS:
                    break

                filename = datetime.datetime.now().strftime("SCRAPE_SERIAL_%Y%m%d_%H:%M:%S.csv")
                meshScraper.endBleScan(updated_filename = folder_path + filename) 

        # if not in continous mode it will break and trigger this
        print('Terminating MeshScraper (Not in Continuous mode)')
        client.close()
        meshScraper.close()
                    
    except KeyboardInterrupt:
        print('\nTerminating Stream')
        client.close()
        meshScraper.close()

if __name__ == '__main__':
    main()
    
        

    