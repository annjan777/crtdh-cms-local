# One-time setup on Windows. In PowerShell, from the folder that contains publish_agent\ :
#   powershell -ExecutionPolicy Bypass -File publish_agent\install\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\..")
$py = (Get-Command py -ErrorAction SilentlyContinue)
if ($py) { $python = "py"; $pyargs = @("-3") } else { $python = "python"; $pyargs = @() }
& $python @pyargs -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 'Python 3.10 or newer is needed')"
if (-not (Test-Path .venv)) { & $python @pyargs -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& .\.venv\Scripts\python.exe -m pip install --require-hashes -r publish_agent\requirements.txt
if (-not (Test-Path config.ini)) { Copy-Item publish_agent\config.example.ini config.ini }
New-Item -ItemType Directory -Force keys, state | Out-Null
if (-not (Test-Path keys\crtdh_publish_ed25519)) {
  & .\.venv\Scripts\python.exe -m publish_agent keygen keys\crtdh_publish_ed25519
}
if (-not (Test-Path agent-secret.txt)) { New-Item -ItemType File agent-secret.txt | Out-Null }
if (-not (Test-Path access-secret.txt)) { New-Item -ItemType File access-secret.txt | Out-Null }
# Only the current user may read the key and the secrets.
foreach ($f in @("keys\crtdh_publish_ed25519", "agent-secret.txt", "access-secret.txt")) {
  icacls $f /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null
}
Write-Host ""
Write-Host "Done. Next (see publish_agent\README.md):"
Write-Host "  1. Put this public key on the server:  $(Get-Content keys\crtdh_publish_ed25519.pub)"
Write-Host "  2. Paste the agent secret into agent-secret.txt and the Cloudflare Access client secret into access-secret.txt (one line each)."
Write-Host "  3. Edit config.ini (user, cms url), then:  .\.venv\Scripts\python.exe -m publish_agent check --trust-host-key"
