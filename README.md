# SHAREM

Welcome to SHAREM! 

SHAREM is intended to be the ultimate Windows shellcode tool, with support to emulate over 12,000 WinAPIs, virtually all user-mode Windows syscalls, and SHAREM provides numerous new features. SHAREM was released on September 29, 2022, at Virus Bulletin, the top malware conference globally. SHAREM contains an emulator, a disassembler, timeless debugging, brute-force deobfuscation, and many other features. SHAREM's emulator can also display complete structures (or even structures within structures) and it can allow encoded shellcode to deobfuscate itself. SHAREM logs output from all WinAPIs and Windows syscalls analyzed, and it also breaks each into many categories and subcategories. SHAREM's complete code coverage also allows it to discover unreachable functionality.

SHAREM's disassembler is able to integrate discovered functions into the disassembly, labelling each in the disassembler. SHAREM also will displayed the decrypted form of encoded shellcode in the disassembler, so it is not necessary to debug shellcode.

We have created a [SHAREM Wiki](https://github.com/Bw3ll/sharem/wiki) that provides some instructional  information on SHAREM usage, although there are significant portions and features not currently documented. SHAREM has been developed over a period of two years with several people working on it. SHAREM's disassembler is significantly more accurate than leading disassemblers. Additionally, SHAREM can integrate emulation data into the disassembler, allowing for nearly flawless disassembly to be obtained.

Please be aware that as SHAREM has just been released, the documentation on here is a little sparse. We will update the GitHub with more information as well in the coming weeks.

If you are new to SHAREM, feel free to check out a brief demo video, showcasing some of its capabilities Click on image to view demo:
[![Watch the video](https://github.com/Bw3ll/sharem/blob/testing/sharem/SHAREM_images/Sharem_demo.png?raw=true)](https://youtu.be/S1PI9O-q6eM)

# Install Instructions
## Updates
Sept. 29, 2022: We did make a very minor update to the setup.py regarding numpy, which may affect some people with the latest version of Python.

## Windows
SHAREM is installed as a local Python package, so that we have access to it in other projects. This allows parts of SHAREM to be imported. Thus, it must be installed as a package.

1. Git is required for installation of sharem. 
It can be installed from https://git-scm.com/download/win. After installion restart computer and continue with SHAREM install. The Git is to automate the installation of the Windows SSDeep. You can also manually do this and modify the .bat to exclude the SSDeep, if you do it yourself.

2. Run .bat file. It will call the setup.py file. Depending on how you call Python, you may need to call the alternate .bat file or even modify it slightly, if using something nonstandard.

3. Do
```py -m pip list``` or  ```python3 -m pip list``` to verify that that SHAREM is installed locally as a package. It must be installed as a package to work.


## Linux
1. ```chmod +x linux_installer.sh``` Enable Execution of the Installer
2. ```sudo ./linux_installer.sh``` Execute the Installer
3. Add DLL Files

You will need to add the Windows DLL files. We do not currently these available as a separate download for Linux users. At this time, users would need harvest them by installing it via Windows. (Note: These DLLs MUST be inflated by SHAREM. Dlls cannot be used if not inflated.) Later, we will provide these as a separate download in the coming weeks.

# Documentation
Documentation can be found at the [SHAREM Wiki](https://github.com/Bw3ll/sharem/wiki), which provides some instructional  information on SHAREM usage, although there are significant portions and features not currently documented. 

# Screenshots
SHAREM is a very powerful framework with numerous capabilities, some well documented, and some which are not. This section will showcase a small number of those capabilities. 

SHAREM can take an encoded shellcode and deobfuscate it through emulation. Not only does it capture all WinAPI or syscall information, but if you choose to view it in the disassembler, it shows you the decoded form of the shellcode:

![image](https://github.com/Bw3ll/sharem/blob/testing/sharem/SHAREM_images/encodedShellcode.png?raw=true)

SHAREM not only can ennumerate 12,000+ WinAPI functions, but it can also do so with virtually all user-mode Windows syscalls. In addition, for some it displays structure information. For those dealing with the registry, it will extract registry information and add that to our Registry Manager:

![image](https://user-images.githubusercontent.com/49998815/204032319-1e10d3cc-dfc0-49e8-912d-9629571a1144.png)

SHAREM also has the ability to download files via UrldownloadToFileA, if they exist. These are downloaded into the emulator's memory - not saved to disk. If successful, it will capture the hash. There is also a limited pseudo file system, and so you can see correlations, such as a file being downloaded as one thing and renamed to another. If the needed download is not available, it will simply be simulated as a successful download. Live downloading is an option can be enabled or disabled in the config

![image](https://github.com/Bw3ll/sharem/blob/testing/sharem/SHAREM_images/downloading.png?raw=true)


# Co-Authors and Contributors
Dr. Bramwell Brizendine, Austin Babcock, Jake Hince, Shelby VandenHoek, Sascha Walker, Tarek Abdelmotaleb, Evan Read, Dylan Park, Kade Brost, and Aaron Baker.

# Acknowledgement
This research and some co-authors have been supported by NSA Grant H98230-20-1-0326.