Get-ChildItem -Path . -Filter *.py -Recurse | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    
    if ($content -match "import PyQt5|from PyQt5 import") { "PyQt5" }
    if ($content -match "import PyQt6|from PyQt6 import") { "PyQt6" }
    if ($content -match "import PySide2|from PySide2 import") { "PySide2" }
    if ($content -match "import PySide6|from PySide6 import") { "PySide6" }
} | Group-Object | Select-Object Name, Count
