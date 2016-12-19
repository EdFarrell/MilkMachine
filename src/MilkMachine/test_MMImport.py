import unittest

import logging
import os

# make sure SIP versions are correct
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QDate', 2)
sip.setapi('QDateTime', 2)
sip.setapi('QTextStream', 2)
sip.setapi('QTime', 2)
sip.setapi('QUrl', 2)

from qgis.core import QgsApplication, QgsVectorLayer
from MMImport import loadCSVLayer

def mockLogger():
    logger = logging.getLogger('milkmachine')
    logger.setLevel(logging.DEBUG)

    # create a file handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

class MockMessageBar:
    def __init__(self, logger):
        self.logger = logger
        self.gotSuccess = False

    def pushMessage(self, title, body, level, duration):
        self.logger.info("{0}: {1}".format(title, body))

        if title == "Success":
            self.gotSuccess = True

class MockMessageBox:
    @staticmethod
    def critical(window, title, body):
        pass

    @staticmethod
    def warning(window, title, body):
        pass

# generic function for finding the idices of qgsvector layers
def field_indices(qgsvectorlayer):
    field_dict = {}
    fields = qgsvectorlayer.dataProvider().fields()
    for f in fields:
        field_dict[f.name()] = qgsvectorlayer.fieldNameIndex(f.name())
    return field_dict

class TestMMImport(unittest.TestCase):
    def testImportCSVFile(self):
        QgsApplication.setPrefixPath("/usr/share/qgis", True)
        qgs = QgsApplication([], False)
        # load providers
        qgs.initQgis()

        # shapefile
        aroundtheblockPath = os.path.join(os.path.abspath("../../sampledata/aroundtheblock/"), "aroundtheblock.csv")
        logger = mockLogger()
        messageBar = MockMessageBar(logger)
        messageBox = MockMessageBox
        layer = loadCSVLayer(
            dateFormat='mm/dd/yyyy',
            gpsPath=aroundtheblockPath,
            logger=logger,
            mainWindow=None,
            messageBar=messageBar,
            messageBox=messageBox
        )

        self.assertIsNotNone(layer)
        self.assertIsInstance(layer, QgsVectorLayer)
        self.assertTrue(layer.isValid())

        featuresCount = sum(1 for _ in layer.getFeatures())
        self.assertEqual(featuresCount, 587)

        # both segfault:
        # QgsApplication.exitQgis()
        # qgs.exitQgis()

if __name__ == '__main__':
    unittest.main()
