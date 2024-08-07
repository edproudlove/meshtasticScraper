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

sys.path.append('/Users/ethan/Desktop/Summer_Internship_2024/Rssi_and_snr_tests/MLDataScraping/pythonmatser')
import meshtastic
from meshtastic.ble_interface import BLEInterface

from mesh_scraper import MeshScraper

#Dont really want theese called into both -> maybe just put it into the mesh scraper class and use it from there
config = configparser.ConfigParser()
config.read('config.ini')

INTERVAL = config.getint('SETTINGS', 'interval', fallback=600)
CONTINUOUS = config.getboolean('SETTINGS', 'continuous', fallback=False)
HOP_LIMIT = config.getint('SETTINGS', 'hoplimit', fallback=3)

async def setup_node():
    """ 
    
    Code to find the name and BLE address of the node connected via serial 
    returns: the ble-address to setup the BleakDevice 
    
    """

    resp = subprocess.getoutput('meshtastic --info')
    respSplit = resp.split('\n')[2].split(' ')
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
    resp = subprocess.getoutput('meshtastic --reset-nodedb')  
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

    #Could go into meshScraper class?
    for port in list_ports.comports():
        if port.vid is not None:
            print(f"Serial Port Found: {port.device}")
            port_dev = port.device

    print('Initializing MeshScraper')
    meshScraper = MeshScraper(ser_port = port_dev, filename = folder_path + filename)
    meshScraper.begin()

    #Not sure why but you need to instantiate the bluetooth device after the serial thread othewise it dosent work
    print('Connecting Bluetooth')

    try: 
        client = BLEInterface(bleAdr)
    except Exception as e:
        print(e)
        print(f' Ensure nothing is connected to {bleAdr} already via Bluetooth ')
        sys.exit(1)
 
    meshScraper.base_firmware_version = client.metadata.firmware_version
    meshScraper.base_id = client.getMyNodeInfo()['user']['id'].replace('!', "0x")

    meshScraper.init_file()

    # Main loop
    try:
        counter = 0
        while True:
            
            # could just do time.sleep(INTERVAL) - no counter - but its good for debugging
            time.sleep(1)
            counter += 1
            print(counter)

            if counter % INTERVAL == 0:

                if not meshScraper.unique_id_array:
                    print(' No nodes / messages discovered during interval ')

                meshScraper.startBleScan()
                while meshScraper.unique_id_array:

                    #Remove the items from front of list .... Can Run this loop over and over if continuous=True
                    uniqueDest = meshScraper.unique_id_array.pop(0)

                    #We get the ACK from the file rather than from the client -> sometimes the client misses it/ response isnt triggered
                    meshScraper.CurrMeshID = uniqueDest
                    meshScraper.BleTraceRouteACK = False

                    # Needs to be in this format to be send via ble client
                    uniqueDest = uniqueDest.replace('0x', '!') 

                    print('------------------------------------------------------------------')
                    print(f'Sending TraceRoute to {uniqueDest}, Remaining Nodes: {meshScraper.unique_id_array}')

                    #1. it is not handeling failed tracereoutes and errors well, -> maybe implement my own timeout / repsonse rather than waiting
                    #2. it would be better if it filtered the incomming stream only to include the traceroute messages when this is happening
                    #3. I have taken it out the try except block out... You need it appreantly otherwise if it fails the 
                    #4. TRY CHANGING THE TIMEOUT CLASS IN MESHTASTIC UTILS -> also mabe record the time taken to arrive at that decision
                    
                    try: 
                        client.sendTraceRoute(dest=uniqueDest, hopLimit=HOP_LIMIT) 
                    
                    except Exception as e:
                    # The timeout can take over 15 mins and scales with hop limit and the no.nodes in the network
                        print(f'TraceRoute Failed: Timed out: {uniqueDest}: Exception {e}')
                    
                    # Wait for a response for at least 20s -> The BLE client can be hastey in assuming we have failed 
                    time.sleep(20) # Use asyncio.sleep for non-blocking sleep

                    fileStr = f" {meshScraper.CurrMeshID} ACK: {meshScraper.BleTraceRouteACK} "
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
    
        

    