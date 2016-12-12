import csv
import datetime
import re
import traceback

from PyQt4.QtCore import QVariant

from qgis.core import QgsField, QgsVectorFileWriter, QgsVectorLayer
from qgis.gui import QgsMessageBar

# generic function for finding the idices of qgsvector layers
def field_indices(qgsvectorlayer):
    field_dict = {}
    fields = qgsvectorlayer.dataProvider().fields()
    for f in fields:
        field_dict[f.name()] = qgsvectorlayer.fieldNameIndex(f.name())
    return field_dict

# given the path to a CSV file, returns a QgsVectorLayer
def loadCSVLayer(gpsPath, logger, messageBar, dateFormat, mainWindow, messageBox):
    fields = ['date', 'time', 'x', 'y', 'altitude']
    userfields = []
    with open(gpsPath, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        i = 0
        for row in reader:
            if i == 0: #header row
                #check for x
                for f in fields:
                    Fre = re.search(f, str(row), re.I)
                    if Fre:
                        userfields.append(Fre.group())
                    else:
                        # hang an error
                        logger.error('CSV column names import error. Failed on: %s' % f)
                        messageBox.critical(mainWindow, "Column Name Error", "Missing column: %s\n\nPlease reformat csv file. Column headers should include: 'date', 'time', 'x', 'y', 'altitude'" %(f))
            else:
                pass
            i += 1

        if i < 10:
            messageBox.warning(mainWindow, "Friendly Import Warning", "This track is pretty short, which if fine. However, some of the track smoothing and tour automation won't work great because it is geared for longer tracks. Give it a try anyway and let us know if you encounter an error or serious problem at https://github.com/EdFarrell/MilkMachine/issues" )

    if len(userfields) == 5:
        logger.info('headers %s' % userfields)
        messageBar.pushMessage("Success", "User file column headers good: {0}".format(gpsPath), level=QgsMessageBar.INFO, duration=5)

        #http://qgis.org/api/classQgsVectorLayer.html
        layername = gpsPath.split(".")[0].split('/')[-1]
        #crs = QgsCoordinateReferenceSystem(4326).toProj4()
        crs = 'EPSG:4326'
        uri = "file:/" + gpsPath + "?delimiter=%s&xField=%s&yField=%s&crs=%s" % (",", "x", "y", crs)
        logger.info('uri: %s' % uri)
        Qlayer = QgsVectorLayer(uri, layername, "delimitedtext")

        # check the rest of the fields. required are date, time, and z
        fdict = field_indices(Qlayer)
        logger.info('fdict : %s' %(fdict))

        # save the kml layer as
        shapepath = gpsPath.split(".")[0] + '.shp'
        shapepath_line = gpsPath.split(".")[0] + '_line.shp'
        #shapepath_dup = gpsPath.split(".")[0] + '_duplicate.shp'

        QgsVectorFileWriter.writeAsVectorFormat(Qlayer, shapepath, "utf-8", None, "ESRI Shapefile")  # working copy
        #bring the shapefile back in, and render it on the map
        shaper = QgsVectorLayer(shapepath, layername, "ogr")
        shaper.dataProvider().addAttributes( [QgsField("datetime",QVariant.String), QgsField("camera",QVariant.String), QgsField("flyto",QVariant.String), QgsField("iconstyle", QVariant.String), QgsField("labelstyle", QVariant.String), QgsField("model", QVariant.String), QgsField("lookat", QVariant.String) , QgsField("symbtour", QVariant.String)])
        shaper.updateFields()

        fields = field_indices(shaper)
        # calculate the datetime field
        # idx = fields['datetime']  #feature.attributes()[idx]
        fid_dt = []
        # model_altitude = []
        try:
            for f in shaper.getFeatures():
                # currentatt = f.attributes()[fields['datetime']]  # this should be fields['Name']
                pointdate = f.attributes()[fields['date']]  #2014/06/06
                pointtime = f.attributes()[fields['time']]

                # format for microseconds
                sec_pieces = pointtime.split(':')[2].split('.')
                if len(sec_pieces) == 1:
                    microsec = 0
                elif len(sec_pieces) == 2:
                    microsec = int(float('0.' + sec_pieces[1]) * 1000000)

                #['mm/dd/yyyy', 'dd/mm/yyyy', 'yyyy/mm/dd']
                if dateFormat == 'mm/dd/yyyy':
                    current_dt = datetime.datetime(int(pointdate.split('/')[2]), int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), microsec)
                elif dateFormat == 'dd/mm/yyyy':
                    current_dt = datetime.datetime(int(pointdate.split('/')[2]), int(pointdate.split('/')[1]), int(pointdate.split('/')[0]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), microsec)
                elif dateFormat == 'yyyy/mm/dd':
                    current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), microsec)

                fid_dt.append([f.id(), current_dt.strftime("%Y/%m/%d %H:%M:%S %f")])

            shaper.startEditing()
            shaper.beginEditCommand('datetime')
            for i,v in enumerate(fid_dt):
                shaper.changeAttributeValue(v[0],fields['datetime'], v[1])
            shaper.endEditCommand()
            shaper.commitChanges()

            return shaper
        except:
            logger.error('Error writing time to datetime column, user presented with messagebox')
            logger.exception(traceback.format_exc())
            messageBox.critical(mainWindow,"Date & Time Import Error", "An error occured while converting the 'date' and 'time' fields into a Python datetime object. Please make sure that your specified the correct date format, and the time format is HH:MM:SS. If your seconds are fractional, then please express this as SS.xxxxxx")
