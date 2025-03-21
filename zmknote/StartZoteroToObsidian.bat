:: Starts the zotero item to obsidian note receiver .exe file
:: You can min it to the taskbar and reopen it to check status.
:: Handiest if you create a shortcut to this, and put it on your desktop

:: TODO? Turn this into an executable so can paste to taskbar?

@echo off
cd /d C:\Users\scott\OneDrive\share\ref\refwrangle\zmknote\dist
start "" zotero_to_obsidian_note_receiver.exe
powershell -command "& {Add-Type -TypeDefinition '[DllImport(\"user32.dll\")] public static extern bool ShowWindow(System.IntPtr hWnd, int nCmdShow); [DllImport(\"kernel32.dll\")] public static extern IntPtr GetConsoleWindow(); public static void Minimize() { ShowWindow(GetConsoleWindow(), 6); }' -Name 'WinAPI' -Namespace 'WinAPI'; [WinAPI.WinAPI]::Minimize();}"

