# Scrapes the Mesh information from the serial port and enters it into the CSV
# Using Threading -> MeshScaper Obj 

import time 
import datetime
import serial 
import threading
import configparser
import os

from serial.tools import list_ports
from utils import findOccourance, remove_ansi_escape

# This config stuff is only needed for the metadata, if its not written to the file it can be removed.
config = configparser.ConfigParser()
config.read('config.ini')

SCRAPE_INTERVAL = config.getint('SETTINGS', 'interval', fallback=600)
RESPONSE_WAIT = config.getint('SETTINGS', 'response', fallback=120)
CONTINUOUS = config.getboolean('SETTINGS', 'continuous', fallback=False)
HOP_LIMIT = config.getint('SETTINGS', 'hoplimit', fallback=3)
ANTENNA = config.get('NODE_CONFIG', 'antenna', fallback='mini')
TX_POWER = config.getint('NODE_CONFIG', 'txPower', fallback=27)
BAND = config.get('NODE_CONFIG', 'band', fallback='EU_868')

class MeshScraper():
    def __init__(self, ser_port): 
        self.ser = serial.Serial(port=ser_port, baudrate=115200)
        self.filename = None
        self.base_id = None
        self.base_firmware_version =  None

        self.init_file_bool = False
        self.unique_id_array = []
        self.ble_scan = False
        self.ble_scan_result = {}

        self.meshTread = threading.Thread(target=self._scrape, args=(), daemon=True)
        
        self.broadcastInfo = {
            'TIME': 'N/A', 
            'MESSAGE_TYPE': 'N/A',
            'AIR_TIME': 'N/A',
            'RX_TIME': 'N/A',
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

    
    def init_file(self, filename, is_results=False):
        ''' Create file and Optionally write metadata to it

        Should be called after begin() and after endBleScan() to change the file for diffrent data
        
        Filename: name of file to create (needs to include the folder name if there is one)
        is_results: is this a results file - means the column headers will be diffrent

        '''

        # Create file (Could call this in the begin function but its called just before the main loop to get exactly the interval time)
        self.filename = filename

        print(f'Writing to: {self.filename}')

        if is_results:
            try:
                with open(self.filename, 'w') as f:
                    f.write('TR_TIMESTAMP,ID,ACK,\n')
                    
            except Exception as e:
                print(f'Error Writing to File: {e}')
        
        else:
            # Scraping the mesh 
            # -> create file_metadata (dont need to change this for the results its the same)
            # -> Write the scraping headers to the file 

            self.file_metadata = {
                'TIMESTAMP': datetime.datetime.now().strftime(f"%Y%m%d_%H:%M:%S"),
                'SCRAPE_INTERVAL': SCRAPE_INTERVAL,
                'RESPONSE_WAIT': RESPONSE_WAIT,
                'CONTINUOUS': CONTINUOUS,
                'ANTENNA': ANTENNA,
                'TX_POWER': TX_POWER,
                'TR_HOPLIMIT':HOP_LIMIT,
                'BAND': BAND,
                'BASE_ID': self.base_id, 
                'FIRMWARE_V': self.base_firmware_version, 
            }

            # Could write metadata to the file aswell - This just writes the broadcastInfo keys as column headers
            try:
                with open(self.filename, 'w') as f:
                    f.write(','.join(self.broadcastInfo.keys()))
                    f.write('\n')
            except Exception as e:
                print(f'Error Writing to File: {e}')

            #Allow mesh-data to be written into the file aswell in (_parseScrapeData)
            self.init_file_bool = True

    # Both begin() and close() are adpated from meshtastic python docs: https://github.com/meshtastic/python/blob/master/meshtastic/stream_interface.py
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
        
        -> Tells class we are currently waiting for traceroute response
        -> Populates the result dictionary
        '''

        print('------------------------------------------------------------------')
        print(f'Beginning BLE Scan, Nodes: {self.unique_id_array}')

        self.ble_scan = True

        if self.unique_id_array:
            for mesh_id in self.unique_id_array:
                self.ble_scan_result[mesh_id] = {
                    'ACK': False,
                    'START_TIME': None,
                    'START_TIMESTAMP': None,
                    'RESPONSE_WAIT_TIME': None,
                }
        else:
            print('Should not have started BLE scan - No Nodes Discovered')
        

    def endBleScan(self):
        ''' 
        Function called when BLE scan ends 
        
        -> changes filename (if we are doing a CONTINOUS loop we want a new file 
        -> and updates self vars essentially a reset() (and other things)
        '''

        print('------- SCAN RESULTS -------')
        # First parse all the result data into the current file
        for result_mesh_id in self.ble_scan_result:
            fileStr = f"{self.ble_scan_result[result_mesh_id]['TR_TIMESTAMP']}, {result_mesh_id}, {self.ble_scan_result[result_mesh_id]['ACK']}"
            print(fileStr)
            self.writeToFile(text=fileStr)

        # Reset -> Call init_file() after this with new filename (if its continuous)
        self.init_file_bool = False 
        self.ble_scan = False
        self.ble_scan_result = {}
        self.unique_id_array = []

    
    def writeToFile(self, text):
        ''' Write data into the csv -> can be called from run.py'''

        try:
            with open(self.filename, 'a') as f:
                f.write(text)
                f.write('\n')
        except Exception as e:
            print(f'Error Writing to File: {e}')


    def _scrape(self):
        ''' Thread that scrapes the Serial Data '''

        try: 
            while True: 
                out = ''
                time.sleep(0.25)
                
                while self.ser.inWaiting() > 0:
                    out += self.ser.read(1).decode("latin-1")
                    
                if len(out) > 1:
                    # Need to remove the ansi escape chars (color) if firmware > 2.3.15 - Nothing happens if firmware < 2.3.15 so no need to remove
                    # Review remove_ansi_escape if serial output text is strange/garbled
                    self._parseScrapeData(remove_ansi_escape(out)) 

        except Exception as e: 
            print(f"Exception in rxThread --> Closing Serial: {e}")
            self.close()
            

    def _parseScrapeData(self, serialOutput):
        ''' Function to parse the raw serial data into a file with a specified path '''

        outSplit = serialOutput.split('\n')

        if len(outSplit) > 1:
            importantContents = []
            messageType = '/'
            traceRoute = ''
            
            for line in outSplit:
                print(line) # For debugging

                # Hacky method of processing traceroutes: finding the "-->" in the line
                if '-->' in line:
                    
                    #For each word in the line find the index of '-->'
                    for i in range(len(line.split(' '))):
                        if line.split(' ')[i] == '-->':

                            if self.ble_scan:
                                #Function to handle traceroute responces if we are using ble to scan
                                self._ble_scan_traceroute_response(line, i)

                            try: 
                                # If this is the first time get the before and after 
                                if traceRoute == '':
                                    traceRoute = line.split(' ')[i-1] + ' --> ' + line.split(' ')[i+1]

                                # We have a multi traceroute (more than 1 '-->')
                                else:
                                    traceRoute += ' --> ' + line.split(' ')[i+1]
                            except:
                                pass

                # Hacky method of finding the message type: where is says "Recived" it says the message type after:
                if 'Received' in line:
                    for i in range(len(line.split(' '))):
                        if line.split(' ')[i] == 'Received':
                            try: 
                                messageType += line.split(' ')[i + 1]
                                messageType += '/'
                            except:
                                pass
            
                # The requirements for a word to be considered important and retained:
                importantContents.extend([x for x in line.split(' ') if ('=' in x) or ('ms' in x)])

            # findOccourance finds the first occourance - sorting ensures its the longest (most info)
            importantContents.sort(key=lambda s: len(s))
            importantContents.reverse()

            self.broadcastInfo['TIME'] = datetime.datetime.now().strftime("%Y%m%d_%H:%M:%S") 
            self.broadcastInfo['MESSAGE_TYPE'] = messageType if messageType != '/' else 'N/A' #Replace '/' with 'N/A'
            self.broadcastInfo['AIR_TIME'] = findOccourance([word for word in importantContents if 'g' not in word], 'ms')
            self.broadcastInfo['RX_TIME'] = findOccourance(importantContents, 'rxtime=') 
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

            # Don't write to file if: self update, No message ID, encrypted, while we are sending traceroutes and waiting for responses, etc
            # Also wait for the file_init() to be run before trying to write too it .... (Still want to print the outputs)

            if (self.broadcastInfo['NODE_ID'] not in ['0x0', 'N/A', self.base_id]) and (self.broadcastInfo['MESSAGE_ID'] != 'N/A') and (self.init_file_bool) and not (self.ble_scan):

                with open(self.filename, 'a') as f:
                    f.write(','.join(str(x) for x in self.broadcastInfo.values()))
                    f.write('\n')
            
                # If we havent seen this NODE_ID before append to unique_id_array
                if self.broadcastInfo['NODE_ID'] not in self.unique_id_array:
                    self.unique_id_array.append(self.broadcastInfo['NODE_ID'])
                    print(self.unique_id_array)


    def _ble_scan_traceroute_response(self, line, index):
        ''' 
        If we are scanning for responses: Get the ACK=True or False from the traceroute
        
        If self.ble_scan (we are looking for traceroute responses) - if we recive a traceroute with an ID we are looking for 
        ACK=True, otherwise ACK=False

        '''

        try:
            trace_mesh_id = line.split(' ')[index+1].replace('\r', '')
            if trace_mesh_id in self.unique_id_array:
                # We have a TraceRoute with the correct ID -> ACK = True (Need to remove '\r)
                
                if not (self.ble_scan_result[trace_mesh_id]['ACK']) and (self.ble_scan_result[trace_mesh_id]['START_TIME'] is not None): 
                    # If we have already seen it or havent started looking for it yet move on (if START_TIME has been set we have sent a traceroute to this one)
                    # Otherwise update result dict
            
                    self.ble_scan_result[trace_mesh_id]['ACK'] = True
                    self.ble_scan_result[trace_mesh_id]['RESPONSE_WAIT_TIME'] = time.time() - self.ble_scan_result[trace_mesh_id]['START_TIME']
                
        # We are looking for baseID or the result dict does not have the ID we have found - The if checks should catch this before an Exception ...
        except Exception as e:
            print(f'Exeption in scanning ble response: {e}')
            pass


if __name__ == '__main__':
    folder_path = datetime.datetime.now().strftime(f"dataGathering/%Y_%m_%d/")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")

    for port in list_ports.comports():
        if port.vid is not None:
            print(f" Serial Port Found: {port.device}")
            port_dev = port.device

    print('Init MeshScraper')
    meshScraper = MeshScraper(ser_port=port_dev)
    meshScraper.begin()

    # Running this as main just outputs the serial data to terminal - no need to save it to a csv ....

    # filename = datetime.datetime.now().strftime(f"SCRAPE_SERIAL_%Y%m%d_%H:%M:%S.csv")
    # meshScraper.init_file(filename=folder_path + filename) 

    try:
        counter = 0
        while True:
            counter += 1
            time.sleep(1)
            print(counter)
    except KeyboardInterrupt:
        print('\n Terminating MeshScraper')
        meshScraper.close()
