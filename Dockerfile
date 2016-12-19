# image with base requirements
FROM debian:jessie
MAINTAINER Peter Robinett <peter@bubblefoundry.com>

# install QGIS apt-get repository
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-key 073D307A618E5811
RUN echo "deb     http://qgis.org/debian jessie main" >> /etc/apt/sources.list
RUN echo "deb-src http://qgis.org/debian jessie main" >> /etc/apt/sources.list
RUN apt-get -y update

# get latest QGIS
RUN apt-get --assume-yes install qgis python-qgis qgis-plugin-grass

# NumPy, SciPy, and QtSql
RUN apt-get --assume-yes install python-qt4-sql python-numpy python-scipy

# Python debugging
RUN apt-get --assume-yes install gdb python-dbg

# mmdev user
RUN adduser --uid 1000 --disabled-password --gecos '' mmdev
USER mmdev
