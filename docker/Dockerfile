FROM python:3.6
MAINTAINER Zeng Ke <superisaac.ke@gmail.com>

RUN apt-get update -yy & apt-get upgrade -yy

RUN pip3 install git+https://github.com/haobtc/bbox.git

EXPOSE 30000

WORKDIR /root/

ADD run.sh run.sh
ADD get_local_ip.py get_local_ip.py

ENTRYPOINT ["/root/run.sh"]
