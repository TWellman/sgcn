
# coding: utf-8

# This process registeres unique species names from the SGCN source data into the Taxonomic Information Registry. The process is all based on pulling unique species names that are then examined via TIR processes to find matches with taxonomic authorities. Those decisions on taxonomic matching are used to create a nationally synthesized list of taxa that states have listed as Species of Greatest Conservation Need.
# 
# Registration consists of a set of key/value pairs that are inserted into the registration property of the TIR table. An hstore column in PostgreSQL of key/value pairs is used in order to accommodate different registration vectors having varying attributes. Every registration has the following:
# * source - Logical name specifying the source of the registration ("SGCN" in this case)
# * registrationDate - Date/time stamp of the registration
# 
# Most TIR registrations will have a "scientificname" property containing the name string used as a primary identifier. Some TIR registrations will have other identifiers that come from source material.
# 
# SGCN registrations include a list of common names and taxonomic groups supplied by the state and pulled together with an array_agg function and a DISTINCT operator to create a list of unique values in a string. These values can then be reasoned on in TIR processing. The code to register names in the TIR from the SGCN table could operate at any time there are new names showing up in the SGCN, but we might miss some of the aggregated common names when new state data is processed. To deal with this, we could set up a process to periodically check the SGCN records for new instances of a given name and reaggregate common names and taxonomic groups.

# In[42]:

import requests,datetime
from IPython.display import display
from bis import tir
from bis2 import gc2


# ### Get data to process
# 
# This script gathers all of the unique taxonomic names (scientificname_submitted) from the SGCN data and registers them with the Taxonomic Information Registry. The query checks to make sure the taxon name is not already registered in the TIR.

# In[43]:

q_sgcn = "SELECT scientificname_submitted scientificname,     array_to_string(array_agg(DISTINCT CASE WHEN commonname_submitted <> '' THEN commonname_submitted ELSE NULL END),',') commonnames,     array_to_string(array_agg(DISTINCT CASE WHEN sgcn_state <> '' THEN sgcn_state ELSE NULL END),',') sgcnstates,     array_to_string(array_agg(DISTINCT CASE WHEN taxonomicgroup_submitted <> '' THEN taxonomicgroup_submitted ELSE NULL END),',') taxonomicgroups     FROM sgcn.sgcn     WHERE scientificname_submitted NOT IN (        SELECT registration->'scientificname' AS scientificname_submitted         FROM tir.tir         WHERE registration->'Source' = 'SGCN'     )     GROUP BY scientificname_submitted"
r_sgcn = requests.get(gc2.sqlAPI("DataDistillery","BCB")+"&q="+q_sgcn).json()


# ### Iterate over the data and process to TIR
# 
# This block iterates over the unique species returned, packages up the data for the registration, and inserts them into the TIR table. It requires the following:
# 
# * TIR table set up in the appropriate GC2-basede data schema
# * Registration field in the TIR table using the hstore data type
# * gc2 module from the BIS2 package (connection info for the API)
# * tir module from the BIS package (function to insert registration info)

# In[44]:

recordCount = 0

for sgcn in r_sgcn['features']:
    recordInfoPairs = '"registrationDate" => "'+datetime.datetime.utcnow().isoformat()+'"'

    # Set source to indicate data coming from the SGCN system
    recordInfoPairs = recordInfoPairs+',"source"=>"SGCN"'

    # Set properties to configure taxonomic lookup rules
    recordInfoPairs = recordInfoPairs+',"taxonomicLookupProperty"=>"scientificname"'
    recordInfoPairs = recordInfoPairs+',"followTaxonomy"=>"true"'

    # Set the scientific name string - a common point of registration into the TIR (was formerly "SGCN_ScientificName_Submitted")
    recordInfoPairs = recordInfoPairs+',"scientificname"=>"'+sgcn['properties']['scientificname'].replace("\'","''")+'"'

    # Set a list of the unique common names that are associated with the scientific name
    recordInfoPairs = recordInfoPairs+',"commonnames"=>"'+sgcn['properties']['commonnames'].replace("\'","''")+'"'

    # Set a list of the unique taxonomic groups (something specific to the SGCN) that are associated with the scientific name
    recordInfoPairs = recordInfoPairs+',"taxonomicgroups"=>"'+sgcn['properties']['taxonomicgroups']+'"'

    # Set a list of the states that reported this scientific name
    recordInfoPairs = recordInfoPairs+',"sgcnstates"=>"'+sgcn['properties']['sgcnstates']+'"'

    try:
        print (sgcn['properties']['scientificname'], tir.tirRegistration(gc2.sqlAPI("DataDistillery","BCB"),recordInfoPairs))
        recordCount = recordCount + 1
    except Exception as e:
        print (e)

print ("Unique records processed: "+str(recordCount))


# ### Final Check
# 
# Check that the total number of SGCN registrations in the TIR match the total unique number of names in the SGCN table.

# In[41]:

q_uniqueSGCNNames = "SELECT COUNT(*) AS num FROM (SELECT DISTINCT scientificname_submitted FROM sgcn.sgcn) AS temp"
r_uniqueSGCNNames = requests.get(gc2.sqlAPI("DataDistillery","BCB")+"&q="+q_uniqueSGCNNames).json()
print ("Total number distinct SGCN scientific names: "+str(r_uniqueSGCNNames["features"][0]["properties"]["num"]))

q_tirRegisteredSGCNNames = "SELECT COUNT(*) AS num FROM tir.tir WHERE registration->'source' = 'SGCN'"
r_tirRegisteredSGCNNames = requests.get(gc2.sqlAPI("DataDistillery","BCB")+"&q="+q_tirRegisteredSGCNNames).json()
print ("Total number SGCN scientific names in TIR: "+str(r_tirRegisteredSGCNNames["features"][0]["properties"]["num"]))


# In[ ]:



