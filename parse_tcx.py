"""Some functions for parsing a TCX file (specifically, a TCX file
downloaded from Strava, which was generated based on data recorded by a
Garmin vívoactive 3) and creating a Pandas DataFrame with the data.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Union, Tuple

import lxml.etree
import pandas as pd
import dateutil.parser as dp


NAMESPACES = {
    'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
    'ns2': 'http://www.garmin.com/xmlschemas/UserProfile/v2',
    'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2',
    'ns4': 'http://www.garmin.com/xmlschemas/ProfileExtension/v1',
    'ns5': 'http://www.garmin.com/xmlschemas/ActivityGoals/v1'
}

# The names of the columns we will use in our points DataFrame
POINTS_COLUMN_NAMES = ['latitude', 'longitude', 'elevation', 'time', 'heart_rate', 'cadence', 'speed', 'lap']

# The names of the columns we will use in our laps DataFrame
LAPS_COLUMN_NAMES = ['number', 'start_time', 'distance', 'total_time', 'max_speed', 'max_hr', 'avg_hr']

def get_tcx_lap_data(lap: lxml.etree._Element) -> Dict[str, Union[float, datetime, timedelta, int]]:
    """Extract some data from an XML element representing a lap and
    return it as a dict.
    """
    
    data: Dict[str, Union[float, datetime, timedelta, int]] = {}
    
    # Note that because each element's attributes and text are returned as strings, we need to convert those strings
    # to the appropriate datatype (datetime, float, int, etc).
    
    start_time_str = lap.attrib['StartTime']
    data['start_time'] = dp.parse(start_time_str)
    
    distance_elem = lap.find('ns:DistanceMeters', NAMESPACES)
    if distance_elem is not None:
        data['distance'] = float(distance_elem.text)
    
    total_time_elem = lap.find('ns:TotalTimeSeconds', NAMESPACES)
    if total_time_elem is not None:
        data['total_time'] = timedelta(seconds=float(total_time_elem.text))
    
    max_speed_elem = lap.find('ns:MaximumSpeed', NAMESPACES)
    if max_speed_elem is not None:
        data['max_speed'] = float(max_speed_elem.text)
    
    max_hr_elem = lap.find('ns:MaximumHeartRateBpm', NAMESPACES)
    if max_hr_elem is not None:
        data['max_hr'] = float(max_hr_elem.find('ns:Value', NAMESPACES).text)
    
    avg_hr_elem = lap.find('ns:AverageHeartRateBpm', NAMESPACES)
    if avg_hr_elem is not None:
        data['avg_hr'] = float(avg_hr_elem.find('ns:Value', NAMESPACES).text)
    
    return data

def get_tcx_point_data(point: lxml.etree._Element) -> Optional[Dict[str, Union[float, int, str, datetime]]]:
    """Extract some data from an XML element representing a track point
    and return it as a dict.
    """
    
    data: Dict[str, Union[float, int, str, datetime]] = {}
    
    position = point.find('ns:Position', NAMESPACES)
    if position is None:
        # This Trackpoint element has no latitude or longitude data.
        # For simplicity's sake, we will ignore such points.
        return None
    else:
        data['latitude'] = float(position.find('ns:LatitudeDegrees', NAMESPACES).text)
        data['longitude'] = float(position.find('ns:LongitudeDegrees', NAMESPACES).text)
    
    time_str = point.find('ns:Time', NAMESPACES).text
    data['time'] = dp.parse(time_str)
        
    elevation_elem = point.find('ns:AltitudeMeters', NAMESPACES)
    if elevation_elem is not None:
        data['elevation'] = float(elevation_elem.text)
    
    hr_elem = point.find('ns:HeartRateBpm', NAMESPACES)
    if hr_elem is not None:
        data['heart_rate'] = int(hr_elem.find('ns:Value', NAMESPACES).text)
        
    cad_elem = point.find('ns:Cadence', NAMESPACES)
    if cad_elem is not None:
        data['cadence'] = int(cad_elem.text)
    
    # The ".//" here basically tells lxml to search recursively down the tree for the relevant tag, rather than just the
    # immediate child elements of speed_elem. See https://lxml.de/tutorial.html#elementpath
    speed_elem = point.find('.//ns3:Speed', NAMESPACES)
    if speed_elem is not None:
        data['speed'] = float(speed_elem.text)
    
    return data
    

def get_dataframes(fname: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Takes the path to a TCX file (as a string) and returns two Pandas
    DataFrames: one containing data about the laps, and one containing
    data about the individual points.
    """
    
    tree = lxml.etree.parse(fname)
    root = tree.getroot()
    activity = root.find('ns:Activities', NAMESPACES)[0]  # Assuming we know there is only one Activity in the TCX file
                                                          # (or we are only interested in the first one)
    points_data = []
    laps_data = []
    lap_no = 1
    for lap in activity.findall('ns:Lap', NAMESPACES):
        # Get data about the lap itself
        single_lap_data = get_tcx_lap_data(lap)
        single_lap_data['number'] = lap_no
        laps_data.append(single_lap_data)
        
        # Get data about the track points in the lap
        track = lap.find('ns:Track', NAMESPACES) 
        for point in track.findall('ns:Trackpoint', NAMESPACES):
            single_point_data = get_tcx_point_data(point)
            if single_point_data:
                single_point_data['lap'] = lap_no
                points_data.append(single_point_data)
        lap_no += 1
    
    # Create DataFrames from the data we have collected. If any information is missing from a particular lap or track
    # point, it will show up as a null value or "NaN" in the DataFrame.
    
    laps_df = pd.DataFrame(laps_data, columns=LAPS_COLUMN_NAMES)
    laps_df.set_index('number', inplace=True)
    points_df = pd.DataFrame(points_data, columns=POINTS_COLUMN_NAMES)
    
    return laps_df, points_df


if __name__ == '__main__':
    
    from sys import argv
    fname = argv[1]  # Path to TCX file to be given as first argument to script
    laps_df, points_df = get_dataframes(fname)
    print('LAPS:')
    print(laps_df)
    print('\nPOINTS:')
    print(points_df)
    

