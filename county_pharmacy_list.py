import pandas as pd             
import numpy as np              # for nans
import geopy.geocoders as geoc  # for the geographical aspects
from rapidfuzz import fuzz      # for string analysis

# function needed to clean pharmacy addresses, pharmacy names, and rename groupings
from cleaning import clean_address, clean_name, pick_representative_name       
from NPI_assist import pull_from_NPI               # function needed to pull pharmacy info

# a function that will take a data frame of pharmacy names and addresses and returns the number of occurrences of the
# pharmacy organization in the data frame
#
# input: DF, a pandas dataframe with pharmacy names and addresses from a region
#        MATCH_threshold, a number between 0 and 100 that represents percent of similarity that is good enough
#        with_variants, a boolean that will determine whether the output will include details on groupings
#
# output: a data frame with pharmacy organization name and the count of occurrences in a region represented by DF
#
def county_pharmacy_list(DF: pd.DataFrame, MATCH_THRESHOLD: float, with_variants: True):

    # start with empty list that will eventually contain all pharmacies in a single county
    T_co = []

    for j in range(DF.shape[0]):

        # Select the j-th city and state
        city = DF["city"][j]
        state = DF["state"][0]

        try:

            # check if city has information in registry
            df2 = pull_from_NPI(city, state)

        except:

            # if not, move on
            continue

        # process the address data for city in registry: essentially only use organization name 
        
        temp = []
        no_good = []

        # if this variable exists for the city
        if 'basic.organization_name' in df2.columns:
            
            # i is index, other is elem in other_names, basic_name is elem in basic.org_name
            for i, (other, basic_name) in enumerate(zip(df2['other_names'], df2['basic.organization_name'])):
                
                name = None

                # check other_names.organization_name first, then check basic.organization_name
                
                # if the element is not empty and is a list
                if other and isinstance(other, list):
                    first = other[0]
                    # if the element is a dictionary, check if there is an organization name
                    if isinstance(first, dict) and 'organization_name' in first:
                        # if there is, use that as the name we extract
                        name = first['organization_name']
                
                # if the other_names variable doesn't have an org name, try basic.org_name
                if name is None and pd.notna(basic_name):
                    name = basic_name
                
                if name:
                    temp.append(name)
                # if there isn't a name in either variable, we have no choice but to make it empty
                else:
                    temp.append('NA')
                    no_good.append(i)
            
        # if that other variable doesn't exist, we'll try
        else:

            # i is index, other is elem in other_names, basic_name is elem in basic.org_name
            for i, other in enumerate(df2['other_names']):
                
                name = None
                
                # if the element is not empty and is a list
                if other and isinstance(other, list):
                    first = other[0]
                    # if the element is a dictionary, check if there is an organization name
                    if isinstance(first, dict) and 'organization_name' in first:
                        # if there is, use that as the name we extract
                        name = first['organization_name']
                
                if name:
                    temp.append(name)

                # if there isn't a name in either variable, we have no choice but to make it empty
                # and we keep track of those indexes for removal later
                else:
                    temp.append('NA')
                    no_good.append(i)

        # extract only the address info
        df3 = pd.DataFrame(df2['addresses'])
        # drop pharmacies that don't have the organization's name
        df3['name'] = temp
        df3 = df3.drop(no_good)
        # add location and mailing addresses as separate columns
        df3["AddressLocation"] = ""
        df3["AddressMailing"] = ""

        # separate 'other name' of pharmacy
        # clean up addresses+separate mailing and location
        for index, row in df3.iterrows():
                    
            # clean up address
            if df3["addresses"][index][0]["address_purpose"] == "LOCATION":
                LOC_address = df3["addresses"][index][0]
                MAIL_address =  df3["addresses"][index][1]
            elif df3["addresses"][index][1]["address_purpose"] == "LOCATION":
                LOC_address = df3["addresses"][index][1]
                MAIL_address =  df3["addresses"][index][0]
            
            # if not in state or city of choice, drop this entry
            if LOC_address["city"].casefold() != city.casefold():
                df3.drop(index)
            elif LOC_address["state"].casefold() != state.casefold():
                df3.drop(index)
            else:
                df3.loc[index, "AddressLocation"] = clean_address(LOC_address)
                df3.loc[index, "AddressMailing"] = clean_address(MAIL_address)

        # some cleaning of data
        del df3['addresses']
        # drop pharmacies at same location (they could share the same mailing address though)
        df3 = df3.drop_duplicates(subset = ['AddressLocation'])
        df3 = df3.reset_index(drop = True)

        T_co.append(df3)

    county_pharm = pd.concat(T_co, axis = 0)
    
    # now make that list unique
    
    # clean and format the pharmacy names for processing
    county_pharm['clean_name'] = county_pharm['name'].apply(clean_name)
    # start with each pharmacy as its own initial group
    county_pharm['company_group'] = county_pharm.index.astype(str)  # temporary company ID
    # group pharmacies by same location address
    mask = county_pharm['AddressLocation'].notna()
    county_pharm.loc[mask, 'company_group'] = (county_pharm[mask].groupby('AddressLocation')['company_group'].transform('first'))

    # group pharmacies by the same mailing address
    for mailing, group_ids in county_pharm[~county_pharm['AddressMailing'].isna()].groupby('AddressMailing')['company_group']:
        min_group = group_ids.min()
        county_pharm.loc[county_pharm['AddressMailing'] == mailing, 'company_group'] = min_group

    # group pharmacies by same name
    for name, group_ids in county_pharm[~county_pharm['clean_name'].isna()].groupby('clean_name')['company_group']:
        min_group = group_ids.min()
        county_pharm.loc[county_pharm['clean_name'] == name, 'company_group'] = min_group

    # build name dict for each group to apply to fuzzy matching
    group_to_names = (county_pharm.groupby('company_group')['clean_name'].apply(lambda x: set(x.dropna())).to_dict())

    # combine groups if one name from each group has a high fuzzy match, can adjust match threshold if needed
    merged = True
    while merged:
        merged = False
        groups = list(group_to_names.keys())
        for i, g1 in enumerate(groups):
            names1 = group_to_names[g1]
            for g2 in groups[i+1:]:
                names2 = group_to_names[g2]
                found_match = False
                for n1 in names1:
                    for n2 in names2:
                        score = fuzz.token_sort_ratio(n1, n2)
                        if score >= MATCH_THRESHOLD:
                            found_match = True
                            break
                    if found_match:
                        break
                if found_match:
                    county_pharm.loc[county_pharm['company_group'] == g2, 'company_group'] = g1
                    group_to_names[g1].update(group_to_names[g2])
                    group_to_names[g2] = set()
                    merged = True
                    break 
            if merged:
                break

    # assign company_name
    company_names = county_pharm.groupby('company_group')['clean_name'].apply(pick_representative_name)
    county_pharm['company_name'] = county_pharm['company_group'].map(company_names)
            
    # count unique AddressLocation per company
    location_counts = county_pharm.groupby('company_name')['AddressLocation'].nunique().sort_values(ascending=False)
    county_pharm['location_count'] = county_pharm['company_name'].map(location_counts) # add as a new column
    county_pharm = county_pharm.sort_values(by='location_count', ascending=False) # sort df by location count

    if with_variants == False:

        DF_unique_pharm_list = location_counts

    else:

        # summary with counts and name variants to confirm groupings
        DF_unique_pharm_list = county_pharm.groupby('company_name').agg(
            num_locations = ('AddressLocation', 'nunique'),  # unique locations only
            total_rows = ('clean_name', 'count'),           # total entries for this company
            name_variants = ('clean_name', lambda x: list(x.unique()))  # unique name variants
        ).sort_values(by='num_locations', ascending=False)


    return DF_unique_pharm_list