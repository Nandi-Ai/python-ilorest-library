
import sys, json, re, random, string
from redfish import RedfishClient
from redfish.rest.v1 import ServerDownOrUnreachableError

from get_resource_directory import get_resource_directory



# Assemble request body to delete logical volume
# 
# Args:
#       volumeIds (list<str>): logical volume unique identifiers
# Returns:
#       Request body, dictionary
#
def get_logicalvolume_actions(volumeIds):
    body = dict()
    body["LogicalDrives"] = dict()
    body["LogicalDrives"]["Actions"] = dict()
    body["LogicalDrives"]["Actions"]["Action"] = "LogicalDriveDelete"
    body["LogicalDrives"]["VolumeUniqueIdentifier"] = str(volumeIds[0])
    body["DataGuard"] = "Permissive"

    return body


# Assemble request body to create logical drive 
# 
# Args:
#       disks(list<dict): list of disks
# Returns:
#       Request body, dictionary
#
def create_logicaldrive_json(Disks):
    body = dict()
    body['DataDrives'] = list()
    numberOfDisks = len(Disks)
    diskSize = Disks[0]["CapacityGB"]
    for disk in Disks:
        body['DataDrives'].append(disk["Location"])
        if disk["CapacityGB"] <  diskSize:
            print("Smaller disk found")
            diskSize = disk["CapacityGB"]
    if numberOfDisks is 2:
        totalStorage = diskSize
        raid_type = 'Raid1'
    elif numberOfDisks > 3:
        totalStorage = numberOfDisks / 2 * diskSize
        raid_type = 'Raid10'
    elif len(Disks) < 2:
        print("ERROR!")

    body['CapacityGiB'] = totalStorage
    body['Raid'] = raid_type
    body['StripSizeBytes'] = 262144
    body['LogicalDriveName'] = 'RADCOM'+''.join((random.choice(string.digits) for i in range(5)))
    body['Accelerator'] = 'ControllerCache'

    print(json.dumps(body, indent=4))
    return body



# Creates logical drive 
# 
# Args:
#       _redfishobj(RedfishClient): redfish client object
# Returns:
#       Nothing
#
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
        drive_locations2 = []
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
                   # print(drive_data["Location"])
                    drive_locations2.append(str(drive_data["Location"]))
                    drive_locations.append(drive_data)
                # print(totalStorage)
                #print(drive_locations)

            elif '#SmartStorageConfig.' in instance['@odata.type']:
                   smartstorage_uri_config = instance['@odata.id']
                   print(smartstorage_uri_config)
                   # print("uri")
        if len(drive_locations) > 2:
            raid1_loc = drive_locations2[:2]
            create_logicaldrive_json(raid1_loc)
            raid10_loc = drive_locations2[2:]
            create_logicaldrive_json(raid10_loc)
            #print(raid1_loc)
            #print(raid10_loc)
        elif len(drive_locations) is 2:
            create_logicaldrive_json(drive_locations)
#           resp = _redfishobj.put(smartstorage_uri_config, body)
            #print(resp)
        else:
            print("error")


# Changes boot order
# 
# Args:
#       _redfishobj(RedfishClient): redfish client object
#       boottarget(str): temporary boot device
# Returns:
#       Nothing
#
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



# Reboots server
#
# Args:
#       _redfishobj(RedfishClient): redfish client object
# Returns:
#       Nothing
#
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


# Deletes logical drive
#
# Args:
#       _redfishobj(RedfishClient): redfish client object
# Returns:
#       HTTP status code
#
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
        #print(smart_storage_config_uri)
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
            #       print("uri")


    body = get_logicalvolume_actions(drive_ids)
    #print(smartstorage_uri_config)
    #print(body)
    # res = _redfishobj.put("https://febm-probe3.ilo.ps.radcom.co.il/redfish/v1/Systems/1/SmartStorageConfig/Settings/", )
    resp = _redfishobj.put(smartstorage_uri_config, body)
    return resp.status


# Gets logical drives
#
# Args:
#       _redfishobj(RedfishClient): redfish client object
# Returns:
#       Nothing
#
def get_SmartArray_Drives(_redfishobj):

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
                sys.stdout.write("Physical Drive URIs for Smart Storage Array Controller " \
                    "'%s\' : \n" % smartstorage_resp.get('Id'))
                physicaldrives_uri = smartstorage_resp.Links['PhysicalDrives']['@odata.id']
                logicaldrives_uri = smartstorage_resp.Links['LogicalDrives']['@odata.id']
                physicaldrives_resp = _redfishobj.get(physicaldrives_uri)
                logicaldrives_resp = _redfishobj.get(logicaldrives_uri)
                if not physicaldrives_resp.dict['Members']:
                    sys.stderr.write("\tPhysical drives are not available for this controller.\n")
                for drives in physicaldrives_resp.dict['Members']:
                    sys.stdout.write("\t An associated Physical drive: %s\n" % drives)
                    drive_data = _redfishobj.get(drives['@odata.id']).dict
                    print(json.dumps(drive_data, indent=4, sort_keys=True))
                    
                # WARNING    
                # commented, because I think it's mistake, function that lists drives
                # shouldn't delete them
                #  
                # if logicaldrives_resp.dict['Members']:
                #     sys.stderr.write("\tLogical drives are available for this controller.\nDeleting..")
                #     del_res = delete_SmartArray_LogicalDrives(REDFISHOBJ)
                #     if del_res == 200:
                #         print("success")
                #     else:
                #         print("fail, couldn't delete logical drives.")
                #         exit(1)


# Gets encryption settings for smart storage array controller 
#
# Args:
#       _redfishobj(RedfishClient): redfish client object
#       desired_properties(list<str>): properties for encryption settings
# Returns:
#       Nothing
#
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

    #list of desired properties related to Smart Array controller encryption#
#    DESIRED_PROPERTIES = ["Name", "Model", "SerialNumber", "EncryptionBootPasswordSet",\
#             "EncryptionCryptoOfficerPasswordSet",\
#             "EncryptionLocalKeyCacheEnabled", "EncryptionMixedVolumesEnabled",\
#             "EncryptionPhysicalDriveCount", "EncryptionRecoveryParamsSet",\
#             "EncryptionStandaloneModeEnabled", "EncryptionUserPasswordSet"]
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
    get_SmartArray_Drives(REDFISHOBJ)
    createLogicalDrive(REDFISHOBJ)
    # get_SmartArray_EncryptionSettings(REDFISHOBJ, DESIRED_PROPERTIES)
#    delete_SmartArray_LogicalDrives(REDFISHOBJ)
#    print("")
    reboot_server(REDFISHOBJ)


    REDFISHOBJ.logout()
