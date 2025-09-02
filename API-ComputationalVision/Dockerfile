# Use an official Python runtime as a parent image
FROM python:3.13-slim

RUN apt-get update \
  && apt-get install -y  \
       ca-certificates curl gnupg jq \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/ms.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/ms.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/mssql-release.list \
  && apt-get update \
  && ACCEPT_EULA=Y apt-get install -y \
    libgssapi-krb5-2 msodbcsql18 unixodbc unixodbc-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ENV DEPLOYMENT_TARGET=Docker
ENV TZ=UTC
ENV HEALTHCHECK_BASEURL=http://localhost:80
ENV HEALTHCHECK_PATH=/Health

# Set the working directory in the container
WORKDIR /App

# Copy the current directory contents into the container at /app
COPY run.sh /App/
#COPY requirements.txt /app/

# Make the entrypoint script executable
RUN chmod +x /App/run.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
 CMD sh -c 'curl -fs http://localhost:80/Health | jq -r ".status" | grep -qi "^Healthy$"'

# Run the entrypoint script
ENTRYPOINT ["/App/run.sh"]
