import re
import sys
import json
from redfish import RedfishClient
from redfish.rest.v1 import ServerDownOrUnreachableError

from get_resource_directory import get_resource_directory


def change_bios_setting(_redfishobj, bios_property, property_value):


    bios_uri = None
    bios_data = None
    global bios_res
    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        #if we do not have a resource directory or want to force it's non use to find the
        #relevant URI
        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_members_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_members_response = _redfishobj.get(systems_members_uri)
        bios_uri = systems_members_response.obj['Bios']['@odata.id']
        bios_data = _redfishobj.get(bios_uri)

    else:
        #Use Resource directory to find the relevant URI
        for instance in resource_instances:
            if '#Bios.' in instance['@odata.type']:
                bios_uri = instance['@odata.id']
                bios_data = _redfishobj.get(bios_uri)
                break
    bios_res = bios_data.obj
    if bios_data:
        print("\n\nShowing BIOS attributes before changes:\n\n")
        print(json.dumps(bios_data.dict, indent=4, sort_keys=True))

    if bios_uri:
        #BIOS settings URI is needed
        bios_settings_uri = bios_data.obj['@Redfish.Settings']['SettingsObject']['@odata.id']
        body = {'Attributes': {bios_property: property_value}}
        #update BIOS password
        if bios_property:
            _redfishobj.property_value = property_value
        resp = _redfishobj.patch(bios_settings_uri, body)

        #If iLO responds with soemthing outside of 200 or 201 then lets check the iLO extended info
        #error message to see what went wrong
        if resp.status == 400:
            try:
                print(json.dumps(resp.obj['error']['@Message.ExtendedInfo'], indent=4, \
                                                                                sort_keys=True))
            except Exception:
                sys.stderr.write("A response error occurred, unable to access iLO Extended "\
                                 "Message Info...")
        elif resp.status != 200:
            sys.stderr.write("An http response of \'%s\' was returned.\n" % resp.status)
        else:
            print("\nSuccess!\n")
            print("\n\nShowing BIOS attributes after changes:\n\n")
            print(json.dumps(resp.dict, indent=4, sort_keys=True))
            #uncomment if you would like to see the full list of attributes
            #print("\n\nShowing BIOS attributes after changes:\n\n")
            #bios_data = _redfishobj.get(bios_uri)
            #print(json.dumps(bios_data.dict, indent=4, sort_keys=True))


if __name__ == "__main__":
    # When running on the server locally use the following commented values
    #SYSTEM_URL = None
    #LOGIN_ACCOUNT = None
    #LOGIN_PASSWORD = None

    # When running remotely connect using the secured (https://) address,
    # account name, and password to send https requests
    # SYSTEM_URL acceptable examples:
    # "https://10.0.0.100"
    # "https://ilo.hostname"
    SYSTEM_URL = "https://febm-probe3.ilo.ps.radcom.co.il"
    LOGIN_ACCOUNT = "admin"
    LOGIN_PASSWORD = "Radmin1234"

    BIOS_PASSWORD = ""
    #provide the attribute name and the associated attribute value. Note: some, values may
    #be containers (arrays or dictionaries) so keep this in mind.
    #ATTRIBUTE = "AdminName"
    #ATTRIBUTE_VAL = "Luigi"

    # flag to force disable resource directory. Resource directory and associated operations are
    # intended for HPE servers.
    DISABLE_RESOURCE_DIR = False

    try:
        # Create a Redfish client object
        REDFISHOBJ = RedfishClient(base_url=SYSTEM_URL, username=LOGIN_ACCOUNT, \
                                                                            password=LOGIN_PASSWORD)
        # Login with the Redfish client
        REDFISHOBJ.login()
    except ServerDownOrUnreachableError as excp:
        sys.stderr.write("ERROR: server not reachable or does not support RedFish.\n")
        sys.exit()

    Att_bios = {'ExtendedMemTest': 'Disabled', 'InternalSDCardSlot': 'Disabled','AutoPowerOn': 'PowerOn' \
                , 'PostF1Prompt': 'Delayed20Sec', 'BootMode': 'LegacyBios', 'FlexLom1Enable': 'Auto', \
                'RedundantPowerSupply': 'HighEfficiencyAuto', 'PciSlot1Enable': 'HighEfficiencyAuto' \
                , 'EmbVideoConnection': 'AlwaysEnabled', 'ThermalConfig': 'IncreasedCooling'}



    AttributesElements = Att_bios.items()
    for ATTRIBUTE, ATTRIBUTE_VAL in AttributesElements:
        print("--------------------")
        print(ATTRIBUTE)
        print("--------------------")
        change_bios_setting(REDFISHOBJ, ATTRIBUTE, ATTRIBUTE_VAL)

    Nics = []
    for val, att in bios_res['Attributes'].items():
        if re.match(r'^Slot\dNic*', val):
            Nics.append(val)
    for nic in Nics:
        change_bios_setting(REDFISHOBJ, nic, "Disabled")



    REDFISHOBJ.logout()