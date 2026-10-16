# Windows equivalent of the Makefile:  .\make.ps1 up | down | migrate | seed | test | backup | restore [file]
param([Parameter(Position = 0)][string]$Target = "help", [Parameter(Position = 1)][string]$File = "")

# Native commands report failure through $LASTEXITCODE (checked in Run). Do not use
# $ErrorActionPreference = "Stop": PowerShell 5.1 would treat Docker's progress output on stderr as an error.
Set-Location $PSScriptRoot

function New-Secret([int]$bytes) {
    $buffer = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    return [Convert]::ToBase64String($buffer).Replace("+", "-").Replace("/", "_")
}

function Ensure-Env {
    # First run: create .env from .env.example with random secrets (Fernet key = url-safe base64 of 32 bytes).
    if (-not (Test-Path ".env")) {
        $values = @{
            "DJANGO_SECRET_KEY"       = (New-Secret 48)
            "FIELD_ENCRYPTION_KEY"    = (New-Secret 32)
            "POSTGRES_PASSWORD"       = (New-Secret 18)
            "POWERBI_READER_PASSWORD" = (New-Secret 18)
        }
        $lines = Get-Content ".env.example" | ForEach-Object {
            $name = ($_ -split "=", 2)[0]
            if ($values.ContainsKey($name)) { "$name=$($values[$name])" } else { $_ }
        }
        [System.IO.File]::WriteAllText((Join-Path $PSScriptRoot ".env"), (($lines -join "`n") + "`n"))
        Write-Host "Created .env with random secrets (keep this file private)."
    }
}

function Run([string[]]$cmd) {
    & $cmd[0] $cmd[1..($cmd.Length - 1)]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Target) {
    "up"             { Ensure-Env; Run @("docker", "compose", "up", "-d", "--build"); Write-Host "SME-ERP is starting at https://localhost" }
    "env"            { Ensure-Env }
    "down"           { Run @("docker", "compose", "down") }
    "build"          { Ensure-Env; Run @("docker", "compose", "build") }
    "logs"           { Run @("docker", "compose", "logs", "-f", "--tail=100") }
    "migrate"        { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "migrate") }
    "makemigrations" { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "makemigrations") }
    "seed"           { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "seed_demo", "--reset") }
    "test"           {
        Ensure-Env
        Run @("docker", "compose", "run", "--rm", "web", "pytest", "--cov", "--cov-report=term", "--cov-report=html", "--cov-report=xml")
        Run @("docker", "compose", "run", "--rm", "web", "coverage", "report", "--include=*/services.py,*/cleansing.py,*/importers.py,*/builder.py,*/audit.py", "--fail-under=80")
    }
    "shell"          { Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "shell") }
    "createsuperuser"{ Ensure-Env; Run @("docker", "compose", "run", "--rm", "web", "python", "manage.py", "createsuperuser") }
    "cert"           { Run @("docker", "compose", "run", "--rm", "-e", "FORCE=1", "certs") }
    "backup"         { Run @("docker", "compose", "exec", "cron", "/scripts/backup.sh") }
    "restore"        {
        if (-not $File) { $File = "latest" }
        Run @("docker", "compose", "stop", "web")
        & docker compose exec -it cron /scripts/restore.sh $File
        Run @("docker", "compose", "start", "web")
    }
    default          { Write-Host "Usage: .\make.ps1 up | down | migrate | seed | test | backup | restore <file> | logs | shell | cert" }
}
