param(
    [Parameter(Mandatory = $true)]
    [string]$Text,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$voice = New-Object -ComObject SAPI.SpVoice
$englishVoice = $voice.GetVoices() |
    Where-Object { $_.GetDescription() -like "*English*" } |
    Select-Object -First 1

if ($null -eq $englishVoice) {
    throw "No English SAPI voice is installed."
}

$voice.Voice = $englishVoice
$voice.Rate = -1
$voice.Volume = 100

$stream = New-Object -ComObject SAPI.SpFileStream
$stream.Open($OutputPath, 3, $false)
$voice.AudioOutputStream = $stream

try {
    [void]$voice.Speak($Text)
}
finally {
    $stream.Close()
}
