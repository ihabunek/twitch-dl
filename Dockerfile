FROM python:alpine3.7
RUN apk --no-cache add ffmpeg
COPY . /twitch-dl
WORKDIR /twitch-dl
RUN python setup.py install
RUN mkdir /downloads
WORKDIR /downloads
ENTRYPOINT [ "twitch-dl" ]
