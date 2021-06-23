
import sys, json
from redfish import RedfishClient
from redfish.rest.v1 import ServerDownOrUnreachableError

from get_resource_directory import get_resource_directory





def get_SmartArray_LogicalDrives(_redfishobj):

    smartstorage_response = []
    smartarraycontrollers = dict()

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_members_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_members_response = _redfishobj.get(systems_members_uri)
        bios_uri = systems_members_response.obj.Oem.Hpe.Links\
                                                                ['Bios']
        smartstorage_response = _redfishobj.get(bios_uri).obj['Members']
    else:
        for instance in resource_instances:
            if '#Bios.' in instance['@odata.type']:
                bios_uri = instance['@odata.id']
                bios_resp = _redfishobj.get(bios_uri).obj
                #print(json.dumps(bios_resp['Attributes'], indent=4, sort_keys=True))

                AttributesElements = {'ExtendedMemTest': 'Disabled', 'InternalSDCardSlot': 'Disabled',
                                      'AutoPowerOn': 'PowerOn' \
                                    , 'PostF1Prompt': 'Delayed20Sec', 'BootMode': 'LegacyBios', 'FlexLom1Enable': 'Auto', \
                                      'RedundantPowerSupply': 'HighEfficiencyAuto',
                                      'PciSlot1Enable': 'HighEfficiencyAuto' \
                                    , 'EmbVideoConnection': 'AlwaysEnabled', 'ThermalConfig': 'IncreasedCooling'}

                # body = {'Attributes': {bios_property: property_value}}
                y = bios_resp['Attributes'].items()
                x = AttributesElements.items()
                # res = [y[key] for key in AttributesElements]
                for attribute, val in y:
                    # print(str(attribute), str(val))
                    for attribute2, val2 in x:
                        if (attribute == attribute2) and (val == val2):
                            print(str(attribute), str(val))
                        elif (attribute == attribute2) and (val != val2):
                            _redfishobj.val = val2
                            print(str(attribute), str(val))



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

    #list of desired properties related to Smart Array controller encryption
    DESIRED_PROPERTIES = ["Name", "Model", "SerialNumber", "EncryptionBootPasswordSet",\
             "EncryptionCryptoOfficerPasswordSet",\
             "EncryptionLocalKeyCacheEnabled", "EncryptionMixedVolumesEnabled",\
             "EncryptionPhysicalDriveCount", "EncryptionRecoveryParamsSet",\
             "EncryptionStandaloneModeEnabled", "EncryptionUserPasswordSet"]
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


    get_SmartArray_LogicalDrives(REDFISHOBJ)
    print("")
    ## reboot_server(REDFISHOBJ)


    REDFISHOBJ.logout()
