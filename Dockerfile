# Set base image (host OS)
FROM python:3.12.7

# By default, listen on port 5000
EXPOSE 5000/tcp

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .
COPY 2399_secret.json .

# Install any dependencies
RUN pip install -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY student-app/ /app/student-app/

# Specify the command to run on container start
CMD [ "python", "./student-app/app.py" ]