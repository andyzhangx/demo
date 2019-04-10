$global:AzureHostname = "34763k8s9010"
$global:MasterIP = "10.240.255.5"
$global:KubeDnsServiceIp = "10.0.0.10"
$global:MasterSubnet = "10.240.0.0/16"
$global:KubeClusterCIDR = "10.244.0.0/16"
$global:KubeServiceCIDR = "10.0.0.0/16"
$global:KubeBinariesVersion = "1.7.9"
$global:CNIPath = "c:\k\cni"
$global:NetworkMode = "L2Bridge"
$global:CNIConfig = "c:\k\cni\config\$global:NetworkMode.conf"
$global:HNSModule = "c:\k\hns.psm1"

function
Get-DefaultGateway($CIDR)
{
    return $CIDR.substring(0,$CIDR.lastIndexOf(".")) + ".1"
}

function
Get-PodCIDR()
{
    $podCIDR = c:\k\kubectl.exe --kubeconfig=c:\k\config get nodes/$($global:AzureHostname.ToLower()) -o custom-columns=podCidr:.spec.podCIDR --no-headers
    return $podCIDR
}

function
Test-PodCIDR($podCIDR)
{
    return $podCIDR.length -gt 0
}

function
Update-CNIConfig($podCIDR, $masterSubnetGW)
{
    $jsonSampleConfig =
"{
  ""cniVersion"": ""0.2.0"",
  ""name"": ""<NetworkMode>"",
  ""type"": ""wincni.exe"",
  ""master"": ""Ethernet"",
  ""capabilities"": { ""portMappings"": true },
  ""ipam"": {
     ""environment"": ""azure"",
     ""subnet"":""<PODCIDR>"",
     ""routes"": [{
        ""GW"":""<PODGW>""
     }]
  },
  ""dns"" : {
    ""Nameservers"" : [ ""<NameServers>"" ]
  },
  ""AdditionalArgs"" : [
    {
      ""Name"" : ""EndpointPolicy"", ""Value"" : { ""Type"" : ""OutBoundNAT"", ""ExceptionList"": [ ""<ClusterCIDR>"", ""<MgmtSubnet>"" ] }
    },
    {
      ""Name"" : ""EndpointPolicy"", ""Value"" : { ""Type"" : ""ROUTE"", ""DestinationPrefix"": ""<ServiceCIDR>"", ""NeedEncap"" : true }
    }
  ]
}"

    $configJson = ConvertFrom-Json $jsonSampleConfig
    $configJson.name = $global:NetworkMode.ToLower()
    $configJson.ipam.subnet=$podCIDR
    $configJson.ipam.routes[0].GW = $masterSubnetGW
    $configJson.dns.Nameservers[0] = $global:KubeDnsServiceIp

    $configJson.AdditionalArgs[0].Value.ExceptionList[0] = $global:KubeClusterCIDR
    $configJson.AdditionalArgs[0].Value.ExceptionList[1] = $global:MasterSubnet
    $configJson.AdditionalArgs[1].Value.DestinationPrefix  = $global:KubeServiceCIDR

    if (Test-Path $global:CNIConfig)
    {
        Clear-Content -Path $global:CNIConfig
    }

    Write-Host "Generated CNI Config [$configJson]"

    Add-Content -Path $global:CNIConfig -Value (ConvertTo-Json $configJson -Depth 20)
}

try
{
    $masterSubnetGW = Get-DefaultGateway $global:MasterSubnet
    $podCIDR=Get-PodCIDR
    $podCidrDiscovered=Test-PodCIDR($podCIDR)

    # if the podCIDR has not yet been assigned to this node, start the kubelet process to get the podCIDR, and then promptly kill it.
    if (-not $podCidrDiscovered)
    {
        $argList = @("--hostname-override=$global:AzureHostname","--pod-infra-container-image=kubletwin/pause","--resolv-conf=""""","--kubeconfig=c:\k\config","--cloud-provider=azure","--cloud-config=c:\k\azure.json","--api-servers=https://${global:MasterIP}:443")

        $process = Start-Process -FilePath c:\k\kubelet.exe -PassThru -ArgumentList $argList

        # run kubelet until podCidr is discovered
        Write-Host "waiting to discover pod CIDR"
        while (-not $podCidrDiscovered)
        {
            Write-Host "Sleeping for 10s, and then waiting to discover pod CIDR"
            Start-Sleep 10

            $podCIDR=Get-PodCIDR
            $podCidrDiscovered=Test-PodCIDR($podCIDR)
        }

        # stop the kubelet process now that we have our CIDR, discard the process output
        $process | Stop-Process | Out-Null
    }

    # Turn off Firewall to enable pods to talk to service endpoints. (Kubelet should eventually do this)
    netsh advfirewall set allprofiles state off

    # startup the service
    $hnsNetwork = Get-HnsNetwork | ? Name -EQ $global:NetworkMode.ToLower()

    if (!$hnsNetwork)
    {
        Write-Host "No HNS network found, creating a new one..."
        ipmo $global:HNSModule

        $hnsNetwork = New-HNSNetwork -Type $global:NetworkMode -AddressPrefix $podCIDR -Gateway $masterSubnetGW -Name $global:NetworkMode.ToLower() -Verbose
    }

    Start-Sleep 10
    # Add route to all other POD networks
    Update-CNIConfig $podCIDR $masterSubnetGW

    c:\k\kubelet.exe --hostname-override=$global:AzureHostname --pod-infra-container-image=kubletwin/pause --resolv-conf="" --allow-privileged=true --enable-debugging-handlers --cluster-dns=$global:KubeDnsServiceIp --cluster-domain=cluster.local  --kubeconfig=c:\k\config --hairpin-mode=promiscuous-bridge --v=2 --azure-container-registry-config=c:\k\azure.json --runtime-request-timeout=10m  --cloud-provider=azure --cloud-config=c:\k\azure.json --api-servers=https://${global:MasterIP}:443 --network-plugin=cni --cni-bin-dir=$global:CNIPath --cni-conf-dir $global:CNIPath\config --image-pull-progress-deadline=20m --cgroups-per-qos=false --enforce-node-allocatable=""
}
catch
{
    Write-Error $_
}
