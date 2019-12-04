
FROM alpine

RUN apk add bash python3 gcc python3-dev musl-dev libffi-dev libressl-dev 
RUN pip3 install --upgrade pip
COPY bin/requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

COPY bin/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

