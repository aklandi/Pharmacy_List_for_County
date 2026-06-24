import re
import pandas as pd
from rapidfuzz import fuzz

#
# Contributing Authors: Amanda Landi, Addie Duncan (primary)
#


# a function designed to clean an address from the NIP Registry
#
# input: my_address, which is a string
#
# output: a cleaned address that can be used to find lats and longs
#
def clean_address(my_address):
    # need to clean up first part of address if it includes anything beyond street location
    my_street = my_address["address_1"];
    
    cutoff_options = [" STE "," RM "," UNIT "," FL "," APT "," STE. ", " #"];
    
    for cutoff in cutoff_options:
        cutoff_index = my_street.find(cutoff);
        if cutoff_index != -1:
            my_street = my_street[:cutoff_index];
    
    # combined address as a string
    combined_address = my_street +", "+  my_address["city"] +", "+ my_address["state"]+ " "+ my_address["postal_code"][0:5];

    return combined_address

# function for cleaning the pharmacy names so they are easier to match
#
# input: name, the current name of a pharmacy
#
# output: a name for a pharmacy that has been standardized
#
def clean_name(name):

    name = name.lower().strip() # make lower case
    name = re.sub(r'[^\w\s]','',name) # strip punctuation
    name = re.sub(r'\s*\d+$', '', name) # remove trailing numbers (like store numbers)

    GENERIC_WORDS = [
    "pharmacy", "drugstore", "clinic", "health", "medical",
    "hospital", "wellness", "center", "centre", "store", "outlet", "community",
    "road", "rd", "ave", "street", "st", "lane", "ln",
    "unit", "suite", "super", "express", "plus", "market", "corner"]

    name = ' '.join([w for w in name.split() if w not in GENERIC_WORDS and len(w) > 2]) # remove generic words
    name = name.strip() # remove extra spaces

    return name


# function to pick representative company name (most common name in group)
#
# input: names, a pandas dataframe that contains pharmacy names, grouped by similarity in name
#
# output: changes all names in group to the same name for counting
#
def pick_representative_name(names):
    counts = names.value_counts() # counts number of names in the group

    # if there are no names in the group, then just give them a blank 
    if len(counts) == 0:
        return ""
    
    # whichever name appears the most
    max_count = counts.max()
    # give that name to everyone in group
    most_common = counts[counts == max_count].index
    
    return most_common[0]

def is_valid(x):
    return pd.notna(x) and str(x).strip() != "" and str(x).strip().upper() != "NA"




