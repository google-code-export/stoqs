#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2013, MBARI"
__license__ = "GPL"
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Script to query the database for measured parameters from the same instantpoint and to
make scatter plots of temporal segments of the data.  A simplified trackline of the
trajectory data and the start time of the temporal segment are added to each plot.

Make use of STOQS metadata to make it as simple as possible to use this script for
different platforms, parameters, and campaigns.

Mike McCann
MBARI Dec 6, 2013

@var __date__: Date of last svn commit
@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE']='settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # settings.py is one dir up

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DAILY
from datetime import datetime, timedelta
from django.contrib.gis.geos import LineString, Point
from utils.utils import round_to_n
from textwrap import wrap
from mpl_toolkits.basemap import Basemap
import matplotlib.gridspec as gridspec

from contrib.analysis import BiPlot, NoPPDataException


class PlatformsBiPlot(BiPlot):
    '''
    Make customized BiPlots (Parameter Parameter plots) for platforms from STOQS.
    '''

    def xySubPlot(self, x, y, platform, color, xParm, yParm, ax, startTime):
        '''
        Given names of platform, x & y paramters add a subplot to figure fig.
        '''

        xmin, xmax, xUnits = self._getAxisInfo(platform, xParm)
        ymin, ymax, yUnits = self._getAxisInfo(platform, yParm)

        # Make the plot 
        ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
        ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))
        ax.set_xlabel('%s (%s)' % (xParm, xUnits))
        ax.set_ylabel('%s (%s)' % (yParm, yUnits))
        #ax.set_title('%s' % (platform,)) 
        ##ax.set_title('%s from %s' % (platform, self.args.database)) 
        ax.scatter(x, y, marker='.', s=10, c=color, lw = 0, clip_on=True)
        ##ax.set_xticks([])
        ##ax.set_yticks([])
        ##ax.text(0.1, 0.8, startTime.strftime('%Y-%m-%d %H:%M'), transform=ax.transAxes)
        ax.text(0.5, 0.8, platform, transform=ax.transAxes, horizontalalignment='center')

        return ax

    def timeSubPlot(self, platformDTHash, ax, startTime, endTime, swrTS):
        '''
        Make subplot of depth time series for all the platforms and highlight the time range
        '''
        for pl, ats in platformDTHash.iteritems():
            color = self._getColor(pl)
            for a, ts in ats.iteritems():
                datetimeList = []
                depths = []
                for ems, d in ts:
                    datetimeList.append(datetime.utcfromtimestamp(ems/1000.0))
                    depths.append(d)
           
                ##print "Plotting %s: start = %s, end = %s" % (a, datetimeList[0], datetimeList[-1])
                ax.plot_date(matplotlib.dates.date2num(datetimeList), depths, '-', c=color, alpha=0.2)

        # Highlight the selected time extent
        ax.axvspan(*matplotlib.dates.date2num([startTime, endTime]), facecolor='y', alpha=0.2)  

        if self.args.minDepth is not None:
            print "setting mindepth to", self.args.minDepth
            ax.set_ylim(top=self.args.minDepth)
        if self.args.maxDepth:
            ax.set_ylim(bottom=self.args.maxDepth)
        ax.set_ylim(ax.get_ylim()[::-1])

        # Plot short wave radiometer data
        ax2 = ax.twinx()
        ax2.plot_date(matplotlib.dates.date2num(swrTS[0]), swrTS[1], '-', c='black', alpha=0.5)
        
        ax.set_xlabel('Time (GMT)')
        ax.set_ylabel('Depth (m)')
        ax2.set_ylabel('SWR (W/m^2)')
        loc = ax.xaxis.get_major_locator()
        loc.maxticks[DAILY] = 6

        return ax

    def spatialSubPlot(self, platformLineStringHash, ax, e):
        '''
        Make subplot of tracks for all the platforms within the time range
        '''
        m = Basemap(llcrnrlon=e[0], llcrnrlat=e[1], urcrnrlon=e[2], urcrnrlat=e[3], projection='cyl', resolution ='f', ax=ax)
 
        for pl, LS in platformLineStringHash.iteritems():
            x,y = zip(*LS)
            m.plot(x, y, '-', c=self._getColor(pl))

        m.drawcoastlines()
        m.drawmapboundary()
        m.drawparallels(np.linspace(e[1],e[3],num=4), labels=[True,False,False,False])
        m.drawmeridians(np.linspace(e[0],e[2],num=4), labels=[False,False,False,True])

        return ax

    def makeIntervalPlots(self):
        '''
        Make a plot each timeInterval starting at startTime
        '''

        self._getActivityExtent(self.args.platform)
        xmin, xmax, xUnits = self._getAxisInfo(self.args.platform, self.args.xParm)
        ymin, ymax, yUnits = self._getAxisInfo(self.args.platform, self.args.yParm)

        if self.args.hourInterval:
            timeInterval = timedelta(hours=self.args.hourInterval)
        else:
            timeInterval = self.activityEndTime - self.activityStartTime
 
        if self.args.verbose:
            print "Making time interval plots for platform", self.args.platform
            print "Activity start:", self.activityStartTime
            print "Activity end:  ", self.activityEndTime
            print "Time Interval =", timeInterval

        # Pull out data and plot at timeInterval intervals
        startTime = self.activityStartTime
        endTime = startTime + timeInterval
        while endTime <= self.activityEndTime:
            x, y, points = self._getPPData(startTime, endTime, self.args.platform, self.args.xParm, self.args.yParm)
        
            if len(points) < 2:
                startTime = endTime
                endTime = startTime + timeInterval
                continue

            path = LineString(points).simplify(tolerance=.001)
        
            fig = plt.figure()
            plt.grid(True)
            ax = fig.add_subplot(111)
    
            # Scale path points to appear in upper right of the plot as a crude indication of the track
            xp = []
            yp = []
            for p in path:
                xp.append(0.30 * (p[0] - self.extent[0]) * (xmax - xmin) / (self.extent[2] - self.extent[0]) + 0.70 * (xmax - xmin))
                yp.append(0.18 * (p[1] - self.extent[1]) * (ymax - ymin) / (self.extent[3] - self.extent[1]) + 0.75 * (ymax - ymin))
       
            # Make the plot 
            ax.set_xlim(round_to_n(xmin, 1), round_to_n(xmax, 1))
            ax.set_ylim(round_to_n(ymin, 1), round_to_n(ymax, 1))
            ax.set_xlabel('%s (%s)' % (self.args.xParm, xUnits))
            ax.set_ylabel('%s (%s)' % (self.args.yParm, yUnits))
            ax.set_title('%s from %s' % (self.args.platform, self.args.database)) 
            ax.scatter(x, y, marker='.', s=10, c='k', lw = 0, clip_on=False)
            ax.plot(xp, yp, c=self.color)
            ax.text(0.1, 0.8, startTime.strftime('%Y-%m-%d %H:%M'), transform=ax.transAxes)
            fnTempl= '{platform}_{xParm}_{yParm}_{time}' 
            fileName = fnTempl.format(platform=self.args.platform, xParm=self.args.xParm, yParm=self.args.yParm, time=startTime.strftime('%Y%m%dT%H%M'))
            wcName = fnTempl.format(platform=self.args.platform, xParm=self.args.xParm, yParm=self.args.yParm, time=r'*')
            if self.args.daytime:
                fileName += '_day'
                wcName += '_day'
            if self.args.nighttime:
                fileName += '_night'
                wcName += '_night'
            fileName += '.png'

            fig.savefig(fileName)
            print 'Saved file', fileName
            plt.close()
    
            startTime = endTime
            endTime = startTime + timeInterval

        print 'Done. Make an animated gif with: convert -delay 100 {wcName}.png {gifName}.gif'.format(wcName=wcName, gifName='_'.join(fileName.split('_')[:3]))

    def makePlatformsBiPlots(self):
        '''
        Cycle through all the platforms & parameters (there will be more than one) and make the correlation plots
        for the interval as subplots on the same page.  Include a map overview and timeline such that if a movie 
        is made of the resulting images a nice story is told.  Layout of the plot page is like:

         D  +-------------------------------------------------------------------------------------------+
         e  |                                                                                           |
         p  |                                                                                           |
         t  |                                                                                           |
         h  +-------------------------------------------------------------------------------------------+
                                                        Time

            +---------------------------------------+           +-------------------+-------------------+
            |                                       |           |                   |                   |
            |                                       |         y |                   |                   |
         L  |                                       |         P |                   |                   |
         a  |                                       |         a |    Platform 0     |    Platform 1     |
         t  |                                       |         r |                   |                   |
         i  |                                       |         m |                   |                   |
         t  |                                       |           |                   |                   |
         u  |                                       |           +-------------------+-------------------+
         d  |                                       |           |                   |                   |
         e  |                                       |         y |                   |                   |
            |                                       |         P |                   |                   |
            |                                       |         a |    Platform 2     |    Platform 3     |
            |                                       |         r |                   |                   |
            |                                       |         m |                   |                   |
            |                                       |           |                   |                   |
            +---------------------------------------+           +-------------------+-------------------+
                           Longitude                                    xParm               xParm

        '''
        # Plot figure size in inches and nested subplot structure
        fig = plt.figure(figsize=(9, 6))
        outer_gs = gridspec.GridSpec(2, 1, height_ratios=[1,4])
        time_gs  = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer_gs[0])
        lower_gs = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=outer_gs[1])
        map_gs   = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=lower_gs[0])
        plat_gs  = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=lower_gs[1], wspace=0.0, hspace=0.0, width_ratios=[1,1], height_ratios=[1,1])
        ##plat_gs  = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=lower_gs[1], width_ratios=[1,1], height_ratios=[1,1])

        # Get overall temporal and spatial extents of platforms requested
        allActivityStartTime, allActivityEndTime, allExtent  = self._getActivityExtent(self.args.platform)

        # Setup the time windowing and stepping - if none specified then use the entire extent that is in the database
        if self.args.hourStep:
            timeStep = timedelta(hours=self.args.hourStep)
            if self.args.hourWindow:
                timeWindow = timedelta(hours=self.args.hourWindow)
            else:
                if self.args.hourStep:
                    timeWindow = timedelta(hours=self.args.hourStep)
        else:
            timeWindow = allActivityEndTime - allActivityStartTime
            timeStep = timeWindow
        startTime = allActivityStartTime
        endTime = startTime + timeWindow

        # Get overall temporal data for placement in the temporal subplot
        platformDTHash = self._getplatformDTHash(self.args.platform)
        swrTS = self._getTimeSeriesData(allActivityStartTime, allActivityEndTime, parameterStandardName='surface_downwelling_shortwave_flux_in_air')

        # Loop through sections of the data with temporal query constraints based on the window and step command line parameters
        while endTime <= allActivityEndTime:
 
            # Plot temporal overview
            ax = plt.Subplot(fig, time_gs[:])
            ax = self.timeSubPlot(platformDTHash, ax, startTime, endTime, swrTS)
            fig.add_subplot(ax)

            # Make scatter plots of data fromt the platforms 
            platformLineStringHash = {}
            for i, (pl, xP, yP) in enumerate(zip(self.args.platform, self.args.xParm, self.args.yParm)):
                try: 
                    x, y, points = self._getPPData(startTime, endTime, pl, xP, yP)
                    platformLineStringHash[pl] = LineString(points).simplify(tolerance=.001)
                except NoPPDataException, e:
                    if self.args.verbose: print e
                    continue

                ax = plt.Subplot(fig, plat_gs[i])
                ax = self.xySubPlot(x, y, pl, self._getColor(pl), xP, yP, ax, startTime)
                fig.add_subplot(ax, aspect='equal')

            # Plot spatial
            ax = plt.Subplot(fig, map_gs[:])
            ax = self.spatialSubPlot(platformLineStringHash, ax, allExtent)
            fig.add_subplot(ax)
           
            startTime = startTime + timeStep
            endTime = startTime + timeWindow

            fnTempl= 'platforms_{time}' 
            fileName = fnTempl.format(time=startTime.strftime('%Y%m%dT%H%M'))
            wcName = fnTempl.format(time=r'*')
            if self.args.daytime:
                fileName += '_day'
                wcName += '_day'
            if self.args.nighttime:
                fileName += '_night'
                wcName += '_night'
            fileName += '.png'

            plt.figtext(0.55, 0.0, '\\\n'.join(wrap(self.commandline)), size=7, verticalalignment='bottom')
            plt.tight_layout()
            plt.savefig(fileName)
            print 'Saved file', fileName

            plt.close()
            raw_input('P')

        print 'Done. Make an animated gif with: convert -delay 100 {wcName}.png {gifName}.gif'.format(wcName=wcName, gifName='_'.join(fileName.split('_')[:3]))

    def process_command_line(self):
        '''
        The argparse library is included in Python 2.7 and is an added package for STOQS.
        '''
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n\n' 
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado Slocum_294 tethys -x bbp420 optical_backscatter470nm bb470 -y fl700_uncorr fluorescence chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p tethys -x bb470 -y chlorophyll --hourStep 12 --hourWindow 24\n'
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p Slocum_294 -x optical_backscatter470nm -y fluorescence --hourStep 12 --hourWindow 24\n'
        examples += sys.argv[0] + ' -d stoqs_september2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p dorado -x bbp420 -y fl700_uncorr\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p daphne -x bb470 -y chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll --daytime\n'
        examples += sys.argv[0] + ' -d stoqs_march2013_o -p tethys -x bb470 -y chlorophyll --nighttime\n'
        examples += '\n\nMultiple platform and parameter names are paired up in respective order.\n'
        examples += '(Image files will be written to the current working directory)'
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                         description='Read Parameter-Parameter data from a STOQS database and make bi-plots',
                                         epilog=examples)
                                             
        parser.add_argument('-x', '--xParm', action='store', help='One or more Parameter names for the X axis', nargs='*', default='bb470', required=True)
        parser.add_argument('-y', '--yParm', action='store', help='One or more Parameter names for the Y axis', nargs='*', default='chlorophyll', required=True)
        parser.add_argument('-p', '--platform', action='store', help='One or more platform names separated by spaces', nargs='*', default='tethys', required=True)
        parser.add_argument('-d', '--database', action='store', help='Database alias', default='stoqs_september2013_o', required=True)
        parser.add_argument('--hourWindow', action='store', help='Window in hours for interval plot. If not specified it will be the same as hourStep.', type=int)
        parser.add_argument('--hourStep', action='store', help='Step though the time series and make plots at this hour interval', type=int)
        parser.add_argument('--daytime', action='store_true', help='Select only daytime hours: 10 am to 2 pm local time')
        parser.add_argument('--nighttime', action='store_true', help='Select only nighttime hours: 10 pm to 2 am local time')
        parser.add_argument('--minDepth', action='store', help='Minimum depth for data queries', default=None, type=float)
        parser.add_argument('--maxDepth', action='store', help='Maximum depth for data queries', default=None, type=float)
        parser.add_argument('-v', '--verbose', action='store_true', help='Turn on verbose output')
    
        self.args = parser.parse_args()
        self.commandline = ' '.join(sys.argv)
    
    
if __name__ == '__main__':

    bp = PlatformsBiPlot()
    bp.process_command_line()
    if len(bp.args.platform) > 0:
        bp.makePlatformsBiPlots()
    else:
        bp.makePlatformsBiPlots()
        ##bp.makeIntervalPlots()

