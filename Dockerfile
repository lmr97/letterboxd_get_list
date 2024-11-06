FROM ubuntu:24.04

RUN apt-get update
RUN apt-get -y install python3.12
RUN apt-get -y install python3-pip
RUN apt-get -y install python3.12-venv

RUN useradd runner
USER runner

WORKDIR /usr/local/runner
COPY ./get_list.py ./
COPY ./LetterboxdFilm.py ./

RUN python3 -m venv .venv
RUN ./.venv/bin/pip install requests==2.32.3
RUN ./.venv/bin/pip install selectolax==0.3.21
