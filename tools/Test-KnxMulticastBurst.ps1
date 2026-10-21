param(
    [Parameter(Mandatory = $true)][ValidateRange(1, 6)][int]$Series,
    [Parameter(Mandatory = $true)][ValidateSet(100, 10, 2)][int]$IntervalMs,
    [switch]$RefreshKnx
)

$localAddress = [Net.IPAddress]::Parse('192.0.2.123')
$groupAddress = [Net.IPAddress]::Parse('224.0.23.12')
$remote = [Net.IPEndPoint]::new($groupAddress, 3671)
$udp = [Net.Sockets.UdpClient]::new([Net.Sockets.AddressFamily]::InterNetwork)
$udp.Client.Bind([Net.IPEndPoint]::new($localAddress, 0))
$udp.Client.SetSocketOption(
    [Net.Sockets.SocketOptionLevel]::IP,
    [Net.Sockets.SocketOptionName]::MulticastInterface,
    $localAddress.GetAddressBytes())
$udp.Client.SetSocketOption(
    [Net.Sockets.SocketOptionLevel]::IP,
    [Net.Sockets.SocketOptionName]::MulticastTimeToLive,
    1)
$udp.Client.SetSocketOption(
    [Net.Sockets.SocketOptionLevel]::IP,
    [Net.Sockets.SocketOptionName]::MulticastLoopback,
    $true)
$localPort = $udp.Client.LocalEndPoint.Port

$refreshProcess = $null
if ($RefreshKnx) {
    $refreshProcess = Start-Process -FilePath 'curl.exe' `
        -ArgumentList '--fail', '--silent', '--output', 'NUL', 'http://192.0.2.156/knx' `
        -WindowStyle Hidden -PassThru
    Start-Sleep -Milliseconds 50
}

$clock = [Diagnostics.Stopwatch]::StartNew()
$sent = [Collections.Generic.List[object]]::new()
for ($sequence = 0; $sequence -lt 20; $sequence++) {
    $payload = [byte[]](0x4B, 0x58, 0x44, 0x47, 1, $Series, $sequence, 20)
    $count = $udp.Send($payload, $payload.Length, $remote)
    $sent.Add([pscustomobject]@{ sequence = $sequence; elapsed_us = [long]($clock.Elapsed.TotalMilliseconds * 1000); bytes = $count })
    if ($sequence -lt 19) {
        $deadline = [long]($clock.Elapsed.TotalMilliseconds * 1000) + ($IntervalMs * 1000)
        while ([long]($clock.Elapsed.TotalMilliseconds * 1000) -lt $deadline) {
            [Threading.Thread]::SpinWait(100)
        }
    }
}
$udp.Dispose()

if ($null -ne $refreshProcess) {
    $refreshProcess.WaitForExit(30000) | Out-Null
}

[pscustomobject]@{
    series = $Series
    interval_ms = $IntervalMs
    web_refresh = [bool]$RefreshKnx
    local_address = $localAddress.ToString()
    local_port = $localPort
    multicast_interface = $localAddress.ToString()
    multicast_ttl = 1
    sent_count = $sent.Count
    sent = $sent
} | ConvertTo-Json -Depth 4
