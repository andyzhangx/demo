FROM microsoft/windowsservercore:1709
LABEL maintainers="Kubernetes Authors"
LABEL description="HostPath Driver"

COPY ./hostpathplugin.exe c:\hostpathplugin.exe
COPY ./hostpathplugin.cmd c:\hostpathplugin.cmd
ENTRYPOINT ["c:\hostpathplugin.cmd"]
