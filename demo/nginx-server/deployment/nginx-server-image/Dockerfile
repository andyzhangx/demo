FROM nginx
ADD ./default.conf /etc/nginx/conf.d/default.conf
ADD ./gitclone.sh /mnt/gitclone.sh

RUN apt-get update && apt-get install git -y
