# Start from official Python docker image
# FROM python:3.8
FROM python:3.7-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True
ENV APP_HOME /home
WORKDIR $APP_HOME

# Create required directories and set workdir.
RUN mkdir -p /home/requirements /home/scripts /home/templates /home/config /home/data /home/internal
WORKDIR /home/scripts

# Install all required packages. Requirements file contains the necessary python
# packages.
COPY ./inputData/requirements/ /home/requirements/
RUN pip install -r /home/requirements/requirements.txt

# Copy files with scripts and config data, set permissions.
COPY ./inputData/scripts/ /home/scripts/
RUN chmod +x /home/scripts/app.py
COPY ./inputData/templates/ /home/templates/
COPY ./inputData/config/ /home/config/

ENV PORT 8000

# # Define the default command to run when starting the container.
# # This command keeps the container running as because the websocket is being
# # kept open.
ENTRYPOINT [ "nohup", "python", "/home/scripts/start.py", "&" ]

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 --chdir /home/scripts app:app
