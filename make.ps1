# Windows equivalent of the Makefile:  .\make.ps1 up | down | migrate | seed | test | backup | restore [file]
param([Parameter(Position = 0)][string]$Target = "help", [Parameter(Position = 1)][string]$File = "")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Ensure-Env {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example - edit the secrets."
    }
}

function Run([string[]]$cmd) {
    & $cmd[0] $cmd[1..($cmd.Length - 1)]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Target) {
    "up"             { Ensure-Env; Run @("docker", "compose", "up", "-d", "--build"); Write-Host "SME-ERP is starting at https://localhost" }
    "down"           { Run @("docker", "compose", "down") }
    "build"          { Ensure-Env; Run @("docker", "compose", "build") }
    "logs"           { Run @("docker", "compose", "logs", "-f", "--tail=100") }
    "migrate"        { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "migrate") }
    "makemigrations" { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "makemigrations") }
    "seed"           { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "seed_demo", "--reset") }
    "test"           { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "pytest") }
    "shell"          { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "shell") }
    "createsuperuser"{ Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "createsuperuser") }
    "cert"           { Run @("docker", "compose", "run", "--rm", "-e", "FORCE=1", "certs") }
    "backup"         { Run @("docker", "compose", "exec", "cron", "/scripts/backup.sh") }
    "restore"        { Run @("docker", "compose", "exec", "cron", "/scripts/restore.sh", $File) }
    default          { Write-Host "Usage: .\make.ps1 up | down | migrate | seed | test | backup | restore <file> | logs | shell | cert" }
}
