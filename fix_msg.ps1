param([string]$file)
$content = Get-Content $file -Raw
$content = $content -replace '^pick ea2686a', 'reword ea2686a'
$content | Set-Content $file -NoNewline
