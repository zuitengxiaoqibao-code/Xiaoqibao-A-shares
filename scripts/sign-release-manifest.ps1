param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [switch]$Verify
)

$ErrorActionPreference = "Stop"
$Utf8 = [Text.UTF8Encoding]::new($false)
$ResolvedRoot = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$ManifestPath = Join-Path $ResolvedRoot "release-manifest.json"

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Release manifest is missing: $ManifestPath"
}

function Get-ManifestDigest([object]$Manifest) {
    $Manifest.PSObject.Properties.Remove("manifest_signature")
    $Canonical = $Manifest | ConvertTo-Json -Depth 20 -Compress
    $Hasher = [Security.Cryptography.SHA256]::Create()
    try {
        return ($Hasher.ComputeHash($Utf8.GetBytes($Canonical)) | ForEach-Object { $_.ToString("X2") }) -join ""
    } finally {
        $Hasher.Dispose()
    }
}

$ManifestText = [IO.File]::ReadAllText($ManifestPath, $Utf8)
$Manifest = $ManifestText | ConvertFrom-Json
$ExistingSignature = $Manifest.manifest_signature
$Digest = Get-ManifestDigest $Manifest

if ($Verify) {
    if ($null -eq $ExistingSignature) {
        throw "Release manifest signature is missing"
    }
    if ([string]$ExistingSignature.algorithm -ne "SHA256") {
        throw "Release manifest signature algorithm is unsupported"
    }
    if ([string]$ExistingSignature.digest -cne $Digest) {
        throw "Release manifest signature verification failed"
    }
    Write-Host ("Release manifest signature verified: {0}" -f $Digest)
    return
}

$Signature = [ordered]@{
    algorithm = "SHA256"
    digest = $Digest
    signed_at = (Get-Date).ToUniversalTime().ToString("o")
}
$Manifest | Add-Member -MemberType NoteProperty -Name manifest_signature -Value $Signature -Force
$SignedJson = $Manifest | ConvertTo-Json -Depth 20
[IO.File]::WriteAllText($ManifestPath, $SignedJson, $Utf8)
Write-Host ("Release manifest signed: {0}" -f $Digest)
