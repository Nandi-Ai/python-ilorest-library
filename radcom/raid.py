
import sys, json, random, string
from redfish import RedfishClient
from redfish.rest.v1 import ServerDownOrUnreachableError

from get_resource_directory import get_resource_directory


def get_logicalvolume_actions(volumeIds):
    params = {
        "LogicalDrives": [],
        "DataGuard": "Permissive"
    }
    for id in volumeIds:
        action = {
            "Actions": "[Action: LogicalDriveDelete]"
        }
        # item['VolumeUniqueIdentifier'] = id
        # params['LogicalDrives'].append(action)
    body = dict()
    body["LogicalDrives"] = dict()
    body["LogicalDrives"]["Actions"] = dict()
    body["LogicalDrives"]["Actions"]["Action"] = "LogicalDriveDelete"
    body["LogicalDrives"]["VolumeUniqueIdentifier"] = str(volumeIds[0])
    body["DataGuard"] = "Permissive"
 
    print(body)
    return body


def create_logicaldrive_json(size, locations):

    if len(locations) is 2:
        raid_type = 'Raid1'
    elif len(locations) > 3:
        raid_type = 'Raid5'
    elif len(locations) < 2:
        print("ERROR!")
    body = dict()
    body['CapacityGiB'] = 558
    body['Raid'] = raid_type
    body['StripSizeBytes'] = size
    source = string.ascii_letters + string.digits
    body['LogicalDriveName'] = 'My'+''.join((random.choice(source) for i in range(3)))
    body['DataDrives'] = list()
    for location in locations:
        body['DataDrives'].append(location)
    body['Accelerator'] = 'ControllerCache'

    print(json.dumps(body, indent=4))

#     resp = _redfishobj.put(smartstorage_uri_config, body)



def createLogicalDrive(_redfishobj):

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        #if we do not have a resource directory or want to force it's non use to find the
        #relevant URI

        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_members_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_members_response = _redfishobj.get(systems_members_uri)
        smart_storage_uri = systems_members_response.obj.Oem.Hpe.Links\
                                                                ['SmartStorage']['@odata.id']
        smart_storage_arraycontrollers_uri = _redfishobj.get(smart_storage_uri).obj.Links \
            ['ArrayControllers']['@odata.id']
        smartstorage_response = _redfishobj.get(smart_storage_arraycontrollers_uri).obj['Members']
    else:
        drive_locations = []
        totalStorage = 0
        for instance in resource_instances:
            #Use Resource directory to find the relevant URI
            if '#HpeSmartStorageArrayController.' in instance['@odata.type']:
                smartstorage_uri = instance['@odata.id']
                smartstorage_resp = _redfishobj.get(smartstorage_uri).obj
                sys.stdout.write("Logical Drive URIs for Smart Storage Array Controller " \
                    "'%s\' : \n" % smartstorage_resp.get('Id'))
                PysicalDrives_uri = smartstorage_resp.Links['PhysicalDrives']['@odata.id']
                Pysicaldrives_resp = _redfishobj.get(PysicalDrives_uri)
                if not Pysicaldrives_resp.dict['Members']:
                    sys.stderr.write("\tPysical drives are not available for this controller.\n")
                for drives in Pysicaldrives_resp.dict['Members']:
                    sys.stdout.write("\t An associated logical drive: %s\n" % drives)
                    drive_data = _redfishobj.get(drives['@odata.id']).dict
                    # drive_ids.append(drive_data["VolumeUniqueIdentifier"])
                    print(drive_data["Location"])
                    drive_locations.append(str(drive_data["Location"]))
                    totalStorage += drive_data["CapacityGB"]
                print(totalStorage)
                print(drive_locations)
                create_logicaldrive_json(totalStorage, drive_locations)
            elif '#SmartStorageConfig.' in instance['@odata.type']:
                   smartstorage_uri_config = instance['@odata.id']
                   # print(smartstorage_uri_config)
                   print("uri")





def change_temporary_boot_order(_redfishobj, boottarget):

    systems_members_uri = None
    systems_members_response = None

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_members_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_members_response = _redfishobj.get(systems_members_uri)
    else:
        for instance in resource_instances:
            if '#ComputerSystem.' in instance['@odata.type']:
                systems_members_uri = instance['@odata.id']
                systems_members_response = _redfishobj.get(systems_members_uri)

    if systems_members_response:
        print("\n\nShowing bios attributes before changes:\n\n")
        print(json.dumps(systems_members_response.dict.get('Boot'), indent=4, sort_keys=True))
    body = {'Boot': {'BootSourceOverrideTarget': boottarget}}
    resp = _redfishobj.patch(systems_members_uri, body)

    #If iLO responds with soemthing outside of 200 or 201 then lets check the iLO extended info
    #error message to see what went wrong
    if resp.status == 400:
        try:
            print(json.dumps(resp.obj['error']['@Message.ExtendedInfo'], indent=4, sort_keys=True))
        except Exception as excp:
            sys.stderr.write("A response error occurred, unable to access iLO Extended Message "\
                             "Info...")
    elif resp.status != 200:
        sys.stderr.write("An http response of \'%s\' was returned.\n" % resp.status)
    else:
        print("\nSuccess!\n")
        print(json.dumps(resp.dict, indent=4, sort_keys=True))
        if systems_members_response:
            print("\n\nShowing boot override target:\n\n")
            print(json.dumps(systems_members_response.dict.get('Boot'), indent=4, sort_keys=True))



def reboot_server(_redfishobj):

    systems_members_response = None

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        #if we do not have a resource directory or want to force it's non use to find the
        #relevant URI
        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
    else:
        for instance in resource_instances:
            #Use Resource directory to find the relevant URI
            if '#ComputerSystem.' in instance['@odata.type']:
                systems_uri = instance['@odata.id']
                systems_response = _redfishobj.get(systems_uri)

    if systems_response:
        system_reboot_uri = systems_response.obj['Actions']['#ComputerSystem.Reset']['target']
        body = dict()
        body['Action'] = 'ComputerSystem.Reset'
        body['ResetType'] = "ForceRestart"
        resp = _redfishobj.post(system_reboot_uri, body)
        #If iLO responds with soemthing outside of 200 or 201 then lets check the iLO extended info
        #error message to see what went wrong
        if resp.status == 400:
            try:
                print(json.dumps(resp.obj['error']['@Message.ExtendedInfo'], indent=4, \
                                                                                    sort_keys=True))
            except Exception as excp:
                sys.stderr.write("A response error occurred, unable to access iLO Extended "
                                 "Message Info...")
        elif resp.status != 200:
            sys.stderr.write("An http response of \'%s\' was returned.\n" % resp.status)
        else:
            print("Success!\n")
            print(json.dumps(resp.dict, indent=4, sort_keys=True))

def delete_SmartArray_LogicalDrives(_redfishobj):

    smartstorage_response = []
    smartarraycontrollers = dict()

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        #if we do not have a resource directory or want to force it's non use to find the
        #relevant URI

        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_members_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_members_response = _redfishobj.get(systems_members_uri)
        smart_storage_uri = systems_members_response.obj.Oem.Hpe.Links\
                                                                ['SmartStorage']['@odata.id']
        smart_storage_config_uri = systems_members_response.obj.Oem.Hpe.Links\
                                                                ['SmartStorageconfig']['@odata.id']
        print(smart_storage_config_uri)
        smart_storage_arraycontrollers_uri = _redfishobj.get(smart_storage_uri).obj.Links \
            ['ArrayControllers']['@odata.id']
        smartstorage_response = _redfishobj.get(smart_storage_arraycontrollers_uri).obj['Members']
    else:
        drive_ids = []
        for instance in resource_instances:
            #Use Resource directory to find the relevant URI
            if '#HpeSmartStorageArrayController.' in instance['@odata.type']:
                smartstorage_uri = instance['@odata.id']
                smartstorage_resp = _redfishobj.get(smartstorage_uri).obj
                sys.stdout.write("Logical Drive URIs for Smart Storage Array Controller " \
                    "'%s\' : \n" % smartstorage_resp.get('Id'))
                logicaldrives_uri = smartstorage_resp.Links['LogicalDrives']['@odata.id']
                logicaldrives_resp = _redfishobj.get(logicaldrives_uri)
                if not logicaldrives_resp.dict['Members']:
                    sys.stderr.write("\tLogical drives are not available for this controller.\n")
                for drives in logicaldrives_resp.dict['Members']:
                    sys.stdout.write("\t An associated logical drive: %s\n" % drives)
                    drive_data = _redfishobj.get(drives['@odata.id']).dict
                    drive_ids.append(drive_data["VolumeUniqueIdentifier"])
                    print(drive_data["VolumeUniqueIdentifier"])
            elif '#SmartStorageConfig.' in instance['@odata.type']:
                   smartstorage_uri_config = instance['@odata.id']
                   # print(smartstorage_uri_config)
                   print("uri")


    body = get_logicalvolume_actions(drive_ids)
    print(smartstorage_uri_config)
    print(body)
    # res = _redfishobj.put("https://febm-probe3.ilo.ps.radcom.co.il/redfish/v1/Systems/1/SmartStorageConfig/Settings/", )
    resp = _redfishobj.put(smartstorage_uri_config, body)
    print(resp)




def get_SmartArray_LogicalDrives(_redfishobj):

    smartstorage_response = []
    smartarraycontrollers = dict()

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        #if we do not have a resource directory or want to force it's non use to find the
        #relevant URI
        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_members_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_members_response = _redfishobj.get(systems_members_uri)
        smart_storage_uri = systems_members_response.obj.Oem.Hpe.Links\
                                                                ['SmartStorage']['@odata.id']
        smart_storage_arraycontrollers_uri = _redfishobj.get(smart_storage_uri).obj.Links\
                                                                ['ArrayControllers']['@odata.id']
        smartstorage_response = _redfishobj.get(smart_storage_arraycontrollers_uri).obj['Members']
    else:
        for instance in resource_instances:
            #Use Resource directory to find the relevant URI
            if '#HpeSmartStorageArrayController.' in instance['@odata.type']:
                smartstorage_uri = instance['@odata.id']
                smartstorage_resp = _redfishobj.get(smartstorage_uri).obj
                sys.stdout.write("Logical Drive URIs for Smart Storage Array Controller " \
                    "'%s\' : \n" % smartstorage_resp.get('Id'))
                logicaldrives_uri = smartstorage_resp.Links['LogicalDrives']['@odata.id']
                logicaldrives_resp = _redfishobj.get(logicaldrives_uri)
                if not logicaldrives_resp.dict['Members']:
                    sys.stderr.write("\tLogical drives are not available for this controller.\n")
                for drives in logicaldrives_resp.dict['Members']:
                    sys.stdout.write("\t An associated logical drive: %s\n" % drives)
                    drive_data = _redfishobj.get(drives['@odata.id']).dict
                    print(json.dumps(drive_data, indent=4, sort_keys=True))

def get_SmartArray_EncryptionSettings(_redfishobj, desired_properties):

    smartstorage_response = []
    smartarraycontrollers = dict()

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        #if we do not have a resource directory or want to force it's non use to find the
        #relevant URI
        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_members_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_members_response = _redfishobj.get(systems_members_uri)
        smart_storage_uri = systems_members_response.obj.Oem.Hpe.Links\
                                                                ['SmartStorage']['@odata.id']
        smart_storage_arraycontrollers_uri = _redfishobj.get(smart_storage_uri).obj.Links\
                                                                ['ArrayControllers']['@odata.id']
        smartstorage_response = _redfishobj.get(smart_storage_arraycontrollers_uri).obj['Members']
    else:
        for instance in resource_instances:
            #Use Resource directory to find the relevant URI
            if '#HpeSmartStorageArrayControllerCollection.' in instance['@odata.type']:
                smartstorage_uri = instance['@odata.id']
                smartstorage_response = _redfishobj.get(smartstorage_uri).obj['Members']
                break

    for controller in smartstorage_response:
        smartarraycontrollers[controller['@odata.id']] = _redfishobj.get(controller['@odata.id']).\
                                                                                                obj
        sys.stdout.write("Encryption Properties for Smart Storage Array Controller \'%s\' : \n" \
                                        % smartarraycontrollers[controller['@odata.id']].get('Id'))
        for data in smartarraycontrollers[controller['@odata.id']]:
            if data in desired_properties:
                sys.stdout.write("\t %s : %s\n" % (data, smartarraycontrollers[controller\
                                                                        ['@odata.id']].get(data)))

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

    # get_SmartArray_EncryptionSettings(REDFISHOBJ, DESIRED_PROPERTIES)
    # delete_SmartArray_LogicalDrives(REDFISHOBJ)
    createLogicalDrive(REDFISHOBJ)
    print("")
    ## reboot_server(REDFISHOBJ)


    REDFISHOBJ.logout()
