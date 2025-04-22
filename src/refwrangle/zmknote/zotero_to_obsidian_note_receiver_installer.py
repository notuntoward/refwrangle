"""Installs a compiled zotero_to_obsidian_note_listener.py as a Windows Service.
Will restart it on boot or if it crashes.

To install:

python zotero_to_obsidian_note_sender.py install

To start it right after install (do this when you change the listener, etc.)

python zotero_to_obsidian_note_receiver_installer.py start

To uninstall (remove from Windows Registry):

python zotero_to_obsidian_note_receiver_installer.py remove

"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import subprocess
from pathlib import Path
import logging

# Path to receiver executable
RECEIVER_EXECUTABLE = Path(r'C:\Users\scott\OneDrive\share\ref\refwrangle\zmknote\dist\zotero_to_obsidian_note_receiver.exe')

# logfile shared with the receiver script
RECEIVER_LOG_FILE = "zotero_item_receiver.log"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(RECEIVER_LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ZoteroObsidianService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ZoteroObsidianService"
    _svc_display_name_ = "Zotero to Obsidian Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        logger.debug("Service initialized.")

    def SvcStop(self):
        logger.info("Stopping service...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        logger.info("Starting service...")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        try:
            self.main()
        except Exception as e:
            logger.error(f"Error while running service: {e}", exc_info=True)

    def main(self):
        try:
            logger.info(f"Starting executable: {RECEIVER_EXECUTABLE}")
            # Use subprocess.Popen instead of os.system()
            process = subprocess.Popen(
                [str(RECEIVER_EXECUTABLE)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            logger.info(f"Executable started with PID: {process.pid}")
            # Wait for the process to complete or monitor it as needed
            process.communicate()
        except Exception as e:
            logger.error(f"Failed to execute the receiver: {e}", exc_info=True)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ZoteroObsidianService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        try:
            logger.info(f"Running command: {' '.join(sys.argv)}")
            win32serviceutil.HandleCommandLine(ZoteroObsidianService)
        except Exception as e:
            logger.error(f"Error handling command line: {e}", exc_info=True)
