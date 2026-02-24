"""Installs a compiled zotero_to_obsidian_note_listener.py as a Windows Service.
Will restart it on boot or if it crashes.

To compile:

uv run pyinstaller --runtime-tmpdir=. --hidden-import win32timezone --exclude-module PyQt5 --exclude-module PySide6 --onefile zotero_to_obsidian_note_receiver.py

To install, in an admin terminal, type:

uv run zotero_to_obsidian_note_receiver_installer.py install

and you should see a message that ZoteroObsidianService has been installed.

To start it right after install (do this when you change the listener, etc.)

uv run zotero_to_obsidian_note_receiver_installer.py start

Howver, at this point, it doesn't start.  The error is:

2025-05-02 21:10:21,649 - INFO - Handling command line: zotero_to_obsidian_note_receiver_installer.py start
Starting service ZoteroObsidianService
Error starting service: The service did not respond to the start or control request in a timely fashion.

To uninstall (remove from Windows Registry):

uv run zotero_to_obsidian_note_receiver_installer.py remove

"""

import win32serviceutil
import win32service
import win32event
# import servicemanager # No longer explicitly needed
import sys
import subprocess
from pathlib import Path
import logging

# Path to receiver executable (relative to project root)
RECEIVER_EXECUTABLE = Path(__file__).parent / 'dist' / 'zotero_to_obsidian_note_receiver.exe'

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
        # We use a boolean flag to prevent running self.main() multiple times
        # if SvcDoRun is called unexpectedly after the service is already running.
        self.is_running = False
        logger.debug("Service initialized.")

    def SvcStop(self):
        logger.info("Stopping service...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        # Reset the running flag when stopping
        self.is_running = False
        logger.info("Stop event set.")

    def SvcDoRun(self):
        logger.info("Service run requested...")
        # Ensure the main logic runs only once
        if not self.is_running:
            self.is_running = True
            logger.info(f"Starting service logic for {self._svc_name_}...")
            # Replace servicemanager.LogMsg with standard logging
            # Note: This logs to your file/console, not the Windows Event Log directly
            # like servicemanager.LogMsg does, but provides similar information.
            logger.info(f"Service {self._svc_name_} started.")
            try:
                self.main()
                # Once main completes (e.g., process exits), log that the service logic finished
                logger.info(f"Service {self._svc_name_} run loop finished.")
                # Report SERVICE_STOPPED status *only if* the stop wasn't requested.
                # If SvcStop was called, it already handles setting the status.
                # However, win32serviceutil typically handles this transition automatically
                # when SvcDoRun exits cleanly. We might not need explicit status setting here.
                # self.ReportServiceStatus(win32service.SERVICE_STOPPED) # Usually not needed here
                self.is_running = False # Mark as not running
            except Exception as e:
                logger.error(f"Error while running service main function: {e}", exc_info=True)
                # Report stopped status on error
                self.ReportServiceStatus(win32service.SERVICE_STOPPED)
                self.is_running = False # Mark as not running
        else:
            logger.warning("SvcDoRun called while already running. Ignoring.")


    def main(self):
        process = None # Initialize process variable
        try:
            logger.info(f"Starting executable: {RECEIVER_EXECUTABLE}")
            # Use subprocess.Popen instead of os.system()
            process = subprocess.Popen(
                [str(RECEIVER_EXECUTABLE)],
                stdout=subprocess.PIPE, # Consider redirecting to files or using logger if needed
                stderr=subprocess.PIPE, # Consider redirecting to files or using logger if needed
                # shell=True # Generally safer to avoid shell=True if possible
                               # It's okay here since RECEIVER_EXECUTABLE is a fixed path
                               # but if it were constructed from user input, it's risky.
                               # Using a list of args like above avoids shell=True implicitly.
                creationflags=subprocess.CREATE_NO_WINDOW # Optional: hide console window
            )
            logger.info(f"Executable started with PID: {process.pid}")

            # Wait for the process to complete OR for the stop event
            while True:
                # Check if the stop event is set
                wait_result = win32event.WaitForSingleObject(self.stop_event, 1000) # Check every second
                if wait_result == win32event.WAIT_OBJECT_0:
                    # Stop event was signaled
                    logger.info("Stop event received, terminating executable...")
                    break # Exit the loop to stop the service

                # Check if the subprocess has terminated on its own
                if process.poll() is not None:
                    logger.info(f"Executable process {process.pid} terminated on its own with return code {process.returncode}.")
                    break # Exit the loop as the process finished

            # If we broke the loop due to stop event, terminate the process
            if process and process.poll() is None:
                logger.info(f"Attempting to terminate process {process.pid}...")
                process.terminate()
                try:
                    # Wait a bit for graceful termination
                    process.wait(timeout=5)
                    logger.info(f"Process {process.pid} terminated gracefully.")
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process {process.pid} did not terminate gracefully, killing.")
                    process.kill()
                    logger.info(f"Process {process.pid} killed.")

        except Exception as e:
            logger.error(f"Failed to execute or monitor the receiver: {e}", exc_info=True)
            # Ensure process is terminated if an error occurs in the monitoring loop
            if process and process.poll() is None:
                 try:
                     logger.warning(f"Terminating process {process.pid} due to monitoring error.")
                     process.terminate()
                     process.wait(timeout=2)
                 except Exception as term_err:
                     logger.error(f"Error during process termination after failure: {term_err}", exc_info=True)
                     try:
                         process.kill()
                     except Exception as kill_err:
                         logger.error(f"Error killing process after failed termination: {kill_err}", exc_info=True)

        finally:
            # Log stdout/stderr if captured (optional)
            # stdout, stderr = process.communicate() if process else (None, None)
            # if stdout: logger.debug(f"Process stdout: {stdout.decode(errors='ignore')}")
            # if stderr: logger.error(f"Process stderr: {stderr.decode(errors='ignore')}")
            logger.info("Exiting main service logic function.")


if __name__ == '__main__':
    # win32serviceutil.HandleCommandLine handles dispatching to the service entry point
    # when no arguments are passed (i.e., when started by SCM),
    # as well as handling 'install', 'start', 'stop', 'remove', 'debug' arguments.
    # This replaces the need for the explicit servicemanager calls.
    try:
        logger.info(f"Handling command line: {' '.join(sys.argv)}")
        win32serviceutil.HandleCommandLine(ZoteroObsidianService)
    except Exception as e:
        logger.error(f"Error handling command line: {e}", exc_info=True)
        # Optionally add more specific error handling for service installation/removal failures if needed
