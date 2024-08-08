#Usefull functions for parsing scraped data etc
import re

def remove_ansi_escape(output):
    ''' Function removes ansi escape charictors 
    -> theese produce the color in terminal output in device firmware > 2.3.15'''
    # Regex pattern to match ANSI escape codes
    # ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    ansi_escape = re.compile(r'(?:\x1b[@-_][0-?]*[ -/]*[@-~])') #More thorough
    
    # Remove ANSI escape codes
    cleaned_output = ansi_escape.sub('', output)

    # Remove null characters
    cleaned_output = cleaned_output.replace('\x00', '')

    #Considering adding '\x1b[0m' to the output to ensure the terminal is always white (asi escape reset)
    
    return cleaned_output



def findOccourance(listToSearch, tragetString):
    for i in range(len(listToSearch)):
        if tragetString in listToSearch[i]:
            # First half replaces what we are looking for with '', second removes anything in "(),"
            returnString = listToSearch[i].replace(tragetString, '').translate({ord(c): None for c in '(),'})            
            # Hacky again - If after removing all the above, it things msg= is the time (searching for ms) - so if it still includes an '=' its wrong 
            if '=' in returnString:
                continue
            else:
                return returnString.replace('\r', '') #If it includes '\r' remove it

    #If its not there return N/A
    return 'N/A'