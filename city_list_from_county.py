import pandas as pd             # to save file
from census import Census       # for FIPS information
from us import states           # for FIPS information
import osmnx as ox              # to get list of cities
import re      
import requests    

#
# Main Authors: Amanda Landi, Addie Duncan 
#

# function that gets a list of counties within a particular state using open street maps
#
# input: API_KEY, a string containing the OSM api access key
#        state_fips, the FIPS code from the acs/us census
#
# output: a data frame with a list of the counties in a state
#
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


# function that returns a list of cities from a county name in the US
#
# input: API_KEY, a string containing the OSM api access key
#        COUNTY_NAME, a string containing the FULL county name
#        STATE_ABBR, a string with the corresponding state's abbraviated name
#
# output: a dataframe containing the list of cities within the given county, state
#
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

    tags = {'place': ['city', 'town', 'village', 'hamlet', 'locality']}
    polygon = area.iloc[0]['geometry']

    # for places like the Bronx that is both a county and a city
    try:
        cities = ox.features.features_from_polygon(polygon, tags)['name'].unique()
    
    # there needs to be an alternative way
    except:

        print("That is a county, but has no listed cities, towns, villages, hamlets, localities, boroughs within it.")

    check_file = pd.read_csv('exceptions.csv', header = 0)
    for indx, elem in enumerate(check_file['COUNTY']):
        if elem == COUNTY_NAME:
            cities = check_file['GIVEN_NAME'][indx]
        else:
            continue

        DF = pd.DataFrame(
        {
            "city": cities, 
            "state": [STATE_ABBR]
        }
        )

        return DF
    
    else:

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

    