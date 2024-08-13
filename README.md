# Meshtastic Scraper

## Description
- Python code to scrape mesh network traffic through the serial port of the [Lilygo T3S3](https://www.lilygo.cc/products/t3s3-v1-0) board. Built on top of [Meshtastic Python](https://github.com/meshtastic/python).
- Used to create a dataset of file pairs: 2 minutes of network traffic -> whether TraceRoutes to each of the nodes in the mesh are acknowledged or not.
- `$ python run.py` will scrape the serial output of the node for 2 minuets, and parse every packet it receives into a file called `YYMMDD_HHMM_TestID_Band.csv` in a folder called `/data/YYMMDD/`.

- After 2 minuets, TraceRoutes are sent to each unique node we received a packet from during the ‘scraping’ phase. Whether we received a response from each is recorded in `YYMMDD_HHMM_TestID_Band_Power_Hoplimit.csv` (in the same folder as the previous file). See /data for examples.  

1. TestID = Random string of 12 chars, unique identifier for each pair of pre/post TraceRoute data
2. Band = Frequency band transmissions are done on (EU_868 MHz for this dataset)
3. Power = Transmission power measured in dB (lora.tx_power)
4. Hoplimit = Hop limit of the TraceRoutes sent

- Each can be set in `config.ini`, along with the time spent in the ‘scraping phase’ (interval) and the time the code will wait for a traceroute response before considering it failed/timeout (response).
- Continuous mode will loop the code – after receiving the traceroutes it will start scraping the network again. 


## Hardware Setup
1. Install firmware to the board: [Meshtastic Flasher](https://flasher.meshtastic.org) (or alternative method: [Meshtastic Firmware](https://github.com/meshtastic/firmware)).
2. Connect to the board via Bluetooth using the Meshtastic app on the same PC that is connected to it via serial (you may need to 'forget' the device in the PC's Bluetooth settings if you have previously connected to it via Bluetooth before a reset or firmware flash).
3. Set LoRa region to EU_868 (or the relevant region - remember to change `config.ini` / filename).
4. Disconnect Bluetooth from the node.
5. Update `config.ini` accordingly and follow the software steps.


## Software Setup
1. Create the pip virtual environment: change `meshScrapeEnv` to whatever name you want (Alternatively, use conda or whatever is prefered)
    ```bash
    python3 -m venv meshScraperEnv
    ```
2. Activate the environment
    ```bash
    source meshScraperEnv/bin/activate
    ```
3. Install packages
    ```bash
    pip install -r requirements.txt
    ```
4. Make a new directory and clone the git repo:
    ```bash
    git clone https://github.com/edproudlove/meshtasticScraper.git
    ```
5. With the environment activated, run the `run.py` file:
    ```bash
    python3 run.py
    ```

## Compatibility

#### Compatable board firmware versions (which firmware versions the run.py code works for - only considering Beta/Stable versions)
- 2.3.10 (2.3.10.d19607b) -> ✅ WORKS
- 2.3.11 (2.3.11.2740a56) -> ✅ WORKS 
- 2.3.12 (2.3.12.24458a7) -> ✅ WORKS  
- 2.3.13 (2.3.13.83f5ba0) -> ✅ WORKS 

###### Version 2.3.15 and above add colour to the serial debug - requires removal using utils.remove_ansi_escape()
- 2.3.15 (2.3.15.deb7c27) -> ✅ WORKS
- 2.4.0 (2.4.0.46d7b82) ->  ✅ WORKS
- 2.4.1 (2.4.1.394e0e1) ->  ✅ WORKS

#### Python meshtastic CLI versions (use reccomended version in the requirements.txt): 
- 2.3.11 -> ❌ FAILS 
- 2.3.12 -> ❌ FAILS 
- 2.3.13 -> ❌ FAILS 

###### In version 2.3.13 and below client.sendTraceRotue() and client.sendData() do not have a hoplimit argument as input - if you don't specify the hoplimit prvious versions should work
- 2.3.14 -> ✅ WORKS (sendTraceRoute hoplimit fixed in the changelogs: [Meshtastic Python Releases](https://github.com/meshtastic/python/releases))


## TODO Log

#### Done/Outdated

- Find the Bluetooth device we are connected to over serial and clear its nodeDB.
- The BLE will send traceRoutes to each Node in `meshScraper.unique_id_arr`.
- Response will be input into a NEW file (need to change `self.filename`).
- Make finding the BLE scanner dynamic.
- Add a Continuous mode or just run it once.
- End early if all Nodes are accounted for instead of waiting for the entire response time.
- Change the RX power antenna, etc.
- Add in how long we waited for a response for each Node - currently not in results but still in `mesh_scraper`.
- Ensure Bluetooth connection acceptance requires PC connected first if the node has been reset/new firmware; also requires LoRa region set (in hardware tutorial).
- Fix the Time-Out of the BLE interface is unreliable; if we get a response, tell the BLE to move on.
- Implement own timeouts / sendTraceRoute - Don’t use CLI.
- Flash most recent firmware and go through every step to make documentation/tutorial + conda/env setup from a fresh PC.
- Add a test ID because it's hard to tell what file and results are a pair.
- Add example data to github

#### Doing

- Document which firmware versions the code works for -> same for versions of Python CLI.
- Logging rather than prints - remove Meshtastic and Bleak logs.
- DEBUG settings for printing: Debug or Standby Mode.

#### TODO:

- How should the device be configured? On running the script, could send a `config.yml`: [Meshtastic CLI Configuration](https://meshtastic.org/docs/software/python/cli/) -> `$ meshtastic --configure example_config.yaml`
- Improve modularity -> can just clone from GitHub and run it (e.g., install.sh).
- Implement sendText instead of traceRoute.
- Find/set band dynamically.
- Handle multiple serial ports.
