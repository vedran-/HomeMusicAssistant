#Requires -Version 5.1
<#
.SYNOPSIS
    Sets up the Home Assistant Voice Control MVP environment.
.DESCRIPTION
    This script performs the following actions:
    1. Checks for Python 3.9+.
    2. Creates a Python virtual environment (.\.venv).
    3. Installs required Python packages from requirements.txt.
    4. Creates the directory for OpenWakeWord models if it doesn't exist.
    5. Reminds the user to configure AutoHotkey path and API keys in config.json.
    6. Reminds the user to copy music_controller.ahk and its Lib folder to src/tools.
.NOTES
    Run this script from the project root directory.
#>

param (
    [string]$VenvPath = ".\.venv"
)

function Test-PythonVersion {
    try {
        $pythonVersionOutput = python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Python not found or not in PATH. Please install Python 3.9+ and add it to your PATH."
            return $false
        }
        $pythonVersionString = ($pythonVersionOutput -split ' ')[-1]
        $pythonMajor = [int]($pythonVersionString -split '\.')[0]
        $pythonMinor = [int]($pythonVersionString -split '\.')[1]

        if ($pythonMajor -lt 3 -or ($pythonMajor -eq 3 -and $pythonMinor -lt 9)) {
            Write-Error "Python version 3.9 or higher is required. You have $pythonVersionString. Please upgrade your Python installation."
            return $false
        }
        Write-Host "Python version $pythonVersionString found. (OK)" -ForegroundColor Green
        return $true
    } catch {
        Write-Error "Error checking Python version: $_. Ensure Python 3.9+ is installed and in PATH."
        return $false
    }
}

function Create-VirtualEnvironment {
    param (
        [string]$Path
    )
    if (Test-Path $Path) {
        Write-Host "Virtual environment already exists at $Path." -ForegroundColor Yellow
    } else {
        Write-Host "Creating Python virtual environment at $Path..."
        python -m venv $Path
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create virtual environment. Ensure 'venv' module is available for your Python installation."
            return $false
        }
        Write-Host "Virtual environment created successfully." -ForegroundColor Green
    }
    return $true
}

function Install-Requirements {
    param (
        [string]$VenvPythonPath
    )
    Write-Host "Installing Python packages from requirements.txt..."
    # Ensure requirements.txt exists
    if (-not (Test-Path ".\requirements.txt")) {
        Write-Error ".\requirements.txt not found in the current directory."
        return $false
    }

    & $VenvPythonPath -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install Python packages. Check requirements.txt and your internet connection."
        return $false
    }
    Write-Host "Python packages installed successfully." -ForegroundColor Green
    return $true
}

function Ensure-ConfigExists {
    $templatePath = ".\config.template.json"
    $configPath = ".\config.json"

    if (-not (Test-Path $templatePath)) {
        Write-Warning "config.template.json not found. Cannot guide user for config.json creation."
        return
    }

    if (-not (Test-Path $configPath)) {
        Write-Host "
ACTION REQUIRED:
1. Copy '$templatePath' to '$configPath'.
2. Edit '$configPath' to provide your API keys (e.g., groq_api_key).
3. Verify paths like 'autohotkey_exe' and 'openwakeword_models_dir'.
" -ForegroundColor Yellow
    } else {
        Write-Host "config.json already exists. Please ensure it is correctly configured." -ForegroundColor Green
    }
}

function Ensure-OpenWakeWordModelDir {
    # This function assumes config.json might not be parsable yet by Python settings
    # A bit of a chicken-and-egg: we need config to know the path, but this script runs before config is fully validated.
    # For MVP, let's use the default path from the template or prompt user.
    $defaultModelDir = ".\models\openwakeword" # Matches config.template.json
    
    if (-not (Test-Path $defaultModelDir)) {
        Write-Host "Creating directory for OpenWakeWord models at $defaultModelDir..."
        try {
            New-Item -ItemType Directory -Path $defaultModelDir -Force -ErrorAction Stop | Out-Null
            Write-Host "Directory $defaultModelDir created." -ForegroundColor Green
            Write-Host "OpenWakeWord will attempt to download models to this directory on first use if they are not present." -ForegroundColor Cyan
        } catch {
            Write-Error "Failed to create directory $defaultModelDir. Please create it manually."
            return $false
        }
    } else {
        Write-Host "OpenWakeWord models directory $defaultModelDir already exists." -ForegroundColor Green
        Write-Host "OpenWakeWord will attempt to download models to this directory on first use if they are not present." -ForegroundColor Cyan
    }
    return $true
}

function Remind-AutoHotkeySetup {
    Write-Host "
AUTOHOTKEY SETUP:
1. Ensure AutoHotkey v2 is installed.
2. Verify the 'autohotkey_exe' path in your 'config.json' is correct.
3. Place your 'music_controller.ahk' script and its 'Lib' folder (containing UIA.ahk, UIA_Browser.ahk)
   into the 'src\tools' directory of this project.
" -ForegroundColor Yellow
}

# --- Main Script Execution ---
Write-Host "Starting Home Assistant Voice Control MVP Setup..." -ForegroundColor Cyan

if (-not (Test-PythonVersion)) {
    Exit 1
}

if (-not (Create-VirtualEnvironment -Path $VenvPath)) {
    Exit 1
}

$venvPipPath = Join-Path $VenvPath "Scripts\python.exe"
if ($IsCoreCLR) { # PowerShell Core (Linux/macOS)
    $venvPipPath = Join-Path $VenvPath "bin\python"
}

if (-not (Install-Requirements -VenvPythonPath $venvPipPath)) {
    Exit 1
}

if (-not (Ensure-OpenWakeWordModelDir)) {
    # Non-critical, just a warning if failed
}

Ensure-ConfigExists
Remind-AutoHotkeySetup

Write-Host "
Setup script finished.
Next steps:
1. Ensure 'config.json' is created from 'config.template.json' and correctly filled.
2. Ensure AutoHotkey scripts and libraries are in 'src\tools'.
3. Activate the virtual environment: '.\$VenvPath\Scripts\Activate.ps1' (Windows PowerShell)
                                or 'source .\$VenvPath\bin\activate' (bash/zsh/PowerShell Core on Linux/macOS)
4. Run '.\scripts\validate_setup.ps1' to check your setup.
5. Run the main application: '.\$VenvPath\Scripts\python.exe' .\src\main.py
" -ForegroundColor Green 