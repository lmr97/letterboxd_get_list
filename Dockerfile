# largely just copied from Python's official Docker image page
FROM python:3.13

COPY requirements.txt  ./
COPY get_list.py       ./
COPY LetterboxdFilm.py ./
COPY healthcheck.py    ./

RUN pip install --no-cache-dir -r requirements.txt
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD [ "python3", "healthcheck.py" ]
CMD [ "python3", "./get_list.py" ]