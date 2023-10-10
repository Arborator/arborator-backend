# python base image
FROM python:3.10

WORKDIR /app

COPY requirements.txt ./

# Installing the requirements
RUN pip install -r requirements.txt

COPY . .

# Command to run in the dev mode
CMD ["flask", "run", "--host=0.0.0.0", "--cert=adhoc"]