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

config = configparser.ConfigParser()
config.read('config.ini')

INTERVAL = config.getint('SETTINGS', 'interval', fallback=600)
CONTINUOUS = config.getboolean('SETTINGS', 'continuous', fallback=False)

async def setup_node():
    """ Code to find the name and BLE address of the node connected via serial 
    returns: the ble-address to setup the BleakDevice """
    
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
        print(f"Node BLE adr: {bleAdr}")
    else: 
        print(f'Cannot find BLE adr for {name} - Ensure nothing is connected too it already')
        sys.exit(1)

    print('Resetting Node DB')
    resp = subprocess.getoutput('meshtastic --reset-nodedb')  
    time.sleep(15)

    return bleAdr

def main():
    #Making a folder with the timestamp for each run ... (maybe just the day)
    folder_path = datetime.datetime.now().strftime(f"dataGathering/%Y_%m_%d_%H_%M_%S/") #Not to be changed during a test

    if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created folder: {folder_path}")

    bleAdr = asyncio.run(setup_node())

    filename = datetime.datetime.now().strftime(f"SCRAPE_SERIAL_%Y%m%d_%H:%M:%S.csv")

    portList = list_ports.comports()
    for i in range(len(portList)):
        port = portList[i]
        if port.vid is not None:
            print(f" Serial Port Found: {port.device}")
            port_dev = port.device

    print('Initializing MeshScraper')
    meshScraper = MeshScraper(ser_port=port_dev, filename=folder_path + filename)
    meshScraper.begin()

    print('Connecting Bluetooth')
    try: 
        client = BLEInterface(bleAdr)

    except Exception as e:
        print(e)
        print(f' Ensure nothing is connected to {bleAdr} already via Bluetooth ')
        sys.exit(1)

    #Give the ID of the serial node to MeshScraper so it can filter it out:
    meshScraper.baseStationID = list(client.nodes.keys())[0].replace('!', "0x")

    # Main loop of programme
    try:
        counter = 0
        while True:
            counter += 1
            time.sleep(1)

            print(counter)
            print(CONTINUOUS)

            if counter % INTERVAL == 0:

                filename = datetime.datetime.now().strftime("TRACERAOUTE_ACK_%Y%m%d_%H:%M:%S.csv")
                meshScraper.startBleScan(updated_filename = folder_path + filename)

                while meshScraper.unique_id_array:

                    #Remove the items once we have done this .... Can Run this loop over and over if continuous=True
                    uniqueDest = meshScraper.unique_id_array.pop()

                    meshScraper.CurrMeshID = uniqueDest
                    meshScraper.BleTraceRouteACK = False

                    uniqueDest = uniqueDest.replace('0x', '!') 
                    print(uniqueDest)

                    try: 
                        client.sendTraceRoute(dest=uniqueDest, hopLimit=3) 
                        # time.sleep(5)  # Use asyncio.sleep for non-blocking sleep
                        
                    except:
                        # The timeout can take over 15 mins and scales with hop limit and the no.nodes in the network
                        print(f'TraceRoute Failed: Timed out: {uniqueDest} ')

                    fileStr = f" {meshScraper.CurrMeshID} ACK: {meshScraper.BleTraceRouteACK} "
                    meshScraper.writeToCurrFile(text=fileStr)

                if not CONTINUOUS:
                    break

                filename = datetime.datetime.now().strftime("SCRAPE_SERIAL_%Y%m%d_%H:%M:%S.csv")
                meshScraper.endBleScan(updated_filename = folder_path + filename) 

        print('Terminating MeshScraper (Not in Continuous mode)')
        client.close()
        meshScraper.close()
                    
    except KeyboardInterrupt:
        print('Terminating MeshScraper')
        client.close()
        meshScraper.close()


if __name__ == '__main__':
    main()
    
        

    