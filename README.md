#MilkMachine

QGIS Python Plugin for creating KML (keyhole markup language) files from GPS data. The code and components developed to support the 250 Miles Crossing Philadelphia project
http://www.250miles.net/. Milk Machine will accept raw gps data in .csv format and allows for creation of KML tours, placemarks, models, audio attachment,
spatial smoothing/filtering, and time editing. Once editing is complete, files can be exported to .kml or .kmz. An intermediate shapefile (.shp) is 
produced that will store the coded attribute information. No cow's milk (or milk of any kind) is produced.

## Using MilkMachine

### Installation
- The plugin can be copy/pasted from /src/MilkMachine directly into the QGIS plugin directory.
- "Install" the plugin using the QGIS Desktop plugin manager (Plugins > Manage and Install Plugins...). MilkMachine should show up in the "Installed"
tab. Make sure that it is checked. See http://docs.qgis.org/1.8/en/docs/user_manual/plugins/plugins.html for full documentation.

### Install Directories
Windows: C:\Users\<username>\.qgis2\python\plugins
Mac: ~\.qgis2\python\plugins
Ubuntu Linux: \user\lib\qgis\plugins

### Create a KML Placemarks

### Create a KML Tour

## Dependencies

- QGIS 2.4, 2.6, 2.10 (never tested on 2.8, might work)
- gpxpy, mutagen, and simplekml Python packages are all distributed with MilkMachine to avoid user installation.
- SciPy may need to be installed manually.

## Issues
Please submit comments, bugs, etc. on the issues page https://github.com/EdFarrell/MilkMachine/issues

## Credits
Funding and/or Resources can from these sources;
University City Science Center
Wexford Science + Technology
Philadelphia Redevelopment Authority
Drexel University



