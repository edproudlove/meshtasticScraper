# Scrapes the Mesh information from the serial port and enters it into the CSV
# This runs in the background for entire thing, after xxx time the BLE will be submitted
# Using Threading -> MeshScaper Obj 

import time 
import datetime
import serial 
from serial.tools import list_ports
import threading
from utils import findOccourance

# /dev/cu.usbmodemDC5475EE06B41 -> 06b4 firmware version 2.3.12
# /dev/cu.usbmodemDC5475EDEE941 -> ee94 firmware version 2.3.16
# /dev/cu.usbmodemDC5475EE06DC1 -> 06dc fimrware version 2.3.13

#Might be able to do BLE stuff from in here aswell
class MeshScraper():
    def __init__(self, ser_port, filename):
        self.ser = serial.Serial(port=ser_port, baudrate=115200)
        self.filename = filename

        self.firstTime = True
        self.unique_id_array = []
        self.baseStationID = None

        self.CurrMeshID = None
        self.BleTraceRouteACK = False
        self.bleScan = False


        self.meshTread = threading.Thread(target=self.scrape, args=(), daemon=True)

    
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

        #Might Need Editing -> Not sure this is getting triggered, and its already closing anyway
        except Exception as e: 
            print(f"Exception in rxThread --> Closing Serial: {e}")
            self.close()


    def startBleScan(self, updated_filename):
        ''' Function called when BLE scan starts -> changes filename and updates firstTime '''
        self.filename = updated_filename
        self.firstTime = True
        self.bleScan = True

    def endBleScan(self, updated_filename):
        ''' Function called when BLE scan ends -> changes filename and updates firstTime '''
        self.filename = updated_filename
        self.firstTime = True
        self.bleScan = False
    
    
    def writeToCurrFile(self, text):
        ''' Write Text into the csv '''
        try:
            with open(self.filename, 'a') as f:
                f.write(text)
                f.write('\n')
        except:
            print('Error Writing to File')
            


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
                    
                    # We have a TraceRoute with the correct ID -> ACK = True
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

            # findOccourance finds the first occourance - sorting ensures its the longest occourance (could do it in frunction but then it would sort it over and over again - ineffecint) 
            importantContents.sort(key=lambda s: len(s))
            importantContents.reverse()

            broadcastInfo = {
                'TIME': datetime.datetime.now().strftime("%Y%m%d_%H:%M:%S"), 
                'MESSAGE_TYPE': messageType if messageType != '/' else 'N/A', #Replace '/' with 'n/a'
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

            #Dont write it in if its a self update / broadcast to self (from=0x00) / No message ID / (encrypted etc) -> Need to get my own ID and stop that too
            if broadcastInfo['NODE_ID'] != '0x0' and broadcastInfo['NODE_ID'] != 'N/A' and broadcastInfo['MESSAGE_ID'] != 'N/A': 
                
                #If this is the first run then also put the Keys in
                if self.firstTime:
                    with open(self.filename, 'w') as f:
                        self.firstTime = False
                        f.write(','.join(broadcastInfo.keys()))
                        f.write('\n')
                        f.write(','.join(str(x) for x in broadcastInfo.values()))
                        f.write('\n')

                else:
                    with open(self.filename, 'a') as f:
                        f.write(','.join(str(x) for x in broadcastInfo.values()))
                        f.write('\n')
            
            # If we havent seen this UsersID before append to the UNIQUE list
            if broadcastInfo['NODE_ID'] not in self.unique_id_array and broadcastInfo['NODE_ID'] not in ['N/A', self.baseStationID] and not self.bleScan:
                self.unique_id_array.append(broadcastInfo['NODE_ID'])
                print(self.unique_id_array) 


if __name__ == '__main__':
    FILENAME = datetime.datetime.now().strftime("scrapeData/SCRAPE_SERIAL_%Y%m%d_%H:%M:%S.csv")

    portList = list_ports.comports()
    for i in range(len(portList)):
        port = portList[i]
        if port.vid is not None:
            print(port.device)
            port_dev = port.device

    print('Init MeshScraper')
    meshScraper = MeshScraper(ser_port= port_dev, filename=FILENAME)
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
