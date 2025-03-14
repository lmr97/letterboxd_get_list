# largely just copied from Python's official Docker image page
FROM python:3.13

WORKDIR /usr/src/app

COPY requirements.txt  ./
COPY get_list.py       ./
COPY LetterboxdFilm.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "./get_list.py" ]