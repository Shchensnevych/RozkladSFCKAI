$lines = Get-Content 'rasp.txt' -Encoding UTF8 | Where-Object { $_.Trim() -ne '' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("const SCHEDULE_DATA = [")

foreach ($line in $lines) {
    # Parse CSV manually
    $parts = @()
    $current = ""
    $inQuotes = $false
    for ($i = 0; $i -lt $line.Length; $i++) {
        $c = $line[$i]
        if ($c -eq '"') {
            $inQuotes = -not $inQuotes
        } elseif ($c -eq ',' -and -not $inQuotes) {
            $parts += $current.Trim().Trim('"')
            $current = ""
        } else {
            $current += $c
        }
    }
    $parts += $current.Trim().Trim('"')
    
    if ($parts.Count -lt 8) { continue }
    
    $dt = ($parts[0] -split ' ')[0]
    $tid = $parts[1]
    $fam = $parts[2] -replace "'", "\'"
    $pair = $parts[3]
    $gid = $parts[4]
    $gname = $parts[5]
    $kod = $parts[6]
    $lesson = $parts[7] -replace "'", "\'"
    
    [void]$sb.AppendLine("{dt:`"$dt`",tid:$tid,fam:`"$fam`",pair:$pair,gid:$gid,gname:`"$gname`",kod:$kod,lesson:`"$lesson`"},")
}

[void]$sb.AppendLine("];")
Set-Content -Path 'data.js' -Value $sb.ToString() -Encoding UTF8
Write-Host "Done! Created data.js with $($lines.Count) records"
