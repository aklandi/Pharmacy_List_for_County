import pandas as pd             # to save file
from census import Census       # for FIPS information
from us import states           # for FIPS information
import osmnx as ox              # to get list of cities
import re      
import requests


def city_list_from_county(API_KEY: str, COUNTY_NAME: str, STATE_ABBR:str ):

    # Get the fips for state and county
    c = Census(API_KEY)

    # Get state fips code
    state_fips = states.lookup(STATE_ABBR).fips
    # Get county fips for that state
    counties = c.acs5.state_county(
        fields=("NAME",),
        state_fips=state_fips,
        county_fips="*"
    )

    # putting it together in a nice data frame
    Co = []
    for indx, county in enumerate(counties):
        C1 = county['NAME']
        C2 = county['county']
        C3 = county['state']
        Co.append([C1, C2, C3])

    county_fips = pd.DataFrame(Co, columns = ["Name", "county", "state"])

    # save county and state fips in separate variables for later use
    select_row = county_fips['Name'].str.contains(f'{COUNTY_NAME}', case=False, regex=True)
    select_stateFIPS = county_fips['state'][select_row]
    select_countyFips = county_fips['county'][select_row].array[0]


    # now use OpenStreet Maps to get list of cities within boundary of county
    place =  county_fips['Name'][select_row].array[0]
    area = ox.geocoder.geocode_to_gdf(place)

    tags = {'place': ['city', 'town', 'village', 'hamlet']}
    polygon = area.iloc[0]['geometry']
    cities = ox.features.features_from_polygon(polygon, tags)['name'].unique()

    #If the name is two or more words, separated by a space, then put a plus sign between each word - how the NPI registry stores cities with two or more words
    i = 0
    while i < len(cities):
            
        for elem in cities:

            if len(elem.split(" ")) > 1:

                temp = elem.split(" ")
                s = temp[0]
                
                for k in temp[1:]:

                    s = s + "+" + k

                cities[i] = s
                
                i+=1

            else:

                i+=1

    # put all cities and listed state in a data frame
    DF = pd.DataFrame({"city": cities, "state": [STATE_ABBR]*len(cities)})

    return DF


def city_list_from_county_fix(API_KEY: str, COUNTY_NAME: str, STATE_ABBR:str ):

    # rewrite to fix API JSON parsing error
    state_fips = states.lookup(STATE_ABBR).fips
    county_fips = get_counties(API_KEY, state_fips)
    county_fips = county_fips.rename(columns={"NAME": "Name"})


    # save county and state fips in separate variables for later use
    select_row = county_fips['Name'].str.contains(COUNTY_NAME, case=False, regex=False)

    if not select_row.any():

        raise ValueError(f"County '{COUNTY_NAME}' not found")

    place = county_fips.loc[select_row, 'Name'].iloc[0]


    # now use OpenStreet Maps to get list of cities within boundary of county
    area = ox.geocode_to_gdf(place)

    tags = {'place': ['city', 'town', 'village', 'hamlet']}

    polygon = area.geometry.iloc[0]

    cities = ox.features_from_polygon(polygon, tags)['name'].dropna().unique()

    #If the name is two or more words, separated by a space, then put a plus sign between each word - how the NPI registry stores cities with two or more words
    i = 0
    while i < len(cities):
            
        for elem in cities:

            if len(elem.split(" ")) > 1:

                temp = elem.split(" ")
                s = temp[0]
                
                for k in temp[1:]:

                    s = s + "+" + k

                cities[i] = s
                
                i+=1

            else:

                i+=1

    # put all cities and listed state in a data frame
    DF = pd.DataFrame({"city": cities, "state": [STATE_ABBR]*len(cities)})

    return DF


def get_counties(API_KEY, state_fips):

    url = (
        "https://api.census.gov/data/2020/acs/acs5"
        "?get=NAME"
        f"&for=county:*"
        f"&in=state:{state_fips}"
        f"&key={API_KEY}"
    )

    r = requests.get(url)
    data = r.json()

    return pd.DataFrame(data[1:], columns=data[0])