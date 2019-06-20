FROM balenalib/raspberry-pi-python:build

ENV container docker
RUN apt-get update && apt-get install -y --no-install-recommends \
		systemd \
	&& rm -rf /var/lib/apt/lists/*

# We never want these to run in a container
# Feel free to edit the list but this is the one we used
RUN systemctl mask \
    dev-hugepages.mount \
    sys-fs-fuse-connections.mount \
    sys-kernel-config.mount \

    display-manager.service \
    getty@.service \
    systemd-logind.service \
    systemd-remount-fs.service \

    getty.target \
    graphical.target

COPY entry.sh /usr/bin/entry.sh
COPY resin.service /etc/systemd/system/resin.service

RUN systemctl enable /etc/systemd/system/resin.service

STOPSIGNAL 37
VOLUME ["/sys/fs/cgroup"]
ENTRYPOINT ["/usr/bin/entry.sh"]


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

CMD ["python","main.py"]
