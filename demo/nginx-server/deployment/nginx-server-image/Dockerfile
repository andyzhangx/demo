FROM nginx
ADD ./default.conf /etc/nginx/conf.d/default.conf
ADD ./gitclone.sh /mnt/gitclone.sh
ADD ./genfiles.sh /mnt/genfiles.sh

RUN apt-get update && apt-get install git -y
