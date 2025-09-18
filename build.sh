#!/bin/bash

# Install ODBC Driver
apt-get update
apt-get install -y curl gnupg
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17
apt-get install -y unixodbc-dev

# Install Python dependencies
pip install -r requirements.txt
