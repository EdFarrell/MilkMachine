# image with base requirements
FROM kartoza/qgis-desktop

# NumPy, SciPy, and QtSql
RUN apt-get update
RUN apt-get --assume-yes install python-qt4-sql python-numpy python-scipy

# add QGIS to the Python path
ENV PYTHONPATH /usr/share/qgis/python

# mmdev user
RUN adduser --uid 1000 --disabled-password --gecos '' mmdev
USER mmdev
