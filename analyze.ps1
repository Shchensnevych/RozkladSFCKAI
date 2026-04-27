$lines = Get-Content 'rasp.txt' -Encoding UTF8 | Where-Object { $_.Trim() -ne '' }
$teachers = @{}

foreach ($line in $lines) {
    $parts = @()
    $current = ''
    $inQ = $false
    for ($i = 0; $i -lt $line.Length; $i++) {
        $c = $line[$i]
        if ($c -eq '"') { $inQ = -not $inQ }
        elseif ($c -eq ',' -and -not $inQ) { $parts += $current.Trim().Trim('"'); $current = '' }
        else { $current += $c }
    }
    $parts += $current.Trim().Trim('"')
    if ($parts.Count -lt 8) { continue }

    $tid = $parts[1]
    $fam = $parts[2]
    $lesson = $parts[7]

    if (-not $teachers.ContainsKey($fam)) { $teachers[$fam] = @{} }
    if (-not $teachers[$fam].ContainsKey($tid)) { $teachers[$fam][$tid] = @() }
    if ($teachers[$fam][$tid] -notcontains $lesson) { $teachers[$fam][$tid] += $lesson }
}

Write-Host "`n=== Викладачі з однаковим прізвищем але різними ID ==="
foreach ($fam in ($teachers.Keys | Sort-Object)) {
    if ($teachers[$fam].Count -gt 1) {
        Write-Host "`n--- $fam ---" -ForegroundColor Yellow
        foreach ($tid in $teachers[$fam].Keys) {
            $lessons = $teachers[$fam][$tid] -join ', '
            Write-Host "  tid=$tid : $lessons"
        }
    }
}
