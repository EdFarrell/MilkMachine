import datetime
import decimal
import math
import os
import simplekml

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint, QgsVectorFileWriter
from qgis.gui import QgsMessageBar

def wgs84LatLonToUTMZone(latitude, longitude):
    """
    Finds the UTM zone which contains the given WGS84 point.

    Args:
        param1: The WGS84 latitude.
        param2: The WGS84 longitude.

    Returns:
        A tuple of the UTM zone integer and the UTM latitude band character

    >>> wgs84LatLonToUTMZone(13.41250188, 103.86666901)
    (48.0, 'P')
    """
    # based on http://www.movable-type.co.uk/scripts/latlong-utm-mgrs.html
    zone = math.floor((longitude + 180) / 6) + 1 # longitudinal zone

    # handle Norway/Svalbard exceptions
    # grid zones are 8 degrees tall; 0N is offset 10 into latitude bands array
    mgrsLatBands = 'CDEFGHJKLMNPQRSTUVWXX' # X is repeated for 80-84N
    latBand = mgrsLatBands[int(math.floor(latitude / 8 + 10))]
    # adjust zone & central meridian for Norway
    if zone == 31 and latBand == 'V' and longitude >= 3:
        zone += 1
    # adjust zone & central meridian for Svalbard
    elif zone == 32 and latBand == 'X' and longitude < 9:
        zone -= 1
    elif zone == 32 and latBand == 'X' and longitude >= 9:
        zone += 1
    elif zone == 34 and latBand == 'X' and longitude < 21:
        zone -= 1
    elif zone == 34 and latBand == 'X' and longitude >= 21:
        zone += 1
    elif zone == 36 and latBand == 'X' and longitude < 33:
        zone -= 1
    elif zone ==36 and latBand == 'X' and longitude >=33:
        zone += 1
    else:
        pass

    return zone, latBand

def makeCoordinateReferenceSystem(latitude, utmZone):
    """
    Creates a coordinate reference system, for instance for converting to this system.

    Args:
        param1: The WGS84 latitude.
        param2: The UTM zone number.

    Returns:
        A valid QgsCoordinateReferenceSystem or None

    >>> makeCoordinateReferenceSystem(13.41250188, 48) #doctest: +ELLIPSIS
    <qgis._core.QgsCoordinateReferenceSystem object at 0x...>

    >>> makeCoordinateReferenceSystem(13.41250188, 21442) is None
    True
    """
    crs = QgsCoordinateReferenceSystem()
    proj4String = "+proj=utm +ellps=WGS84 +datum=WGS84 +units=m +zone=%s" % utmZone
    if latitude < 0:
        proj4String += " +south"
    result = crs.createFromProj4(proj4String)
    return crs if result and crs.isValid() else None

def exportToFile(activeLayer, audioHREF, audioOffset, exportPath, fields, lastDirectory, logger, loggerPath, messageBar):
    cc = 0
    kml = simplekml.Kml()
    camStartTime = 0

    featureIds = activeLayer.allFeatureIds()
    features = list(activeLayer.getFeatures())

    # run through the datetime field and get all of the durations. these will be used for FlyTo durations
    allfids = featureIds
    endRow = len(allfids) - 1
    ttcount = 0
    time1 = []
    for fg in features: #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
        currentatt = fg.attributes()
        # Start time. Will be used for TimeSpan tags
        pointdate = currentatt[fields['datetime']].split(" ")[0]  #2014/06/06
        pointtime = currentatt[fields['datetime']].split(" ")[1] #10:38:48
        try:
            pointtime_ms = currentatt[fields['datetime']].split(" ")[2]  # microsecond range(1000000)
        except:
            pointtime_ms = 0
        current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), int(pointtime_ms))
        # time1.append(current_dt.second + round(current_dt.microsecond/float(1000000),6))
        time1.append(current_dt)
    # logger.info('time1: %s' % time1)
    # iterate time1 and calculate the durations
    Durations = []
    for iii, vvv in enumerate(time1):
        tdobj = time1[iii+1] - vvv
        # durstring = str(tdobj.seconds) + '.' + str(tdobj.microseconds/float(1000000)).split('.')[1]
        dur = tdobj.seconds + decimal.Decimal(tdobj.microseconds/float(1000000))
        durstring = format(dur, '.6f')
        Durations.append(durstring)
        logger.info('start: {0}, end: {1}, diff: {2}'.format(vvv, time1[iii+1], durstring))
        if (iii+1) == endRow:
            Durations.append(durstring)
            break
    # logger.info('Durations: %s' % Durations)
    # logger.info('Len Durations: %s' % len(Durations))

    #################################
    ## Tour and Camera
    globalcounter = 0
    for f in features: #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
        currentatt = f.attributes()

        if currentatt[fields['lookat']] and currentatt[fields['lookat']] != 'circlearound':
            lookatBack = {'a':'longitude','b' :'latitude','c' :'altitude','d' :'altitudemode','e':'gxaltitudemode','f':'heading','g':'tilt','h' :'range','i' :'duration','j' :'startheading', 'k': 'rotations', 'l': 'direction', 'm': 'streetview'}
            lookat = eval(currentatt[fields['lookat']])
            #convert back to full format
            newlookat = {}
            for kk,vv in lookat.iteritems():
                newlookat[lookatBack[kk]] = vv
            lookatdict = newlookat

            flytodict = eval(currentatt[fields['flyto']])

            if cc == 0:

                # First, put in a <Camera> that matches the same <Camera> at the beginning of the tour, that
                # there is no strange camera movement at the beginning.

                #firstcam_pnt = kml.newpoint()
                kml.document.lookat = simplekml.LookAt()


                # Create a tour and attach a playlist to it
                if flytodict['name']:
                    tour = kml.newgxtour(name=flytodict['name'])
                else:
                    tour = kml.newgxtour(name="Tour")

                playlist = tour.newgxplaylist()

                # Start time. Will be used for TimeSpan tags
                pointdate = currentatt[fields['datetime']].split(" ")[0]  #2014/06/06
                pointtime = currentatt[fields['datetime']].split(" ")[1] #10:38:48
                try:
                    pointtime_ms = currentatt[fields['datetime']].split(" ")[2]  # microsecond range(1000000)
                except:
                    pointtime_ms = 0
                current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), int(pointtime_ms))
                camStartTime = current_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

                # Attach a gx:SoundCue to the playlist and delay playing by 2 second (sound clip is about 4 seconds long)
                if audioHREF:
                    soundcue = playlist.newgxsoundcue()
                    soundcue.href = audioHREF
                    soundcue.gxdelayedstart = audioOffset


                cc += 1


            ##########################################
            ##########################################

            # Start time. Will be used for TimeSpan tags
            pointdate = currentatt[fields['datetime']].split(" ")[0]  #2014/06/06
            pointtime = currentatt[fields['datetime']].split(" ")[1] #10:38:48
            try:
                pointtime_ms = currentatt[fields['datetime']].split(" ")[2]  # microsecond range(1000000)
            except:
                pointtime_ms = 0
            current_dt_end = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), int(pointtime_ms)) #+ datetime.timedelta(seconds=5)
            camendtime = current_dt_end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            ## Cirle Around
            if lookatdict['startheading'] and lookatdict['rotations']:  # lookatdict['duration']  this is for a circle around
                if lookatdict['longitude'] and lookatdict['latitude'] and lookatdict['altitude'] and lookatdict['tilt'] and lookatdict['range']:
                    circle_count = int(float(lookatdict['rotations']))
                    if circle_count > 1:
                        divisor = 36  #36
                        bottomnum = (divisor+1) + ((circle_count-1)*divisor)
                        duration = (float(lookatdict['duration']))/bottomnum
                        timsspanDur = (float(lookatdict['duration']))/(circle_count * divisor)
                        #duration = (float(lookatdict['duration']))/(circle_count * divisor)
                    else:
                        divisor = 36
                        duration = (float(lookatdict['duration']))/(circle_count * (divisor+1))
                        timsspanDur = (float(lookatdict['duration']))/(circle_count * divisor)
                    timekeeper = current_dt_end

                    # Loop through Circle Count
                    for x in range(circle_count):
                        # Define the initial heading based on current heading
                        if x == 0:
                            heading = float(lookatdict['startheading'])
                            divisor = 37
                        else:
                            divisor = 36
                        # 360 Degrees/10 = 36 intervals to iterate through
##                                if x == range(circle_count)[-1]:
##                                    divisor = 37
                        for y in range(divisor):
                            # New Fly To
                            flyto = playlist.newgxflyto(gxduration=duration)
                            if flytodict['flyToMode']:
                                flyto.gxflytomode = flytodict['flyToMode']
                            flyto.lookat.latitude = lookatdict['latitude']
                            flyto.lookat.longitude = lookatdict['longitude']
                            flyto.lookat.altitude =  lookatdict['altitude']
                            if lookatdict['altitudemode'] == 'absolute':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.absolute
                            if lookatdict['altitudemode'] == 'clampToGround':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.clamptoground
                            if lookatdict['altitudemode'] == 'relativeToGround':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                            if lookatdict['altitudemode'] == 'relativeToPoint':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                            if lookatdict['altitudemode'] == 'relativeToModel':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                            flyto.lookat.tilt = lookatdict['tilt']
                            flyto.lookat.range = lookatdict['range']
                            flyto.lookat.heading = heading

                            # Time Span
                            flyto.lookat.gxtimespan.begin = camStartTime
                            flyto.lookat.gxtimespan.end = timekeeper.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

                            timekeeper = timekeeper + datetime.timedelta(seconds = timsspanDur)

                            # adjust the heading by 10 degrees
                            if lookatdict['direction'] == 'clockwise':
                                heading = (heading + 10) % 360
                            if lookatdict['direction'] == 'counterclockwise':
                                heading = (heading - 10) % 360

            ## LookAt Custom
            else:  # non circle around, just custom
                if lookatdict['longitude'] and lookatdict['latitude'] and lookatdict['altitude'] and lookatdict['heading'] and lookatdict['tilt'] and lookatdict['range']:
                    if flytodict['duration']:
                        flyto = playlist.newgxflyto(gxduration=float(flytodict['duration']))
                    else:
                        flyto = playlist.newgxflyto()
                    if flytodict['flyToMode']:
                        flyto.gxflytomode = flytodict['flyToMode']
                    flyto.lookat.longitude = lookatdict['longitude']
                    flyto.lookat.latitude = lookatdict['latitude']
                    flyto.lookat.altitude = lookatdict['altitude']
                    if lookatdict['altitudemode'] == 'absolute':
                        flyto.lookat.altitudemode = simplekml.AltitudeMode.absolute
                    if lookatdict['altitudemode'] == 'clampToGround':
                        flyto.lookat.altitudemode = simplekml.AltitudeMode.clamptoground
                    if lookatdict['altitudemode'] == 'relativeToGround':
                        flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                    if lookatdict['altitudemode'] == 'relativeToPoint':
                        flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                    if lookatdict['altitudemode'] == 'relativeToModel':
                        flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                    flyto.lookat.heading = lookatdict['heading']
                    flyto.lookat.tilt = lookatdict['tilt']
                    flyto.lookat.range = lookatdict['range']
                    if lookatdict['gxaltitudemode']:
                        flyto.lookat.gxaltitudemode = lookatdict['gxaltitudemode']
                    # Time Span
                    flyto.lookat.gxtimespan.begin = camStartTime
                    flyto.lookat.gxtimespan.end = camendtime



            if cc == 1:  # this is the first thing, not camera
                kml.document.lookat = flyto.lookat
                if lookatdict['streetview']:
                    kml.document.lookat.gxvieweroptions.newgxoption(name=simplekml.GxOption.streetview)

            cc+=1


        if currentatt[fields['camera']]:
                # camera = {'longitude': None, 'longitude_off': None, 'latitude': None, 'latitude_off': None,
                # 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'gxhoriz' : None,
                # 'heading' : None,'roll' : None,'tilt' : None}

            if cc == 0:  # establish this as the start of the tour
                camera = eval(currentatt[fields['camera']])
                cameraBack = {'a': 'longitude', 'b': 'longitude_off','c': 'latitude','d': 'latitude_off','e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle', 'n': 'streetview', 'o': 'hoffset'}

                #convert back to full format
                newcam = {}
                for kk,vv in camera.iteritems():
                    newcam[cameraBack[kk]] = vv
                cameradict = newcam

                flytodict = eval(currentatt[fields['flyto']])

                # First, put in a <Camera> that matches the same <Camera> at the beginning of the tour, that
                # there is no strange camera movement at the beginning.

                #firstcam_pnt = kml.newpoint()
                kml.document.camera = simplekml.Camera()


                # Create a tour and attach a playlist to it
                if flytodict['name']:
                    tour = kml.newgxtour(name=flytodict['name'])
                else:
                    tour = kml.newgxtour(name="Tour")

                playlist = tour.newgxplaylist()

                # Start time. Will be used for TimeSpan tags
                pointdate = currentatt[fields['datetime']].split(" ")[0]  #2014/06/06
                pointtime = currentatt[fields['datetime']].split(" ")[1] #10:38:48
                try:
                    pointtime_ms = currentatt[fields['datetime']].split(" ")[2]  # microsecond range(1000000)
                except:
                    pointtime_ms = 0
                current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]) )
                current_dt_end = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), int(pointtime_ms)) #+ datetime.timedelta(seconds=5)
                camStartTime = current_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                camendtime = current_dt_end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


                # Attach a gx:SoundCue to the playlist and delay playing by 2 second (sound clip is about 4 seconds long)
                if audioHREF:
                    soundcue = playlist.newgxsoundcue()
                    soundcue.href = audioHREF
                    soundcue.gxdelayedstart = audioOffset


                if flytodict['duration']:
                    flyto = playlist.newgxflyto(gxduration=float(flytodict['duration']))
                elif flytodict['duration'] is None:
                    flyto = playlist.newgxflyto(gxduration=float(Durations[globalcounter]))

                else:
                    flyto = playlist.newgxflyto()
                if flytodict['flyToMode']:
                    flyto.gxflytomode = flytodict['flyToMode']




                if cameradict['longitude'] and cameradict['latitude']:
                    if cameradict['longitude_off'] or cameradict['latitude_off']: # If there is an offset
                        longitude = float(cameradict['longitude'])
                        latitude = float(cameradict['latitude'])
                        zone, band = wgs84LatLonToUTMZone(latitude, longitude)

                        crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
                        crsDest = makeCoordinateReferenceSystem(latitude, zone)
                        xform = QgsCoordinateTransform(crsSrc, crsDest)
                        xform2 = QgsCoordinateTransform(crsDest, crsSrc)

                        utmpt = xform.transform(QgsPoint(longitude, latitude))
                        utmptlist = [utmpt[0], utmpt[1]]
                        # now add the utm point to the new feature
                        if cameradict['longitude_off']:
                            utmptlist[0] = float(utmpt[0]) + float(cameradict['longitude_off'])
                        if cameradict['latitude_off']:
                            utmptlist[1] = float(utmpt[1]) + float(cameradict['latitude_off'])

                        offsetpt = xform2.transform(QgsPoint(utmptlist[0],utmptlist[1]))

                        #firstcam_pnt.camera.longitude = offsetpt[0]
                        #firstcam_pnt.camera.latitude = offsetpt[1]

                        flyto.camera.longitude = offsetpt[0]
                        flyto.camera.latitude = offsetpt[1]

                    elif cameradict['range'] and cameradict['heading'] and cameradict['altitude']:
                        longitude = float(cameradict['longitude'])
                        latitude = float(cameradict['latitude'])
                        zone, band = wgs84LatLonToUTMZone(latitude, longitude)

                        crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
                        crsDest = makeCoordinateReferenceSystem(latitude, zone)
                        xform = QgsCoordinateTransform(crsSrc, crsDest)
                        xform2 = QgsCoordinateTransform(crsDest, crsSrc)

                        utmpt = xform.transform(QgsPoint(longitude, latitude))
                        utmptlist = [utmpt[0], utmpt[1]]  # x,y utm

                        if cameradict['follow_angle']:
                            follow_angle = math.radians(float(cameradict['follow_angle']))
                            # now you need to change heading. It should be rotated
                        else:
                            follow_angle = math.pi
                        opp_rad = (math.radians(float(cameradict['heading'])) + follow_angle) % (2*math.pi) #opposite angle in radians
                        #leg_distance = float(cameradict['range']) * sin(float(cameradict['tilt']))

                        if cameradict['altitudemode'] == 'relativeToModel':
                            modeldict = eval(currentatt[fields['model']])
                            camaltitude = float(cameradict['altitude']) - float(modeldict['altitude'])
                        else:
                            camaltitude = float(cameradict['altitude'])

                        leg_distance = math.sqrt( float(cameradict['range'])**2 - camaltitude**2 ) # horizontal distance between the camera at altiduce and the range
                        heading_rad = math.radians(float(cameradict['heading']))
                        x_dist = math.sin(opp_rad) * leg_distance
                        y_dist = math.cos(opp_rad) * leg_distance

                        utm_camera = ((utmpt[0] + x_dist), (utmpt[1] + y_dist))
                        wgs_camera = xform2.transform(QgsPoint(utm_camera[0], utm_camera[1]))

                        flyto.camera.longitude = wgs_camera[0]
                        flyto.camera.latitude = wgs_camera[1]

                        # camera tilt


                    else:
                        flyto.camera.longitude = cameradict['longitude']
                        flyto.camera.latitude = cameradict['latitude']
##                        if cameradict['latitude']:
##                            ifcameradict['latitude_off']:
##                                pass
##                            else:
##                                flyto.camera.latitude = cameradict['latitude']
                if cameradict['altitude']:
                    flyto.camera.altitude = cameradict['altitude']
                if cameradict['altitudemode']:
                    if cameradict['altitudemode'] == 'absolute':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.absolute
                    if cameradict['altitudemode'] == 'clampToGround':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.clamptoground
                    if cameradict['altitudemode'] == 'relativeToGround':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                    if cameradict['altitudemode'] == 'relativeToPoint':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                    if cameradict['altitudemode'] == 'relativeToModel':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground

##                        if cameradict['altitude']:
##                            if cameradict['altitudemode'] == 'relativeToPoint':
##                                flyto.camera.altitude = cameradict['altitude'] +
##                            if cameradict['altitudemode'] == 'relativeToModel':
##
##                                flyto.camera.altitude = cameradict['altitude'] +
##
##                                loc.altitude = currentatt[fields['Descriptio']].split(",")[4].split(': ')[1]  #u'-3.756733'

                if cameradict['gxaltitudemode']:
                    if cameradict['gxaltitudemode'] == 'clampToSeaFloor':
                        flyto.camera.gxaltitudemode = simplekml.GxAltitudeMode.clampToSeaFloor
                    if cameradict['gxaltitudemode'] == 'relativeToSeaFloor':
                        flyto.camera.gxaltitudemode = simplekml.GxAltitudeMode.relativetoseafloor
                if cameradict['gxhoriz']:
                    flyto.camera.gxhoriz = cameradict['gxhoriz']
                if cameradict['heading']:
                    if cameradict['follow_angle']:
                        newhead = math.degrees((math.radians(float(cameradict['heading'])) + follow_angle + math.pi) % (2 * math.pi))
                        if cameradict['hoffset']:
                            flyto.camera.heading = round((newhead + float(cameradict['hoffset'])) % 360, 1)
                        else:
                            flyto.camera.heading = newhead
                    else:
                        flyto.camera.heading = cameradict['heading']
                if cameradict['roll']:
                    flyto.camera.roll = cameradict['roll']
                if cameradict['tilt']:
                    flyto.camera.tilt = cameradict['tilt']

                # Time Span
                flyto.camera.gxtimespan.begin = camStartTime
                flyto.camera.gxtimespan.end = camendtime


                #firstcam_pnt.camera = flyto.camera
                kml.document.camera = flyto.camera
                if cameradict['streetview']:
                    kml.document.camera.gxvieweroptions.newgxoption(name=simplekml.GxOption.streetview)

                cc += 1

            else:  # everything after zero camera
                camera = eval(currentatt[fields['camera']])
                cameraBack = {'a': 'longitude', 'b': 'longitude_off','c': 'latitude','d': 'latitude_off','e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle', 'n': 'streetview', 'o': 'hoffset'}


                #convert back to full format
                newcam = {}
                for kk,vv in camera.iteritems():
                    newcam[cameraBack[kk]] = vv
                cameradict = newcam
                flytodict = eval(currentatt[fields['flyto']])

                # Start time. Will be used for TimeSpan tags
                pointdate = currentatt[fields['datetime']].split(" ")[0]  #2014/06/06
                pointtime = currentatt[fields['datetime']].split(" ")[1] #10:38:48
                try:
                    pointtime_ms = currentatt[fields['datetime']].split(" ")[2]  # microsecond range(1000000)
                except:
                    pointtime_ms = 0
                current_dt_end = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), int(pointtime_ms))# + datetime.timedelta(seconds=5)
                camendtime = current_dt_end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

                if flytodict['duration']:
                    flyto = playlist.newgxflyto(gxduration=float(flytodict['duration']))
                elif flytodict['duration'] is None:
                    flyto = playlist.newgxflyto(gxduration=float(Durations[globalcounter]))
                else:
                    flyto = playlist.newgxflyto()
                if flytodict['flyToMode']:
                    flyto.gxflytomode = flytodict['flyToMode']

                if cameradict['longitude'] and cameradict['latitude']:
                    if cameradict['longitude_off'] or cameradict['latitude_off']: # If there is an offset
                        longitude = float(cameradict['longitude'])
                        latitude = float(cameradict['latitude'])
                        zone, band = wgs84LatLonToUTMZone(latitude, longitude)

                        crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
                        crsDest = makeCoordinateReferenceSystem(latitude, zone)
                        xform = QgsCoordinateTransform(crsSrc, crsDest)
                        xform2 = QgsCoordinateTransform(crsDest, crsSrc)

                        utmpt = xform.transform(QgsPoint(longitude, latitude))
                        utmptlist = [utmpt[0], utmpt[1]]
                        # now add the utm point to the new feature
                        if cameradict['longitude_off']:
                            utmptlist[0] = float(utmpt[0]) + float(cameradict['longitude_off'])
                        if cameradict['latitude_off']:
                            utmptlist[1] = float(utmpt[1]) + float(cameradict['latitude_off'])

                        offsetpt = xform2.transform(QgsPoint(utmptlist[0],utmptlist[1]))

                        flyto.camera.longitude = offsetpt[0]
                        flyto.camera.latitude = offsetpt[1]

                    elif cameradict['range'] and cameradict['heading'] and cameradict['altitude']:
                        longitude = float(cameradict['longitude'])
                        latitude = float(cameradict['latitude'])
                        zone, band = wgs84LatLonToUTMZone(latitude, longitude)

                        crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
                        crsDest = makeCoordinateReferenceSystem(latitude, zone)
                        xform = QgsCoordinateTransform(crsSrc, crsDest)
                        xform2 = QgsCoordinateTransform(crsDest, crsSrc)

                        utmpt = xform.transform(QgsPoint(longitude, latitude))
                        utmptlist = [utmpt[0], utmpt[1]]  # x,y utm

                        if cameradict['follow_angle']:
                            follow_angle = math.radians(float(cameradict['follow_angle']))
                        else:
                            follow_angle = math.pi
                        opp_rad = (math.radians(float(cameradict['heading'])) + follow_angle) % (2*math.pi) #opposite angle in radians from the heading. So you can calculate the direction whre the camerea should be placed

                        if cameradict['altitudemode'] == 'relativeToModel':
                            modeldict = eval(currentatt[fields['model']])
                            camaltitude = float(cameradict['altitude']) - float(modeldict['altitude'])
                        else:
                            camaltitude = float(cameradict['altitude'])
                        leg_distance = math.sqrt( float(cameradict['range'])**2 - camaltitude**2 ) # horizontal distance between the camera at altiduce and the range


                        #leg_distance = math.sqrt( float(cameradict['range'])**2 - float(cameradict['altitude'])**2 ) # horizontal distance between the camera at altiduce and the range
                        heading_rad = math.radians(float(cameradict['heading']))
                        x_dist = math.sin(opp_rad) * leg_distance
                        y_dist = math.cos(opp_rad) * leg_distance

                        utm_camera = ((utmpt[0] + x_dist), (utmpt[1] + y_dist))
                        wgs_camera = xform2.transform(QgsPoint(utm_camera[0], utm_camera[1]))

                        #logger.info('wgs xy {0}'.format(wgs_camera))
                        flyto.camera.longitude = wgs_camera[0]
                        flyto.camera.latitude = wgs_camera[1]

                        # camera tilt


                    else:
                        flyto.camera.longitude = cameradict['longitude']
                        flyto.camera.latitude = cameradict['latitude']
                if cameradict['altitude']:
                    flyto.camera.altitude = cameradict['altitude']
                if cameradict['altitudemode']:
                    if cameradict['altitudemode'] == 'absolute':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.absolute
                    if cameradict['altitudemode'] == 'clampToGround':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.clamptoground
                    if cameradict['altitudemode'] == 'relativeToGround':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                    if cameradict['altitudemode'] == 'relativeToPoint':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                    if cameradict['altitudemode'] == 'relativeToModel':
                        flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                if cameradict['gxaltitudemode']:
                    if cameradict['gxaltitudemode'] == 'clampToSeaFloor':
                        flyto.camera.gxaltitudemode = simplekml.GxAltitudeMode.clampToSeaFloor
                    if cameradict['gxaltitudemode'] == 'relativeToSeaFloor':
                        flyto.camera.gxaltitudemode = simplekml.GxAltitudeMode.relativetoseafloor
                if cameradict['gxhoriz']:
                    flyto.camera.gxhoriz = cameradict['gxhoriz']
                if cameradict['heading']:
                    if cameradict['follow_angle']:
                        newhead = math.degrees((math.radians(float(cameradict['heading'])) + follow_angle + math.pi) % (2 * math.pi))
                        if cameradict['hoffset']:
                            flyto.camera.heading = round((newhead + float(cameradict['hoffset'])) % 360, 1)
                        else:
                            flyto.camera.heading = newhead
                    else:
                        flyto.camera.heading = float(cameradict['heading'])
                if cameradict['roll']:
                    flyto.camera.roll = float(cameradict['roll'])
                if cameradict['tilt']:
                    flyto.camera.tilt = float(cameradict['tilt'])

                # Time Span
                flyto.camera.gxtimespan.begin = camStartTime
                flyto.camera.gxtimespan.end = camendtime

                # Gx Viewer Options
##                        if cameradict['streetview']:
##                            gxview = simplekml.GxViewerOptions(name=simplekml.GxOption.streetview, enabled = True)


                cc += 1

            #kml.document.camera = simplekml.Camera()
            #kml.document.camera = flyto.camera

        globalcounter += 1



    ###############################3
    ## Points
    cc = 0
    folder = kml.newfolder(name='Points')
    for f in features: #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
        geom = f.geometry()
        coords = geom.asPoint() #(-75.1722,39.9659)
        currentatt = f.attributes()

        if currentatt[fields['iconstyle']]:

            pointdate = currentatt[fields['datetime']].split(" ")[0]  #2014/06/06
            pointtime = currentatt[fields['datetime']].split(" ")[1] #10:38:48
            try:
                pointtime_ms = currentatt[fields['datetime']].split(" ")[2]  # microsecond range(1000000)
            except:
                pointtime_ms = 0
            current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), int(pointtime_ms))

            pnt = folder.newpoint(name=str(cc), coords=[(coords[0], coords[1])], description=str(currentatt[1]))
            pnt.timestamp.when = current_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            def transtokmlhex(trans):
                dec = int(float(icondict['transparency']) * 2.55)
                if dec < 10:
                    return '0' + str(dec)
                else:
                    return str(hex(dec)[2:4])

        # Icon Style
        # icon = {'color': None, 'colormode': None,'scale' : None, 'heading': None,'icon' : None ,'hotspot' : None}
        #if currentatt[fields['iconstyle']]:
            icondict = eval(currentatt[fields['iconstyle']])

            if icondict['color']:
                pnt.style.iconstyle.color = simplekml.Color.__dict__[icondict['color']]
            if icondict['color'] and icondict['transparency']:
                transvalue = transtokmlhex(icondict['transparency'])
                colorpick = simplekml.Color.__dict__[icondict['color']]
                pnt.style.iconstyle.color = transvalue + colorpick[2:8]
            if icondict['colormode']:
                pnt.style.iconstyle.colormode = icondict['colormode']
            if icondict['scale']:
                pnt.style.iconstyle.scale = icondict['scale']
            if icondict['heading']:
                pnt.style.iconstyle.heading = icondict['heading']
            if icondict['icon']:
                pnt.style.iconstyle.icon.href = icondict['icon']


            # Label Style
            # label = {'color': None, 'colormode': None,'scale' : None}
            if currentatt[fields['labelstyle']]:
                labeldict = eval(currentatt[fields['labelstyle']])
                if labeldict['color']:
                    pnt.style.labelstyle.color = simplekml.Color.__dict__[labeldict['color']]
                if labeldict['colormode']:
                    pnt.style.labelstyle.colormode = labeldict['colormode']
                if labeldict['scale']:
                    pnt.style.labelstyle.scale = labeldict['scale']

        cc += 1

    ###############################3
    ## Models
    cc = 0
    mfolder = kml.newfolder(name='Models')
    for f in features: #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
        geom = f.geometry()
        coords = geom.asPoint() #(-75.1722,39.9659)
        currentatt = f.attributes()

        if currentatt[fields['model']]:

            mdl = mfolder.newmodel()

            pointdate = currentatt[fields['datetime']].split(" ")[0]  #2014/06/06
            pointtime = currentatt[fields['datetime']].split(" ")[1] #10:38:48
            try:
                pointtime_ms = currentatt[fields['datetime']].split(" ")[2]  # microsecond range(1000000)
            except:
                pointtime_ms = 0
            current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]), int(pointtime_ms))

            mdl.name = current_dt.strftime('%X %m/%d/%Y')
            mdl.description = current_dt.strftime('%X %m/%d/%Y')

            #pnt = folder.newpoint(name=str(cc), coords=[(coords[0], coords[1])], description=str(currentatt[1]))
            #pnt.timestamp.when = current_dt.strftime('%Y-%m-%dT%XZ')


        # Model
        #model = {'link': None, 'longitude': None, 'latitude': None, 'altitude' : None, 'scale': None}
        #class simplekml.Model(altitudemode=None, gxaltitudemode=None, location=None, orientation=None, scale=None, link=None, resourcemap=None, **kwargs)
        #if currentatt[fields['model']]:
            modeldict = eval(currentatt[fields['model']])

            if modeldict['link']:
                mdl.link = simplekml.Link(href = modeldict['link'])

                loc = simplekml.Location()
                if modeldict['longitude']:
                    loc.longitude = modeldict['longitude']
                else:
                    loc.longitude = coords[0]

                if modeldict['latitude']:
                    loc.latitude = modeldict['latitude']
                else:
                    loc.latitude = coords[1]

                if modeldict['altitude']:
                    if modeldict['altitude'] == 'altitude':  # get the altitude from the gps  [u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']

                        try:
                            loc.altitude = currentatt[fields['descriptio']].split(",")[4].split(': ')[1]
                        except:
                            try:
                                loc.altitude = currentatt[fields['Descriptio']].split(",")[4].split(': ')[1]
                            except:
                                logger.error('export function error')
                                #logger.info('fields keys {0}'.format(fields.keys))
                                logger.exception(traceback.format_exc())
                                messageBar.pushMessage("Error", "exportToFile error. Please see error log at: {0}".format(loggerPath), level=QgsMessageBar.CRITICAL, duration=5)


                    else:
                        loc.altitude = modeldict['altitude']
                    mdl.altitudemode = 'relativeToGround'
                mdl.location = loc
                mdl.timestamp = simplekml.TimeStamp(when=current_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))



            scl = simplekml.Scale()
            if modeldict['scale']:
                scl.x = modeldict['scale']; scl.y = modeldict['scale']; scl.z = modeldict['scale']
                mdl.scale = scl


        cc += 1

#            if self.dlg.ui.lineEdit_export_audio.currentText():  # there is a wav file to attach. So only offer kmz

    if exportPath:
        # TODO: export this somehow
        lastDirectory = os.path.dirname(exportPath)
        if exportPath.split('.')[1] == 'kml':
            kml.save(exportPath)
            messageBar.pushMessage("Success", "kml file exported to: {0}".format(exportPath), level=QgsMessageBar.INFO, duration=5)
        if exportPath.split('.')[1] == 'kmz':
            kml.savekmz(exportPath)
            messageBar.pushMessage("Success", "kmz file exported to: {0}".format(exportPath), level=QgsMessageBar.INFO, duration=5)
        if exportPath.split('.')[1] == 'gpx':
            QgsVectorFileWriter.writeAsVectorFormat(activeLayer, exportPath, "utf-8", None, "GPX")
            messageBar.pushMessage("Success", "gpx file exported to: {0}".format(exportPath), level=QgsMessageBar.INFO, duration=5)
        if exportPath.split('.')[1] == 'shp':
            QgsVectorFileWriter.writeAsVectorFormat(activeLayer, exportPath, "utf-8", None, "ESRI Shapefile")
            messageBar.pushMessage("Success", "ESRI shapefile exported to: {0}".format(exportPath), level=QgsMessageBar.INFO, duration=5)
        if exportPath.split('.')[1] == 'geojson':
            QgsVectorFileWriter.writeAsVectorFormat(activeLayer, exportPath, "utf-8", None, "GeoJSON")
            messageBar.pushMessage("Success", "GeoJson file exported to: {0}".format(exportPath), level=QgsMessageBar.INFO, duration=5)
        if exportPath.split('.')[1] == 'csv':
            QgsVectorFileWriter.writeAsVectorFormat(activeLayer, exportPath, "utf-8", None, "CSV")
            messageBar.pushMessage("Success", "GeoJson file exported to: {0}".format(exportPath), level=QgsMessageBar.INFO, duration=5)
