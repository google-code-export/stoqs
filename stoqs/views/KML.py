import os
import sys
import time
import numpy
import settings
import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------------------------------------
# Support functions for rendering measurements into KML

def makeKML(dataHash, pName, title, desc, startDate, endDate):
    '''Generate the KML for the point in mpList'''

    #
    # Define the color lookup table and the color limits for each variable
    #
    clt = readCLT(os.path.join(settings.MEDIA_ROOT, 'jetplus.txt'))
    climHash = { 'temperature': [9, 16]
            , 'sea_water_temperature': [9, 16]
            , 'Temperature': [9, 16]
            , 'sea_water_salinity': [32.6, 34]
            , 'salinity': [32.6, 34]
            , 'nitrate': [0, 25]
            , 'bbp420': [0, .01]
            , 'bbp700': [0, .01]
            , 'fl700_uncorr': [0, .001]
            , 'mass_concentration_of_chlorophyll_in_sea_water': [2, 10]
            , 'mass_concentration_of_oxygen_in_sea_water': [0, 10]
            , 'mole_concentration_of_nitrate_in_sea_water': [0, 30]
            , 'Biolume': [8.8, 10.5]
            , 'oxygen': [0, 10]
            }

    pointKMLHash = {}
    lineKMLHash = {}
    for k in dataHash.keys():
        (pointStyleKML, pointKMLHash[k]) = buildKMLpoints(k, dataHash[k], clt, climHash[pName])
        (lineStyleKML, lineKMLHash[k]) = buildKMLlines(k, dataHash[k], clt, climHash[pName])

    #
    # KML header
    #
    kml = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://earth.google.com/kml/2.1 http://code.google.com/apis/kml/schema/kml21.xsd">
<!-- %s -->
<!-- Mike McCann MBARI 28 October 2010 -->
<Document>
<name>%s</name>
<description>%s</description>
''' % ('Automatically generated by views.py', title, desc)

    kml += pointStyleKML
    kml += lineStyleKML

    #
    # See that the platforms are alphabetized in the KML.  (The point and line KMLHashes will have the same keys.)
    #
    platList = pointKMLHash.keys()
    platList.sort()
    for plat in platList:
        kml += '''<Folder>
<name>%s Points</name>
%s
</Folder>''' % (plat, pointKMLHash[plat])
        kml += '''<Folder>
<name>%s Lines</name>
%s
</Folder>''' % (plat, lineKMLHash[plat])


    #
    # Footer
    #
    kml += '''</Document>
</kml>'''

    return kml


def readCLT(fileName):
    '''Read the color lookup table from disk and return a python list of rgb tuples.
    '''

    cltList = []
    for rgb in open(fileName, 'r'):
        ##logger.debug("rgb = %s", rgb)
        (r, g, b) = rgb.split('  ')[1:]
        cltList.append([float(r), float(g), float(b)])

    return cltList


def buildKMLlines(plat, data, clt, clim):
    '''Build KML placemark LineStrings of all the point data in `list`
    Use distinctive line colors for each platform.
    the same way as is done in the auvctd dorado science data processing.
    `data` are the results of a query, say from xySlice()
    `clt` is a Color Lookup Table equivalent to a jetplus clt as used in Matlab
    `clim` is a 2 element list equivalent to clim in Matlab

    Return strings of style and point KML that can be included in a master KML file.

    '''

    styleKml = '''
<Style id="Tethys">
<LineStyle>
<color>ff0055ff</color>
<width>2</width>
</LineStyle>
</Style>
<Style id="Gulper_AUV">
<LineStyle>
<color>ff00ffff</color>
<width>2</width>
</LineStyle>
</Style>
<Style id="John Martin">
<LineStyle>
<color>ffffffff</color>
<width>1</width>
</LineStyle>
</Style>
'''

    #
    # Build the LineString for the points
    #
    lineKml = ''
    lastCoordStr = ''
    for row in data:
        (dt, lon, lat, depth, parm, datavalue, platform) = row

        coordStr = "%.6f,%.6f,-%.1f" % (lon, lat, depth)

        if lastCoordStr:
            placemark = """
<Placemark>
<styleUrl>#%s</styleUrl>
<TimeStamp>
<when>%s</when>
</TimeStamp>
<LineString>
<altitudeMode>absolute</altitudeMode>
<coordinates>
%s
</coordinates>
</LineString>
</Placemark> """         % (plat, time.strftime("%Y-%m-%dT%H:%M:%SZ", dt.timetuple()), lastCoordStr + ' ' + coordStr)

            lineKml += placemark

        lastCoordStr = coordStr

    return (styleKml, lineKml)


def buildKMLpoints(plat, data, clt, clim):
    '''Build KML Placemarks of all the point data in `list` and use colored styles 
    the same way as is done in the auvctd dorado science data processing.
    `data` are the results of a query, say from xySlice()
    `clt` is a Color Lookup Table equivalent to a jetplus clt as used in Matlab
    `clim` is a 2 element list equivalent to clim in Matlab

    Return strings of style and point KML that can be included in a master KML file.

    '''

    _debug = False


    #
    # Build the styles for the colors in clt using clim
    #
    styleKml = ''
    for c in clt:
        ge_color = "ff%02x%02x%02x" % ((round(c[2] * 255), round(c[1] * 255), round(c[0] * 255)))
        if _debug:
            logger.debug("c = %s", c)
            logger.debug("ge_color = %s", ge_color)

        style = '''<Style id="%s">
<IconStyle>
<color>%s</color>
<scale>0.6</scale>
<Icon>
<href>http://maps.google.com/mapfiles/kml/shapes/dot.png</href>
</Icon>
</IconStyle>
</Style>
''' % (ge_color, ge_color)

        styleKml += style

    #
    # Build the placemarks for the points
    #
    pointKml = ''
    for row in data:
        (dt, lon, lat, depth, parm, datavalue, platform) = row

        coordStr = "%.6f, %.6f,-%.1f" % (lon, lat, depth)

        if _debug:
            logger.debug("datavalue = %f", float(datavalue))
            logger.debug("clim = %s", clim)

        clt_index = int(round((float(datavalue) - clim[0]) * ((len(clt) - 1) / float(numpy.diff(clim)))))
        if clt_index < 0:
            clt_index = 0;
        if clt_index > (len(clt) - 1):
            clt_index = int(len(clt) - 1);
        if _debug:
            logger.debug("clt_index = %d", clt_index)
        ge_color_val = "ff%02x%02x%02x" % ((round(clt[clt_index][2] * 255), round(clt[clt_index][1] * 255), round(clt[clt_index][0] * 255)));

        placemark = """
<Placemark>
<styleUrl>#%s</styleUrl>
<TimeStamp>
<when>%s</when>
</TimeStamp>
<Point>
<altitudeMode>absolute</altitudeMode>
<coordinates>
%s
</coordinates>
</Point>
</Placemark> """         % (ge_color_val, time.strftime("%Y-%m-%dT%H:%M:%SZ", dt.timetuple()), coordStr)

        pointKml += placemark

    return (styleKml, pointKml)
