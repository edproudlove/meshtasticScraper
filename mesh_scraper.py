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

INTERVAL = config.getint('SETTINGS', 'interval', fallback=600)
CONTINUOUS = config.getboolean('SETTINGS', 'continuous', fallback=False)
HOP_LIMIT = config.getint('SETTINGS', 'hoplimit', fallback=3)

ANTENNA = config.get('NODE_CONFIG', 'antenna', fallback='mini')
TX_POWER = config.get('NODE_CONFIG', 'txPower', fallback='27db')

class MeshScraper():
    def __init__(self, 
        ser_port, 
        filename): 

        self.ser = serial.Serial(port=ser_port, baudrate=115200)
        self.filename = filename

        self.base_id = None
        self.base_firmware_version =  None
        
        self.firstTime = True
        self.unique_id_array = []

        self.CurrMeshID = None
        self.BleTraceRouteACK = False
        self.bleScan = False

        self.meshTread = threading.Thread(target=self.scrape, args=(), daemon=True)

    
    def init_file(self):
        ''' Write metadata to the file 
        -> called in begin and BleEnd: becuase the filename changes
        '''

        print(f'Writing Metadata to {self.filename}')

        self.file_metadata = {
            'TIMESTAMP': datetime.datetime.now().strftime(f"%Y%m%d_%H:%M:%S"),
            'INTERVAL': INTERVAL,
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
        except Exception as e:
            print(f'Error Writing to File: {e}')


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


    def scrape(self):
        ''' Thread that scrapes the Serial Data '''

        try: 
            while True: 
                out = ''
                time.sleep(0.25)
                
                while self.ser.inWaiting() > 0:
                    out += self.ser.read(1).decode("latin-1")

                if len(out) > 1:
                    self.parseScrapeData(out)

        # Might Need Editing -> Not sure this is getting triggered, and its already closing anyway
        except Exception as e: 
            print(f"Exception in rxThread --> Closing Serial: {e}")
            self.close()


    def startBleScan(self):
        ''' 
        Function called before BLE scan starts 
        
        -> tells class we are currently waiting for traceroute response
        -> updates firstTime (so we can re-write the key headers)
        -> writes a break in the file
        '''

        print('------------------------------------------------------------------')
        print(f'Beginning BLE Scan, Nodes: {self.unique_id_array}')

        self.firstTime = True
        self.bleScan = True
        self.writeToFile('------------------------------------------------------------------')

    def endBleScan(self, updated_filename):
        ''' 
        Function called when BLE scan ends 
        
        -> changes filename (if we are doing a CONTINOUS loop we want a new file 
        -> and updates firstTime (and other things)
        -> New-File Init
        '''

        self.filename = updated_filename
        self.firstTime = True
        self.bleScan = False

        self.CurrMeshID = None 
        self.BleTraceRouteACK = False
        
        self.init_file()
    
    
    def writeToFile(self, text):
        ''' Write data into the csv '''

        try:
            with open(self.filename, 'a') as f:
                f.write(text)
                f.write('\n')
        except Exception as e:
            print(f'Error Writing to File: {e}')
            

    def parseScrapeData(self, serialOutput):
        ''' Function to parse the raw Serial Data into a file with a specified path '''

        outSplit = serialOutput.split('\n')

        if len(outSplit) > 1:
            importantContents = []
            messageType = '/'
            traceRoute = ''
            
            for line in outSplit:
                print(line) 

                #Hacky method of finding the traceroute string
                if '-->' in line:
                    
                    # We have a TraceRoute with the correct ID -> ACK = True -> GO OVER THIS>>>>>
                    try:
                        if self.CurrMeshID in line:
                            self.BleTraceRouteACK = True
                    except:
                        # currmeshID is None and throws an error searching for it ...
                        pass

                    #For each word in the sentance
                    for i in range(len(line.split(' '))):
                        # Find the word index of '-->'
                        if line.split(' ')[i] == '-->':
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
                # elif self.bleScan:
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

            broadcastInfo = {
                'TIME': datetime.datetime.now().strftime("%Y%m%d_%H:%M:%S"), 
                'MESSAGE_TYPE': messageType if messageType != '/' else 'N/A', #Replace '/' with 'N/A'
                'AIR_TIME': findOccourance([word for word in importantContents if 'g' not in word], 'ms'),
                'RX_TIME': findOccourance(importantContents, 'rxtime='), #filter out msg and floodmsg
                'MESSAGE_ID': findOccourance(importantContents, '(id='), 
                'NODE_ID': findOccourance(importantContents, 'from='), 
                'SNR': findOccourance(importantContents, 'rxSNR='),
                'RSSI':findOccourance(importantContents, 'rxRSSI='),
                'BANDWIDTH': findOccourance(importantContents, 'bw='),
                'SPREADING_FACTOR': findOccourance(importantContents, 'sf='),
                'CODING_RATE': findOccourance(importantContents, 'cr='),
                'HOP_LIMT': findOccourance(importantContents, 'HopLim='),
                'HOP_START': findOccourance(importantContents, 'hopStart='),
                'PAYLOAD_SIZE': findOccourance(importantContents, 'payload='),
                'LAT': findOccourance(importantContents, 'latI='),
                'LON': findOccourance(importantContents, 'lonI='),
                'TRACEROTUE': traceRoute if traceRoute != '' else 'N/A',
            }

            # Discard if self update / from=0x00 / No message ID / encrypted etc -> Last check while we are sending traceroutes only the reponses will be written into the file 
            if broadcastInfo['NODE_ID'] not in ['0x0', 'N/A', self.base_id] and broadcastInfo['MESSAGE_ID'] != 'N/A' and not (broadcastInfo['TRACEROTUE'] == 'N/A' and self.bleScan):

                #If this is the first run then also put the Keys in -> maybe just od this as part of the init
                if self.firstTime:
                    with open(self.filename, 'a') as f:
                        self.firstTime = False
                        f.write(','.join(broadcastInfo.keys()))
                        f.write('\n')
                        f.write(','.join(str(x) for x in broadcastInfo.values()))
                        f.write('\n')

                else:
                    with open(self.filename, 'a') as f:
                        f.write(','.join(str(x) for x in broadcastInfo.values()))
                        f.write('\n')
            
                # If we havent seen this UsersID before, and its not our own, and were not doing a ble scan -> append to unique ID list
                if broadcastInfo['NODE_ID'] not in self.unique_id_array and not self.bleScan:
                    self.unique_id_array.append(broadcastInfo['NODE_ID'])
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
