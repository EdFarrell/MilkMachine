import unittest

from datetime import datetime
import logging
import os

from qgis.core import QgsApplication, QgsVectorLayer
from MMImport import loadCSVLayer
from MMExport import exportToFile

import test_MMImport

class TestMMExport(unittest.TestCase):
    def testExportToFile(self):
        QgsApplication.setPrefixPath("/usr/share/qgis", True)
        qgs = QgsApplication([], False)
        # load providers
        qgs.initQgis()

        # shapefile
        aroundtheblockPath = os.path.join(os.path.abspath("../../sampledata/"), "amsterdam-yymmdd.csv")
        logger = test_MMImport.mockLogger()
        messageBar = test_MMImport.MockMessageBar(logger)
        messageBox = test_MMImport.MockMessageBox
        layer = loadCSVLayer(
            dateFormat='yyyy/mm/dd',
            gpsPath=aroundtheblockPath,
            logger=logger,
            mainWindow=None,
            messageBar=messageBar,
            messageBox=messageBox
        )
        self.assertTrue(layer.isValid())

        # reset the flag
        messageBar.gotSuccess = False

        dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields = test_MMImport.field_indices(layer)

        # if camera data should be included
        layer.startEditing()
        layer.beginEditCommand("Camera Editing")
        flyto = {'name': 'Test Tour', 'flyToMode': 'smooth', 'duration': 1}
        for index, feature in enumerate(layer.getFeatures()):
            # make a dictionary of all of the camera parameters
            attributes = feature.attributes()
            longitudeOffset = 0.001 * index
            latitudeOffset = 0.001 * index
            camera = {'longitude': attributes[fields['x']], 'longitude_off': longitudeOffset, 'latitude': attributes[fields['y']], 'latitude_off': latitudeOffset, 'altitude' : attributes[fields['altitude']], 'altitudemode': 'relativeToGround', 'gxaltitudemode': None, 'gxhoriz': None, 'heading': 0, 'roll': None, 'tilt': 48, 'range': None, 'follow_angle': None, 'streetview': None, 'hoffset': None}
            cameraAlpha = {'longitude': 'a', 'longitude_off': 'b', 'latitude': 'c', 'latitude_off': 'd', 'altitude': 'e', 'altitudemode': 'f', 'gxaltitudemode': 'g', 'gxhoriz': 'h', 'heading': 'i', 'roll': 'j', 'tilt': 'k', 'range': 'l', 'follow_angle': 'm', 'streetview': 'n', 'hoffset': 'o'}
            cameratemp = {}
            #convert to cameratemp
            for key,value in camera.iteritems():
                cameratemp[cameraAlpha[key]] = value
            layer.changeAttributeValue(feature.id(), fields['camera'], str(cameratemp))
            layer.changeAttributeValue(feature.id(), fields['flyto'], str(flyto))
            layer.changeAttributeValue(feature.id(), fields['lookat'], '') # get rid of lookats
        layer.endEditCommand()

        # if model data should be included
        # modelTemplate = {'link': None, 'longitude': None, 'latitude': None, 'altitude' : None, 'scale': None}
        # layer.startEditing()
        # layer.beginEditCommand("Rendering Editing")
        # for feature in layer.getFeatures():
        #     attributes = feature.attributes()
        #     model = modelTemplate
        #     model['link'] = 'files/red_sphereC.dae'
        #     model['longitude'] = attributes[fields['x']]
        #     model['latitude'] = attributes[fields['y']]
        #     model['scale'] = 1
        #     model['altitude'] = attributes[fields['altitude']]
        #     layer.changeAttributeValue(feature.id(), fields['model'], str(model))
        # layer.endEditCommand()

        loggerPath = ""
        exportToFile(
            activeLayer=layer,
            audioHREF="",
            audioOffset=0,
            exportPath="amsterdam-yymmdd.kml",
            fields=fields,
            lastDirectory=".",
            logger=logger,
            loggerPath=loggerPath,
            messageBar=messageBar
        )

        self.assertTrue(messageBar.gotSuccess)

        # qgs.exitQgis()

if __name__ == '__main__':
    unittest.main()
