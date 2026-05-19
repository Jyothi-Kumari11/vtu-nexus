$shell = New-Object -ComObject Shell.Application
$bin = $shell.Namespace(10)
$items = $bin.Items()
Write-Output "Files in Recycle Bin:"
foreach ($item in $items) {
    if ($item.Name -like "*.py" -or $item.Name -like "*index*" -or $item.Name -like "*vtu*") {
        Write-Output ("Name: " + $item.Name + " | Path: " + $item.Path)
    }
}
Write-Output "Done."
