# Scrapes the Mesh information from the serial port and enters it into the CSV
# This runs in the background for entire thing, after xxx time the BLE will be submitted
# Using Threading -> MeshScaper Obj 

import time 
import datetime
import serial 
import threading
import configparser
import os

from serial.tools import list_ports
from utils import findOccourance


# /dev/cu.usbmodemDC5475EE06B41 -> 06b4 firmware version 2.3.12
# /dev/cu.usbmodemDC5475EDEE941 -> ee94 firmware version 2.3.16
# /dev/cu.usbmodemDC5475EE06DC1 -> 06dc fimrware version 2.3.13

config = configparser.ConfigParser()
config.read('config.ini')

SCRAPE_INTERVAL = config.getint('SETTINGS', 'interval', fallback=600)
RESPONSE_WAIT = config.getint('SETTINGS', 'response', fallback=120)
CONTINUOUS = config.getboolean('SETTINGS', 'continuous', fallback=False)
HOP_LIMIT = config.getint('SETTINGS', 'hoplimit', fallback=3)

ANTENNA = config.get('NODE_CONFIG', 'antenna', fallback='mini')
TX_POWER = config.getint('NODE_CONFIG', 'txPower', fallback=27)

class MeshScraper():
    def __init__(self, 
        ser_port, 
        filename): 

        self.ser = serial.Serial(port=ser_port, baudrate=115200)
        self.filename = filename

        self.base_id = None
        self.base_firmware_version =  None
        
        self.unique_id_array = []

        self.ble_scan = False
        self.ble_scan_result = {}
        self.curr_search_id = None
        
        self.meshTread = threading.Thread(target=self.scrape, args=(), daemon=True)
        self.init_file_bool = False

        self.broadcastInfo = {
            'TIME': 'N/A', 
            'MESSAGE_TYPE': 'N/A',
            'AIR_TIME': 'N/A',
            'RX_TIME': 'N/A', #filter out msg and floodmsg
            'MESSAGE_ID': 'N/A', 
            'NODE_ID': 'N/A', 
            'SNR':'N/A',
            'RSSI': 'N/A',
            'BANDWIDTH': 'N/A',
            'SPREADING_FACTOR':'N/A',
            'CODING_RATE':'N/A',
            'HOP_LIMT':'N/A',
            'HOP_START': 'N/A',
            'PAYLOAD_SIZE': 'N/A',
            'LAT': 'N/A',
            'LON': 'N/A',
            'TRACEROUTE': 'N/A',
        }

    
    def init_file(self):
        ''' Write metadata to the file 
        Should be called after begin and in BleEnd becuase the filename changes
        '''

        print(f'Writing Metadata to {self.filename}')

        self.file_metadata = {
            'TIMESTAMP': datetime.datetime.now().strftime(f"%Y%m%d_%H:%M:%S"),
            'SCRAPE_INTERVAL': SCRAPE_INTERVAL,
            'RESPONSE_WAIT': RESPONSE_WAIT,
            'CONTINUOUS': CONTINUOUS,
            'ANTENNA': ANTENNA,
            'TX_POWER': TX_POWER,
            'TR_HOPLIMIT':HOP_LIMIT,
            'BASE_ID': self.base_id, 
            'FIRMWARE_V': self.base_firmware_version, 
        }

        try:
            with open(self.filename, 'w') as f:
                f.write(','.join(self.file_metadata.keys()))
                f.write('\n')
                f.write(','.join(str(x) for x in self.file_metadata.values()))
                f.write('\n')
                f.write('------------------------------------------------------------------\n')
                f.write(','.join(self.broadcastInfo.keys()))
                f.write('\n')
                
        except Exception as e:
            print(f'Error Writing to File: {e}')

        self.init_file_bool = True


    #Taken from the python docs
    def begin(self):
        '''Begining the thread '''
        
        print('Begining the Thread')
        self.meshTread.start()


    def close(self):
        '''Ending the thread'''

        print('Closing MeshScraper')
        self.ser.close()
        if self.meshTread != threading.current_thread():
            self.meshTread.join()


    def startBleScan(self):
        ''' 
        Function called before BLE scan starts 
        
        -> tells class we are currently waiting for traceroute response
        -> updates firstTime (so we can re-write the key headers)
        -> writes a break in the file
        '''

        print('------------------------------------------------------------------')
        print(f'Beginning BLE Scan, Nodes: {self.unique_id_array}')


        self.ble_scan = True

        if self.unique_id_array:
            for mesh_id in self.unique_id_array:
                self.ble_scan_result[mesh_id] = False


        else:
            print('Shouldnt have started BLE scan - No Nodes Discovered')

        
        try:
            with open(self.filename, 'a') as f:
                f.write('------------------------------------------------------------------\n')
                f.write(','.join(self.broadcastInfo.keys()))
                f.write('\n')

        except Exception as e:
            print(f'Error Writing to File: {e}')


    def endBleScan(self, updated_filename):
        ''' 
        Function called when BLE scan ends 
        
        -> changes filename (if we are doing a CONTINOUS loop we want a new file 
        -> and updates firstTime (and other things)
        -> New-File Init
        '''
        self.init_file_bool = False #Semi-pointless when init_file is run it will be set back to True 
        self.filename = updated_filename
        self.ble_scan = False
        self.curr_search_id = None 
        self.ble_scan_result = {}
        
        self.init_file()
    
    
    def writeToFile(self, text):
        ''' Write data into the csv '''

        try:
            with open(self.filename, 'a') as f:
                f.write(text)
                f.write('\n')
        except Exception as e:
            print(f'Error Writing to File: {e}')


    def scrape(self):
        ''' Thread that scrapes the Serial Data '''

        try: 
            while True: 
                out = ''
                time.sleep(0.25)
                
                while self.ser.inWaiting() > 0:
                    out += self.ser.read(1).decode("latin-1")

                if len(out) > 1:
                    self._parseScrapeData(out)

        # Might Need Editing -> Not sure this is getting triggered, and its already closing anyway
        except Exception as e: 
            print(f"Exception in rxThread --> Closing Serial: {e}")
            self.close()
            

    def _parseScrapeData(self, serialOutput):
        ''' Function to parse the raw Serial Data into a file with a specified path '''

        outSplit = serialOutput.split('\n')

        if len(outSplit) > 1:
            importantContents = []
            messageType = '/'
            traceRoute = ''
            
            for line in outSplit:
                print(line)

                #Hacky method of pasring traceroutes: finding the "-->" in the string
                if '-->' in line:
                    
                    #For each word in the sentance -> Find the index of '-->'
                    for i in range(len(line.split(' '))):
                        if line.split(' ')[i] == '-->':

                            #If we are scanning for responses: Get the ACK=True or False them from the traceroute:
                            if self.ble_scan:

                                 # We have a TraceRoute with the correct ID -> ACK = True (Need to remove '\r)
                                try:
                                    if line.split(' ')[i+1].replace('\r', '') in self.unique_id_array:
                                        self.ble_scan_result[line.split(' ')[i+1].replace('\r', '')] = True
                                    
                                    print(self.ble_scan_result)

                                # -> or somehow we are looking for baseID or the result dict does not have the Id we have found
                                except:
                                    pass
                                    

                            try: 
                                # If this is the first time, 
                                if traceRoute == '':
                                    traceRoute = line.split(' ')[i-1] + ' --> ' + line.split(' ')[i+1]

                                #We have a multi traceroute (more than 1)
                                else:
                                    traceRoute += ' --> ' + line.split(' ')[i+1]
                            except:
                                pass
                

                # -> remove if you want network data in the file during the scan
                # elif self.ble_scan:
                #     continue

                #Hacky method of finding the message type, basically where is says Recived it usally says the message type after:
                if 'Received' in line:
                    for i in range(len(line.split(' '))):
                        if line.split(' ')[i] == 'Received':
                            try: 
                                messageType += line.split(' ')[i + 1]
                                messageType += '/'
                            except:
                                pass
            
                # The requirements for a word to be considered important/retained:
                importantContents.extend([x for x in line.split(' ') if ('=' in x) or ('ms' in x)])

            # findOccourance finds the first occourance - sorting ensures its the longest occourance (could do it in function but then it would sort it over and over again - ineffecint) 
            importantContents.sort(key=lambda s: len(s))
            importantContents.reverse()

            self.broadcastInfo['TIME'] = datetime.datetime.now().strftime("%Y%m%d_%H:%M:%S") 
            self.broadcastInfo['MESSAGE_TYPE'] = messageType if messageType != '/' else 'N/A' #Replace '/' with 'N/A'
            self.broadcastInfo['AIR_TIME'] = findOccourance([word for word in importantContents if 'g' not in word], 'ms')
            self.broadcastInfo['RX_TIME'] = findOccourance(importantContents, 'rxtime=') #filter out msg and floodmsg
            self.broadcastInfo['MESSAGE_ID'] = findOccourance(importantContents, '(id=') 
            self.broadcastInfo['NODE_ID'] = findOccourance(importantContents, 'from=') 
            self.broadcastInfo['SNR'] = findOccourance(importantContents, 'rxSNR=')
            self.broadcastInfo['RSSI'] = findOccourance(importantContents, 'rxRSSI=')
            self.broadcastInfo['BANDWIDTH'] = findOccourance(importantContents, 'bw=')
            self.broadcastInfo['SPREADING_FACTOR'] = findOccourance(importantContents, 'sf=')
            self.broadcastInfo['CODING_RATE'] = findOccourance(importantContents, 'cr=')
            self.broadcastInfo['HOP_LIMT'] = findOccourance(importantContents, 'HopLim=')
            self.broadcastInfo['HOP_START'] = findOccourance(importantContents, 'hopStart=')
            self.broadcastInfo['PAYLOAD_SIZE'] = findOccourance(importantContents, 'payloadSize=')
            self.broadcastInfo['LAT'] = findOccourance(importantContents, 'latI=')
            self.broadcastInfo['LON'] = findOccourance(importantContents, 'lonI=')
            self.broadcastInfo['TRACEROUTE'] = traceRoute if traceRoute != '' else 'N/A'

            # Discard if: self update, No message ID, encrypted etc ->
            # Last check: while we are sending traceroutes only the reponses will be written into the file 
            # Wait for the file init to be run before trying to write too it .... (Still want to print the outputs though)

            if (self.broadcastInfo['NODE_ID'] not in ['0x0', 'N/A', self.base_id]) and (self.broadcastInfo['MESSAGE_ID'] != 'N/A') and not (self.broadcastInfo['TRACEROUTE'] == 'N/A' and self.ble_scan) and self.init_file_bool:
                #unsure How but sometimes BaseId still ends up in the unique IDs

                with open(self.filename, 'a') as f:
                    f.write(','.join(str(x) for x in self.broadcastInfo.values()))
                    f.write('\n')
            
                # If we havent seen this UsersID before, and its not our own, and were not doing a ble scan -> append to unique ID list
                if self.broadcastInfo['NODE_ID'] not in self.unique_id_array and not self.ble_scan:
                    self.unique_id_array.append(self.broadcastInfo['NODE_ID'])
                    print(self.unique_id_array) 





if __name__ == '__main__':
    folder_path = datetime.datetime.now().strftime(f"dataGathering/%Y_%m_%d/")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")

    filename = datetime.datetime.now().strftime(f"SCRAPE_SERIAL_%Y%m%d_%H:%M:%S.csv")

    # Not handeling multiple serial ports at the moment
    for port in list_ports.comports():
        if port.vid is not None:
            print(f" Serial Port Found: {port.device}")
            port_dev = port.device

    print('Init MeshScraper')
    meshScraper = MeshScraper(ser_port=port_dev, filename=folder_path + filename)
    meshScraper.begin()

    try:
        counter = 0
        while True:
            counter += 1
            time.sleep(1)
            print(counter)
    except KeyboardInterrupt:
        print('\n Terminating MeshScraper')
        meshScraper.close()
