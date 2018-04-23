FROM microsoft/windowsservercore:1709
LABEL maintainers="Kubernetes Authors"
LABEL description="CSI Driver registrar"

COPY ./driver-registrar.exe c:\driver-registrar.exe
COPY ./driver-registrar.cmd c:\driver-registrar.cmd
ENTRYPOINT ["c:/driver-registrar.exe"]
