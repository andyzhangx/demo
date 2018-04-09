FROM microsoft/windowsservercore:1709
LABEL maintainers="Kubernetes Authors"
LABEL description="CSI Driver registrar"

SHELL ["cmd"]

COPY ./driver-registrar.exe c:\driver-registrar.exe
ENTRYPOINT ["c:\driver-registrar.exe"]
