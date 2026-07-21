FROM python:3.13-slim

#
# Update system dependencies; install git for WRT installation
#
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get dist-upgrade -y \
 && apt-get install git -y

WORKDIR /app

COPY ./requirements.txt ./

RUN pip install -r requirements.txt

#
# Remove git; clean up
#
RUN apt-get purge git -y \
 && apt-get clean \
 && apt autoremove -y  \
 && rm -rf /var/lib/apt/lists/*

COPY ./main.py ./

RUN mkdir /app/workdir /app/workdir/figures

ENTRYPOINT [ "python", "/app/main.py" ]