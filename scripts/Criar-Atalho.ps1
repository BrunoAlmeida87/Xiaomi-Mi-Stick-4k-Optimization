<#
.SYNOPSIS
  Cria atalhos "Xiaomi TV Manager" na Area de Trabalho e no Menu Iniciar.
#>
. "$PSScriptRoot\Comum.ps1"
$shell = New-Object -ComObject WScript.Shell
$criados = @()
foreach ($pasta in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
    if (-not $pasta -or -not (Test-Path $pasta)) { continue }
    try {
        $lnk = $shell.CreateShortcut((Join-Path $pasta 'Xiaomi TV Manager.lnk'))
        $lnk.TargetPath = Join-Path $XtmRoot 'Iniciar-XiaomiTVManager.bat'
        $lnk.WorkingDirectory = $XtmRoot
        $lnk.WindowStyle = 7   # minimizado (o .bat fecha sozinho)
        $lnk.IconLocation = "$env:SystemRoot\System32\imageres.dll,186"
        $lnk.Description = 'Controle e diagnostico do Xiaomi Mi TV Stick'
        $lnk.Save()
        $criados += $lnk.FullName
        Write-XtmLog "Atalho criado: $($lnk.FullName)" OK
    } catch { Write-XtmLog "Nao foi possivel criar atalho em ${pasta}: $($_.Exception.Message)" WARN }
}
$criados
