#Requires -Version 5.0
<#
.SYNOPSIS
    IP Radar - All-in-One Installer
#>

# ====== UAC Auto-Elevation ======
try {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) -or ($currentIdentity.Name -like "*SYSTEM*") -or ($env:SystemRoot -like "X:*")
} catch {
    $isAdmin = $true
}

if (-not $isAdmin) {
    try {
        Write-Host "Meminta izin Administrator..." -ForegroundColor Yellow
        $scriptPath = $PSCommandPath
        if (-not $scriptPath) { $scriptPath = $MyInvocation.MyCommand.Path }
        $psExe = (Get-Command powershell.exe -ErrorAction SilentlyContinue).Source
        if (-not $psExe) { $psExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" }
        Start-Process -FilePath $psExe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" -Verb RunAs
        exit
    } catch {
        # Fallthrough if elevation fails
    }
}

# ====== Konfigurasi ======
$SERVER_URL  = "https://netradar.multiapp.my.id"
$API_TOKEN   = "token_script_ipradar_2026"
$INSTALL_DIR = "C:\IPRadar"
$TASK_NAME   = "IPRadar_Collector"

Clear-Host
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   IP RADAR - AUTO INSTALLER (Task Scheduler Mode)  " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installer ini akan:" -ForegroundColor White
Write-Host "  1. Mengambil konfigurasi IP dan NIP dari Anda" -ForegroundColor Gray
Write-Host "  2. Mendaftarkan komputer ini ke server IP Radar" -ForegroundColor Gray
Write-Host "  3. Membuat Task Scheduler agar berjalan otomatis saat login" -ForegroundColor Gray
Write-Host ""

# ====== Input 1: Target IP ======
Write-Host "-------------------------------------------------------" -ForegroundColor DarkGray
$TARGET_IP_BELAKANG = Read-Host "1. Ketik 3 digit IP terakhir komputer ini (kosongkan jika tidak ubah IP)"
$TARGET_IP = ""
if ($TARGET_IP_BELAKANG -ne "") {
    $TARGET_IP = "10.12.13.$TARGET_IP_BELAKANG"
    Write-Host "   -> IP akan diset ke: $TARGET_IP" -ForegroundColor Green
}

# ====== Input 2: NIP Pendek ======
Write-Host ""
$NIP_PENDEK = ""
while ($true) {
    $NIP_PENDEK = Read-Host "2. Ketik NIP Pendek Pegawai [9 Digit] (kosongkan jika tidak ada)"
    if ($NIP_PENDEK -eq "") { break }
    if ($NIP_PENDEK.Length -eq 9 -and $NIP_PENDEK -match '^\d{9}$') { break }
    Write-Host "   [PERINGATAN] NIP Pendek harus tepat 9 digit angka!" -ForegroundColor Red
}

# (Proses Join Domain via script dihapus)

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "Memulai instalasi..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# ====== Buat Folder & Tulis file_1.ps1 ======
if (-not (Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
    Write-Host "[OK] Folder $INSTALL_DIR dibuat." -ForegroundColor Green
}

$PS1_CONTENT = @'
param (
    [string]$ServerUrl,
    [string]$ApiToken,
    [string]$TargetIp = "",
    [string]$SubnetMask = "255.255.255.0",
    [string]$Gateway = "10.12.13.254",
    [string]$Seksi = "",
    [string]$NipPendek = "",
    [int]$PegawaiId = 0
)
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " IP Radar - Device Collector Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($TargetIp -ne "") {
    if (-not $isAdmin) { Write-Host "[WARNING] Jalankan sebagai Admin untuk ubah IP." -ForegroundColor Yellow }
    else {
        Write-Host "[INFO] Setting IP ke $TargetIp ..." -ForegroundColor Green
        $adapter = Get-NetAdapter | Where-Object { $_.Status -eq "Up" -and $_.MacAddress } | Select-Object -First 1
        if ($adapter) {
            $ifIndex = $adapter.ifIndex
            Remove-NetIPAddress -InterfaceIndex $ifIndex -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
            Remove-NetRoute -InterfaceIndex $ifIndex -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
            $prefixLen = (([IPAddress]$SubnetMask).GetAddressBytes() | ForEach-Object { [Convert]::ToString($_, 2).ToCharArray() | Where-Object { $_ -eq '1' } } | Measure-Object).Count
            if ($Gateway -ne "") { New-NetIPAddress -InterfaceIndex $ifIndex -IPAddress $TargetIp -PrefixLength $prefixLen -DefaultGateway $Gateway -ErrorAction Stop | Out-Null }
            else { New-NetIPAddress -InterfaceIndex $ifIndex -IPAddress $TargetIp -PrefixLength $prefixLen -ErrorAction Stop | Out-Null }
            Set-DnsClientServerAddress -InterfaceIndex $ifIndex -ServerAddresses @("10.254.28.31","10.254.28.141","10.254.28.31","10.253.196.3") | Out-Null
            Set-DnsClient -InterfaceIndex $ifIndex -ConnectionSpecificSuffix "intranet.pajak.go.id" -RegisterThisConnectionsAddress $true -UseSuffixWhenRegistering $false -ErrorAction SilentlyContinue | Out-Null
            Set-DnsClientGlobalSetting -SuffixSearchList @("intranet.pajak.go.id","pajak.kemenkeu.go.id","internetex.pajak.go.id") -ErrorAction SilentlyContinue | Out-Null
            Write-Host "[SUCCESS] IP $TargetIp berhasil diset pada adapter $($adapter.Name)" -ForegroundColor Green
            Write-Host "[INFO] Menunggu 15 detik agar koneksi stabil..." -ForegroundColor Yellow
            Start-Sleep -Seconds 15
        } else { Write-Host "[ERROR] Adapter tidak ditemukan." -ForegroundColor Red }
    }
}
Write-Host "[INFO] Mengumpulkan informasi sistem..." -ForegroundColor Green
$hostname = $env:COMPUTERNAME; $macAddress = ""; $ipAddress = ""
$adapters = Get-WmiObject Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true }
if ($adapters) { $p = $adapters | Select-Object -First 1; $macAddress = $p.MACAddress; if ($p.IPAddress -and $p.IPAddress.Count -gt 0) { $ipAddress = $p.IPAddress[0] } }
if ($macAddress -eq "") { Write-Host "[ERROR] Gagal mendapatkan MAC Address." -ForegroundColor Red; exit 1 }
$cpu = Get-WmiObject Win32_Processor | Select-Object -First 1
$cpu_brand = if ($cpu) { $cpu.Manufacturer.Trim() } else { $null }
$cpu_model = if ($cpu) { $cpu.Name.Trim() } else { $null }
$mem = Get-WmiObject Win32_PhysicalMemory; $ram_total = 0; $ram_type_code = 0; $ram_brand = ""
if ($mem) {
    if ($mem -is [array]) { foreach ($m in $mem) { $ram_total += [math]::Round($m.Capacity/1GB,2) }; $ram_type_code = $mem[0].SMBIOSMemoryType; $ram_brand = $mem[0].Manufacturer.Trim() }
    else { $ram_total = [math]::Round($mem.Capacity/1GB,2); $ram_type_code = $mem.SMBIOSMemoryType; $ram_brand = $mem.Manufacturer.Trim() }
}
$ram_type = switch ($ram_type_code) { 20{"DDR"} 21{"DDR2"} 24{"DDR3"} 26{"DDR4"} 34{"DDR5"} 27{"LPDDR3"} 30{"LPDDR4"} 35{"LPDDR5"} default{"Unknown"} }
$disk = Get-WmiObject Win32_DiskDrive | Select-Object -First 1; $storage_capacity = 0; $storage_brand = ""; $storage_type = "HDD/SSD"
if ($disk) {
    $storage_capacity = [math]::Round($disk.Size/1GB,2); $storage_brand = $disk.Model.Trim()
    if ($storage_brand -match "SSD|NVMe") { $storage_type = "SSD/NVMe" } elseif ($storage_brand -match "HDD|Hard") { $storage_type = "HDD" }
    else { try { $phys = Get-PhysicalDisk -ErrorAction SilentlyContinue | Select-Object -First 1; if ($phys) { if ($phys.MediaType -eq 3) { $storage_type = "HDD" } elseif ($phys.MediaType -eq 4) { $storage_type = "SSD" } } } catch {} }
}
$os = Get-WmiObject Win32_OperatingSystem; $os_version = if ($os) { "$($os.Caption.Trim()) $($os.Version)" } else { $null }
$device_type = "PC"; $chassis = Get-WmiObject Win32_SystemEnclosure | Select-Object -First 1
if ($chassis -and $chassis.ChassisTypes) { foreach ($t in $chassis.ChassisTypes) { if ($t -in 8,9,10,11,12,14,18,21,30,31,32) { $device_type = "Laptop"; break } } }
$payload = @{
    hostname=$hostname; mac_address=$macAddress
    ip_address = if ($TargetIp) { $TargetIp } else { $ipAddress }
    device_type=$device_type; seksi=$Seksi; nip_pendek=$NipPendek
    pegawai_id = if ($PegawaiId -gt 0) { $PegawaiId } else { $null }
    specs = @{
        cpu_brand=$cpu_brand; cpu_model=$cpu_model
        ram_total = if ($ram_total -gt 0) { "$ram_total GB" } else { $null }
        ram_type=$ram_type; ram_brand=$ram_brand
        storage_capacity = if ($storage_capacity -gt 0) { "$storage_capacity GB" } else { $null }
        storage_type=$storage_type; storage_brand=$storage_brand; os_version=$os_version
    }
}
$jsonPayload = $payload | ConvertTo-Json -Depth 5
Write-Host "---- Payload ----"; Write-Host $jsonPayload; Write-Host "-----------------"
$endpoint = "$ServerUrl/api/v1/devices/register"
Write-Host "[INFO] Mengirim ke $endpoint ..." -ForegroundColor Green

$headers = @{ "Content-Type"="application/json"; "X-Script-Token"=$ApiToken }
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }

$sent = $false
for ($retry = 1; $retry -le 5; $retry++) {
    try {
        $response = Invoke-RestMethod -Uri $endpoint -Method Post -Headers $headers -Body $jsonPayload -ErrorAction Stop
        Write-Host "[SUCCESS] Perangkat berhasil didaftarkan ke NetRadar!" -ForegroundColor Green
        $sent = $true
        break
    } catch {
        Write-Host "[WARNING] Percobaan ke-$retry gagal mengirim ke server. Menunggu 5 detik..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}
if (-not $sent) { Write-Host "[ERROR] Gagal terhubung ke server setelah 5x percobaan." -ForegroundColor Red }
Write-Host "Done." -ForegroundColor Cyan
'@

$PS1_PATH = "$INSTALL_DIR\file_1.ps1"
Set-Content -Path $PS1_PATH -Value $PS1_CONTENT -Encoding UTF8 -Force
Unblock-File -Path $PS1_PATH -ErrorAction SilentlyContinue
Write-Host "[OK] file_1.ps1 berhasil ditulis ke $INSTALL_DIR" -ForegroundColor Green

# ====== Jalankan Sekali untuk Inisialisasi ======
Write-Host ""; Write-Host "[INFO] Menjalankan script pertama kali..." -ForegroundColor Cyan
$psExePath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
if (-not (Test-Path $psExePath)) { $psExePath = "powershell.exe" }

$psArgList = [System.Collections.Generic.List[string]]@("-NoProfile","-ExecutionPolicy","Bypass","-File","$PS1_PATH","-ServerUrl","$SERVER_URL","-ApiToken","$API_TOKEN","-NipPendek","$NIP_PENDEK")
if ($TARGET_IP -ne "") { $psArgList.Add("-TargetIp"); $psArgList.Add("$TARGET_IP") }
Start-Process -FilePath $psExePath -ArgumentList $psArgList -Wait -NoNewWindow
Write-Host "[OK] Eksekusi awal selesai." -ForegroundColor Green

# ====== Buat Task Scheduler ======
Write-Host ""; Write-Host "[INFO] Mendaftarkan Scheduled Task..." -ForegroundColor Cyan
$taskArgs = "-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$PS1_PATH`" -ServerUrl `"$SERVER_URL`" -ApiToken `"$API_TOKEN`" -NipPendek `"$NIP_PENDEK`""
$action = New-ScheduledTaskAction -Execute $psExePath -Argument $taskArgs
$trigger1 = New-ScheduledTaskTrigger -AtLogOn
$trigger2 = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0
try {
    Register-ScheduledTask -TaskName $TASK_NAME -Action $action -Trigger @($trigger1, $trigger2) -Settings $settings -User "SYSTEM" -RunLevel Highest -Force | Out-Null
    Write-Host "[OK] Task Scheduler '$TASK_NAME' berhasil dibuat!" -ForegroundColor Green
} catch { Write-Host "[ERROR] Gagal membuat Task Scheduler: $_" -ForegroundColor Red }

# ====== Selesai ======
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " INSTALASI SELESAI!" -ForegroundColor Green
Write-Host " Komputer akan otomatis melaporkan status ke IP Radar" -ForegroundColor White
Write-Host " setiap kali user login." -ForegroundColor White
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Tekan Enter untuk menutup"
