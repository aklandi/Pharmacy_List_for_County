import pandas as pd
import numpy as np
import urllib.request           # for retrieving data
import os                       # to clear up memory
import json                     # data type for NPI data

#
# Contributing Authors: Mariya Savinov, Leah Hoofstra 
#

#
# a function that gets a list of pharmacy information from location (city, state) given
#
# input: city, a string for city
#        state, a string with abbreviation for state
#
# output: df_pharm, a pandas data frame with the pharmacy information available
def pull_from_NPI(city, state):
    
    # You can only access maximum 200 at a time, so do multiple accesses
    completedata = 0
    downloadcount = 0

    # compiled download results
    myresults = []

    while completedata == 0:

        myURL = "https://npiregistry.cms.hhs.gov/api/?number=&enumeration_type=&taxonomy_description=Pharmacy&name_purpose=&first_name=&use_first_name_alias=&last_name=&organization_name=&address_purpose=&city="+city+"&state="+state+"&postal_code=&country_code=&limit=200&"+"skip="+str(downloadcount*200)+"&pretty=&version=2.1"
        download_file_name = city + state + "Data" + str(downloadcount);
        downloadcount += 1

        # download https file
        urllib.request.urlretrieve(myURL, download_file_name)

        # turn into dict files 
        with open(download_file_name) as json_file:
            data = json.load(json_file)
            
        # delete temporary file
        os.remove(download_file_name)
            
        myresults = myresults + data["results"];

        # cease data collection when results return emtpy
        if np.size(data["results"]) == 0:
            completedata = 1

    # construct into a pandas file
    reff = pd.json_normalize(myresults)
    df_pharm = pd.DataFrame(data = reff)

    if reff.empty:
        raise Exception('City not in database')
    else:

        return df_pharm