FROM balenalib/raspberry-pi-python:build

WORKDIR /usr/src/app

COPY ./requirements.txt /requirements.txt

# pip install python deps from requirements.txt on the resin.io build server
#RUN sudo apt-get update -y

#RUN apt-get upgrade -y

#RUN python -m pip install --upgrade pip

RUN pip install -r /requirements.txt

RUN pip install --upgrade pip setuptools

RUN sudo python -m easy_install mysql-connector

RUN sudo apt-get --only-upgrade -y install openssl

# This will copy all files in our root to the working  directory in the container
COPY . ./

# switch on systemd init system in container
#ENV INITSYSTEM on

CMD ["/bin/sh","/usr/src/app/entry.sh"]
