#MilkMachine

QGIS Python Plugin for creating KML (keyhole markup language) files from GPS data. The code and components developed to support the 250 Miles Crossing Philadelphia project
http://www.250miles.net/. Milk Machine will accept raw gps data in .csv format and allows for creation of KML tours, placemarks, models, audio attachment,
spatial smoothing/filtering, and time editing. Once editing is complete, files can be exported to .kml or .kmz. An intermediate shapefile (.shp) is 
produced that will store the coded attribute information. No cow's milk (or milk of any kind) is produced.

![MM Image](https://github.com/EdFarrell/MilkMachine/blob/master/dist/images/mm_image1.PNG "image 1")

## Using MilkMachine

### Installation
- The plugin can be copy/pasted from /src/MilkMachine directly into the QGIS plugin directory, or installed from the QGIS Plugin Repository.
- "Install" the plugin using the QGIS Desktop plugin manager (Plugins > Manage and Install Plugins...). MilkMachine should show up in the "Installed"
tab. Make sure that it is checked. See http://docs.qgis.org/1.8/en/docs/user_manual/plugins/plugins.html for full documentation.
- MilkMachine is currently an "experimental" plugin, so make sure that options is checked in the plugin manager (in Settings...).

#### Install Directories (don't worry about this is you install from the Repository)
- Windows: C:\Users\<username>\.qgis2\python\plugins
- Mac: ~\.qgis2\python\plugins
- Ubuntu Linux: \user\.qgis2\python\plugins

### Import a .csv file
All raw .csv GPS files need to have these 5 fields; "date", "time", "x", "y", "altitude"
- **date**: Date of the location. Can be in these formats; MM/DD/YYYY, DD/MM/YYYY, YYYY/MM/DD
- **time**: Time of the location. Must be HH:MM:SS, or HH:MM:SS mmmmmm. mmmmmm is microseconds. See the Python datetime library for full spec (https://docs.python.org/2/library/datetime.html)
- **x**: Longitude. numeric, geographic coordinates (WGS84)
- **y**: Latitude. numeric, geographic coordinates (WGS84)
- **altitude**: Elevation in reference to sea level (could also be to "sea floor"). numeric, meters preferred.

1. Click the "Import GPS" button (see image above) and browse to a raw gps file in .csv format
2. Once the file is loaded, choose a date format and click the "Draw Track" button.
3. The file will draw a point layer and a line layer on the QGIS map canvas. An ESRI shapefile (.shp) will be created in the source directory for your .csv file. This shapefile will be edited to produce the .kml file


### Create a KML Placemarks

### Create a KML Tour

## Dependencies

- QGIS 2.4, 2.6, 2.8
- Python```python gpxpy, mutagen, simplekml``` packages are all distributed with MilkMachine to avoid user installation.
- Python SciPy may need to be installed manually. See http://www.scipy.org/install.html for platform specific instructions. 

## Issues
Help pages will be updated here and at a future project page. Help, is provided for each input in MilkMachine by hovering over the input.
Please submit comments, bugs, etc. on the issues page https://github.com/EdFarrell/MilkMachine/issues

## Credits
Funding and/or Resources can from these sources;
University City Science Center
Wexford Science + Technology
Philadelphia Redevelopment Authority
Drexel University



