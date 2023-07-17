FROM python:3.11.3-alpine3.18

RUN pip install watchdog

RUN pip install pipenv

COPY Pipfile .

COPY Pipfile.lock .   

RUN pipenv requirements > requirements.txt

RUN pip install -r requirements.txt

RUN rm -rf Pipfile Pipfile.lock requirements.txt

COPY . /app

WORKDIR /app

CMD ["sh", "-c", "watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- python main.py"]