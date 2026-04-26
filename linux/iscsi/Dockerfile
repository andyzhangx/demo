FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends tgt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 3260

ENTRYPOINT ["/entrypoint.sh"]
