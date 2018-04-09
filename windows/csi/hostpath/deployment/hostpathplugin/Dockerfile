FROM microsoft/windowsservercore:1709
LABEL maintainers="Kubernetes Authors"
LABEL description="HostPath Driver"

SHELL ["cmd"]

COPY ./hostpathplugin.exe c:\hostpathplugin.exe
ENTRYPOINT ["c:\hostpathplugin.exe"]
