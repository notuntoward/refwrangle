Get-ChildItem -Path . -Filter *.py -Recurse | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $file = $_.FullName
    
    if ($content -match "import PyQt5|from PyQt5 import") { 
        [PSCustomObject]@{ File = $file; Binding = "PyQt5" }
    }
    if ($content -match "import PyQt6|from PyQt6 import") { 
        [PSCustomObject]@{ File = $file; Binding = "PyQt6" }
    }
    if ($content -match "import PySide2|from PySide2 import") { 
        [PSCustomObject]@{ File = $file; Binding = "PySide2" }
    }
    if ($content -match "import PySide6|from PySide6 import") { 
        [PSCustomObject]@{ File = $file; Binding = "PySide6" }
    }
} | Group-Object -Property Binding | ForEach-Object {
    [PSCustomObject]@{
        Binding = $_.Name
        Count = $_.Count
        Files = ($_.Group | Select-Object -ExpandProperty File) -join ", "
    }
} | Format-Table -AutoSize
