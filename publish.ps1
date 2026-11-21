# Renders HTML slides to 1080x1350 PNGs, pushes them to GitHub, prints public raw URLs.
# Usage: .\publish.ps1 slide1.html slide2.html ...
param([Parameter(Mandatory, ValueFromRemainingArguments)][string[]]$Html)
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$chrome = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
$day = Get-Date -Format 'yyyy-MM-dd'
$out = Join-Path $repo "posts\$day"
New-Item -ItemType Directory -Force $out | Out-Null

$names = foreach ($h in $Html) {
  $src = (Resolve-Path $h).Path
  $name = [IO.Path]::GetFileNameWithoutExtension($src) + '.png'
  $png = Join-Path $out $name
  # virtual-time-budget lets web fonts load before the screenshot
  # Start-Process: chrome writes harmless warnings to stderr, which 'Stop' would treat as fatal
  Start-Process $chrome -Wait -WindowStyle Hidden -ArgumentList '--headless=new','--disable-gpu','--hide-scrollbars',
    '--window-size=1080,1350','--virtual-time-budget=5000',"--screenshot=`"$png`"","file:///$($src -replace '\\','/' -replace ' ','%20')"
  if (-not (Test-Path $png)) { throw "Render failed: $h" }
  Copy-Item $src (Join-Path $out ([IO.Path]::GetFileName($src))) -Force
  $name
}

git -C $repo add posts | Out-Null
git -C $repo commit -m "posts $day" | Out-Null
git -C $repo push -q -u origin master
if ($LASTEXITCODE) { throw 'git push failed' }

# commit-pinned URLs: branch URLs are CDN-cached ~5 min and could serve an older image
$sha = git -C $repo rev-parse HEAD
foreach ($n in $names) { "https://raw.githubusercontent.com/ammaratraat/cortiq-social/$sha/posts/$day/$n" }


