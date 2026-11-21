# Posts an image album with a caption to the Cortiq Telegram channel.
# Usage: .\telegram.ps1 -Caption caption.txt image1.png image2.png
param([Parameter(Mandatory)][string]$Caption, [Parameter(Mandatory, ValueFromRemainingArguments)][string[]]$Images)
$ErrorActionPreference = 'Stop'
$token = [Environment]::GetEnvironmentVariable('TELEGRAM_BOT_TOKEN', 'User')
if (-not $token) { throw 'TELEGRAM_BOT_TOKEN is not set' }
$text = Get-Content $Caption -Raw -Encoding utf8

# curl.exe: PowerShell 5.1 has no multipart upload; --form-string keeps the caption literal
$media = @(); $files = @()
for ($i = 0; $i -lt $Images.Count; $i++) {
  $m = @{ type = 'photo'; media = "attach://p$i" }
  if ($i -eq 0) { $m.caption = $text }
  $media += $m; $files += '-F', "p$i=@$((Resolve-Path $Images[$i]).Path)"
}
$json = ConvertTo-Json -InputObject $media -Compress
$out = & curl.exe -s "https://api.telegram.org/bot$token/sendMediaGroup" --form-string 'chat_id=@CORTIQME' --form-string "media=$json" @files
if ($out -notmatch '"ok":true') { throw "Telegram error: $out" }
'Telegram: posted'
