#Requires -Version 5.1
<#
.SYNOPSIS
    Validates the Home Assistant Voice Control MVP environment setup.
.DESCRIPTION
    This script performs the following checks:
    1. Ensures it's running from an activated Python virtual environment (basic check).
    2. Checks if config.json exists and can be loaded by calling scripts/check_config.py.
    3. Attempts to import all required Python packages by calling scripts/check_deps.py.
    4. Validates paths specified in config.json (AutoHotkey exe, OpenWakeWord models, AHK scripts dir).
    5. Checks for the presence of music_controller.ahk and its UIAutomation libraries.
.NOTES
    Run this script from the project root directory AFTER running setup.ps1 and activating the virtual environment.
    Example: .\scripts\validate_setup.ps1
#>

function Test-VirtualEnvironment {
    $pythonPath = (Get-Command python).Source
    if ($pythonPath -notlike "*\.venv\*" -and $pythonPath -notlike "*\venv\*" ) {
        Write-Warning "Python executable does not appear to be from a virtual environment ($($pythonPath))."
        Write-Warning "Please activate the virtual environment first: '.\.venv\Scripts\Activate.ps1' or similar."
    }
    Write-Host "Python executable: $($pythonPath)" -ForegroundColor Cyan
    return $true # Soft check, does not fail validation
}

function Test-ConfigLoadableWithPythonScript {
    Write-Host "Attempting to load configuration via scripts/check_config.py..." -ForegroundColor Cyan
    $scriptPath = ".\scripts\check_config.py"
    if (-not (Test-Path $scriptPath)) {
        Write-Error "Helper script not found: $($scriptPath)"
        return $false
    }
    try {
        $result = python $scriptPath 2>&1 # Capture both stdout and stderr
        if ($LASTEXITCODE -eq 0 -and $result -match "OK_CONFIG") {
            Write-Host "config.json loaded and validated successfully by check_config.py." -ForegroundColor Green
            return $true
        } else {
            Write-Error "Failed to load or validate config.json using check_config.py: $($result)"
            return $false
        }
    } catch {
        Write-Error "Critical error running python $($scriptPath): $($_.Exception.Message)"
        return $false
    }
}

function Test-PythonDependenciesWithPythonScript {
    Write-Host "Checking Python dependencies via scripts/check_deps.py..." -ForegroundColor Cyan
    $scriptPath = ".\scripts\check_deps.py"
    if (-not (Test-Path $scriptPath)) {
        Write-Error "Helper script not found: $($scriptPath)"
        return $false
    }
    try {
        $result = python $scriptPath 2>&1 # Capture both stdout and stderr
        if ($LASTEXITCODE -eq 0 -and $result -match "OK_DEPS") {
            Write-Host "All Python dependencies imported successfully by check_deps.py." -ForegroundColor Green
            return $true
        } else {
            Write-Error "Failed to import Python dependencies using check_deps.py: $($result)"
            return $false
        }
    } catch {
        Write-Error "Critical error running python $($scriptPath): $($_.Exception.Message)"
        return $false
    }
}

function Get-ConfigValueFromJson {
    param (
        [string]$JsonPath,
        [string]$Key
    )
    try {
        $jsonContent = Get-Content -Path $JsonPath -Raw | ConvertFrom-Json
        $currentObject = $jsonContent
        $Key.Split('.') | ForEach-Object {
            $propName = $_.ToString()
            if ($null -eq $currentObject -or -not $currentObject.PSObject.Properties[$propName]) {
                $currentObject = $null
                return # Exit ForEach-Object early if property not found
            }
            $currentObject = $currentObject.$($propName)
        }
        return $currentObject
    } catch {
        Write-Warning "Could not read/parse $($JsonPath) for key '$($Key)': $($_.Exception.Message)"
        return $null
    }
}

function Test-PathsFromConfig {
    Write-Host "Checking paths from config.json..." -ForegroundColor Cyan
    $configPath = ".\config.json"
    if (-not (Test-Path $configPath)) {
        Write-Error "$($configPath) not found. Cannot check paths."
        return $false
    }
    $allPathsOk = $true

    $ahkExe = Get-ConfigValueFromJson -JsonPath $configPath -Key "paths.autohotkey_exe"
    Write-Host "  AutoHotkey Executable ('paths.autohotkey_exe'): $($ahkExe)\" -NoNewline
    if ($null -ne $ahkExe -and (Test-Path $ahkExe -PathType Leaf)) {
        Write-Host " - Found" -ForegroundColor Green
    } else {
        Write-Host " - NOT FOUND or not a file ($($ahkExe))" -ForegroundColor Red
        $allPathsOk = $false
    }

    $owwModelsDir = Get-ConfigValueFromJson -JsonPath $configPath -Key "paths.openwakeword_models_dir"
    Write-Host "  OpenWakeWord Models Dir ('paths.openwakeword_models_dir'): $($owwModelsDir)\" -NoNewline
    if ($null -ne $owwModelsDir -and (Test-Path $owwModelsDir -PathType Container)) {
        Write-Host " - Found" -ForegroundColor Green
    } else {
        Write-Host " - NOT FOUND or not a directory ($($owwModelsDir))" -ForegroundColor Red
        $allPathsOk = $false
    }
    
    $ahkScriptsDir = Get-ConfigValueFromJson -JsonPath $configPath -Key "paths.autohotkey_scripts_dir"
    Write-Host "  AutoHotkey Scripts Dir ('paths.autohotkey_scripts_dir'): $($ahkScriptsDir)\" -NoNewline
    if ($null -ne $ahkScriptsDir -and (Test-Path $ahkScriptsDir -PathType Container)) {
        Write-Host " - Found" -ForegroundColor Green
    } else {
        Write-Host " - NOT FOUND or not a directory ($($ahkScriptsDir))" -ForegroundColor Red
        $allPathsOk = $false
    }
    return $allPathsOk
}

function Test-AhkFilesPresence {
    Write-Host "Checking for AutoHotkey script files..." -ForegroundColor Cyan
    $ahkScriptsConfigDir = Get-ConfigValueFromJson -JsonPath ".\config.json" -Key "paths.autohotkey_scripts_dir"
    $ahkScriptsBasePath = if ($null -ne $ahkScriptsConfigDir) { (Resolve-Path $ahkScriptsConfigDir -ErrorAction SilentlyContinue).Path } else { ".\src\tools" }
    if ($null -eq $ahkScriptsBasePath) { $ahkScriptsBasePath = ".\src\tools" } # Fallback if Resolve-Path failed

    Write-Host "  Using AutoHotkey scripts base path: $($ahkScriptsBasePath)" -ForegroundColor DarkGray
    $allFilesOk = $true

    $musicControllerPath = Join-Path $ahkScriptsBasePath "music_controller.ahk"
    Write-Host "  Music Controller Script: $($musicControllerPath)\" -NoNewline
    if (Test-Path $musicControllerPath -PathType Leaf) {
        Write-Host " - Found" -ForegroundColor Green
    } else {
        Write-Host " - NOT FOUND or not a file" -ForegroundColor Red
        $allFilesOk = $false
    }

    $uiaLibDir = Join-Path $ahkScriptsBasePath "Lib"
    Write-Host "  UIAutomation Library Dir: $($uiaLibDir)\" -NoNewline
    if (Test-Path $uiaLibDir -PathType Container) {
        Write-Host " - Found" -ForegroundColor Green
        $uiaLibPath = Join-Path $uiaLibDir "UIA.ahk"
        Write-Host "    Checking for UIA.ahk: $($uiaLibPath)\" -NoNewline
        if (Test-Path $uiaLibPath -PathType Leaf) { Write-Host " - Found" -ForegroundColor Green } else { Write-Host " - NOT FOUND" -ForegroundColor Red; $allFilesOk = $false }
        
        $uiaBrowserLibPath = Join-Path $uiaLibDir "UIA_Browser.ahk"
        Write-Host "    Checking for UIA_Browser.ahk: $($uiaBrowserLibPath)\" -NoNewline
        if (Test-Path $uiaBrowserLibPath -PathType Leaf) { Write-Host " - Found" -ForegroundColor Green } else { Write-Host " - NOT FOUND" -ForegroundColor Red; $allFilesOk = $false }
    } else {
        Write-Host " - Lib directory NOT FOUND" -ForegroundColor Red
        $allFilesOk = $false
    }
    return $allFilesOk
}

# --- Main Script Execution ---
Write-Host "Starting Home Assistant Voice Control MVP Setup Validation..." -ForegroundColor Cyan
$overallSuccess = $true

Test-VirtualEnvironment
if (-not (Test-ConfigLoadableWithPythonScript)) { $overallSuccess = $false }
if (-not (Test-PythonDependenciesWithPythonScript)) { $overallSuccess = $false }
if (-not (Test-PathsFromConfig)) { $overallSuccess = $false }
if (-not (Test-AhkFilesPresence)) { $overallSuccess = $false }

Write-Host "-------------------------------------------------" -ForegroundColor Cyan
if ($overallSuccess) {
    Write-Host "Validation finished. All checks passed! Your environment seems ready." -ForegroundColor Green
} else {
    Write-Error "Validation finished. Some checks failed. Please review the errors above and ensure all setup steps were completed correctly."
    Exit 1
} 