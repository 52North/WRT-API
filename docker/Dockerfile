FROM python:3.13

#
# Update system dependencies
#
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get dist-upgrade -y \
 && apt-get clean \
 && apt autoremove -y  \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt ./

RUN pip install -r requirements.txt

COPY ./main.py ./

RUN mkdir /app/workdir /app/workdir/figures

ENTRYPOINT [ "python", "/app/main.py" ]