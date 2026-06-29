param(
  [string]$Path = ".env.local"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path)) {
  throw ".env.local was not found: $Path"
}

Get-Content -LiteralPath $Path | ForEach-Object {
  $line = $_.Trim()
  if ($line -eq "" -or $line.StartsWith("#")) {
    return
  }

  if ($line.StartsWith("export ")) {
    $line = $line.Substring(7).Trim()
  }

  $parts = $line.Split("=", 2)
  if ($parts.Count -ne 2 -or $parts[0].Trim() -eq "") {
    return
  }

  $name = $parts[0].Trim()
  $value = $parts[1].Trim()
  if (($value.StartsWith("'") -and $value.EndsWith("'")) -or ($value.StartsWith('"') -and $value.EndsWith('"'))) {
    $value = $value.Substring(1, $value.Length - 2)
  }

  [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

Write-Host "Loaded environment variables from $Path"
