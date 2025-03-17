"""Installs a compiled zotero_to_obsidian_note_listener.py as a Windows Service.
Will restart it on boot or if it crashes.

To install:

python this_script.py install

To start it right after install (do this when you change the listener, etc.)

python this_script.py start

To uninstall (remove from Windows Registry):

python this_script.py remove

"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os

class ZoteroObsidianService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ZoteroObsidianService"
    _svc_display_name_ = "Zotero to Obsidian Service"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
    
    def main(self):
        # Path to your executable
        exe_path = os.path.abspath("zotero_to_obsidian_note_listener.exe")
        os.system(f'"{exe_path}"')

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ZoteroObsidianService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ZoteroObsidianService)