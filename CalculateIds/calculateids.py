# ------------------------------------------------------------------------------
# Name:        calculateids.py
# Purpose:     generates identifiers for features

# Copyright 2016 Esri

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# ------------------------------------------------------------------------------
from os import path
from datetime import datetime as dt
import arcpy
from arcresthelper import securityhandlerhelper
from arcrest.agol import FeatureLayer

# Data Store
server_type = "AGOL"  # "PORTAL", "SERVER"

# Credentials for AGOL/Portal
orgURL = 'http://localgovtest.maps.arcgis.com'
username = 'allison_demo'
password = 'lgdemo123'

# Services/feature classes to update
#   path: REST enpoint of AGOL/Portal service, or feature class path
#   field: Name of field to contain identifier
#   type: the name of the id value to use. This should correspond to the first value of a line in the ids.csv file
#   sequence: the identifier sequence, with the section to increment marked
#       with {}. Python string formatting applies within the {}. For example,
#       use {:04d}'to pad the incrementing value with 4 zeros.
data = [{'path': '',
         'field': '',
         'type': '',
         'sequence': ''},

         {'path': '',
         'field': '',
         'type': '',
         'sequence': ''}]

# Path to file use to track the identifiers
#   one identifier per line with the following comma separated values:
#       the name of the id value,
#       the interval to use to increment the values,
#       the id value that will be used for the next feature
id_file_path = r'C:\Users\alli6394\Documents\GitHub\crowdsource-reporter-scripts\CalculateIds\ids.csv'


def read_values(f):
    """Read in the settings from the csv file and
    return the same in list format"""

    with open(f, 'r') as f_open:
        f_content = f_open.read()
        f_lines = f_content.split('\n')
        f_values = [val.split(',') for val in f_lines if val]

    return f_values


def find_settings(cat, lst):
    """Return the setting specific to the current iteration"""
    found = False
    for val1, val2, val3 in lst:
        if val1 == cat:
            found = True

            try:
                return [val1, int(val2), int(val3)]

            except ValueError:
                found = False

    if not found:
        return ['error', '', '']


def update_agol(url, fld, sequence_value, interval, seq_format='{}'):
    """Update fetures in an agol/portal service with id values
    Return next valid sequence value"""

    # Connect to org
    securityinfo = {}
    securityinfo['security_type'] = 'Portal'  # LDAP, NTLM, OAuth, Portal, PKI, ArcGIS
    securityinfo['username'] = username
    securityinfo['password'] = password
    securityinfo['org_url'] = orgURL
    securityinfo['proxy_url'] = None
    securityinfo['proxy_port'] = None
    securityinfo['referer_url'] = None
    securityinfo['token_url'] = None
    securityinfo['certificatefile'] = None
    securityinfo['keyfile'] = None
    securityinfo['client_id'] = None
    securityinfo['secret_id'] = None

    shh = securityhandlerhelper.securityhandlerhelper(securityinfo=securityinfo)

    if not shh.valid:
        print shh.message

    fl = FeatureLayer(url=url,
                      securityHandler=shh.securityhandler,
                      proxy_port=None,
                      proxy_url=None,
                      initialize=True)

    # Build SQL query to find features missing id
    sql = """{} is null""".format(fld)

    out_fields = ['objectid', fld]

    # Get features without id
    resFeats = fl.query(where=sql, out_fields=','.join(out_fields))

    # For each feature
    for feat in resFeats:
        id_value = seq_format.format(sequence_value)

        # Update id
        feat.set_value(fld, id_value)

        # Increment sequence value
        sequence_value += interval

    print(fl.updateFeature(features=resFeats))

    return sequence_value


def update_fc(data_path, fld, sequence_value, interval, seq_format='{}'):
    """Update fetures in a server service with id values
    Return next valid sequence value"""

    # Get workspace of fc
    dirname = os.path.dirname(arcpy.Describe(data_path).catalogPath)
    desc = arcpy.Describe(dirname)
    if hasattr(desc, "datasetType") and desc.datasetType == 'FeatureDataset':
        dirname = os.path.dirname(dirname)

    # Start edit session
    edit = arcpy.da.Editor(dirname)
    edit.startEditing(False, True)
    edit.startOperation()

    # find and update all features that need ids
    sql = """{} is null""".format(fld)
    with arcpy.da.UpdateCursor(fc, fld, where_clause=sql) as fcrows:

        for row in fcrows:

            # Calculate a new id value from a string and the current id value
            row[0] = seq_format.format(sequence_value)

            fcrows.updateRow(row)

            # increment the sequence value by the specified interval
            sequence_value += interval_value

    return sequence_value


def main():

    id_log = path.join(sys.path[0], 'id_log.log')
    with open(id_log, 'a') as log:
        log.write('\n{}\n'.format(dt.now()))

        try:
            # Get all id settings
            id_settings = read_values(id_file_path)

            for d in data:
                data_path = d['path']
                id_field = d['field']
                inc_type = d['type']
                seq_format = d['sequence']

                # Get settings for current category
                id_type, interval, sequence_value = find_settings(inc_type,
                                                                  id_settings)

                if id_type == 'error':
                    raise Exception('Specified ID sequence not found')

                # Assign ids to features
                if server_type == 'AGOL' or server_type == 'PORTAL':
                    new_sequence_value = update_agol(data_path,
                                                     id_field,
                                                     sequence_value,
                                                     interval,
                                                     seq_format)

                elif server_type == 'SERVER':
                    new_sequence_value = update_fc(data_path,
                                                   id_field,
                                                   sequence_value,
                                                   interval,
                                                   seq_format)

                # Update the settings with the latest sequence values
                if sequence_value != new_sequence_value:
                    for val in id_settings:
                        if inc_type == val[0]:
                            val[2] = new_sequence_value
                            break

            # Save updated settings to file
            new_settings = ''
            for val in id_settings:
                new_settings += "{}\n".format(','.join(val))

            with open(id_file_path, 'w') as f:
                f.writelines(new_settings)

        except Exception as ex:
            print(ex)
            log.write('{}/n'.format(ex))

if __name__ == '__main__':
    main()
