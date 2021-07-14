import argparse, time
import sys, json, re, random, string
from redfish import RedfishClient
from redfish.rest.v1 import ServerDownOrUnreachableError

from get_resource_directory import get_resource_directory


def mount_virtual_media_iso(_redfishobj, iso_url, media_type, boot_on_next_server_reset):
# mounting virtual media for HPE iLO systems
    virtual_media_uri = None
    virtual_media_response = []

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        #if we do not have a resource directory or want to force it's non use to find the
        #relevant URI
        managers_uri = _redfishobj.root.obj['Managers']['@odata.id']
        managers_response = _redfishobj.get(managers_uri)
        managers_members_uri = next(iter(managers_response.obj['Members']))['@odata.id']
        managers_members_response = _redfishobj.get(managers_members_uri)
        virtual_media_uri = managers_members_response.obj['VirtualMedia']['@odata.id']
    else:
        for instance in resource_instances:
            #Use Resource directory to find the relevant URI
            if '#VirtualMediaCollection.' in instance['@odata.type']:
                virtual_media_uri = instance['@odata.id']

    if virtual_media_uri:
        virtual_media_response = _redfishobj.get(virtual_media_uri)
        for virtual_media_slot in virtual_media_response.obj['Members']:
            data = _redfishobj.get(virtual_media_slot['@odata.id'])
            if media_type in data.dict['MediaTypes']:
                # i'm not sure that i do it correctly
                virtual_media_mount_uri = data.obj['Actions']['#VirtualMedia.InsertMedia']['target']
                virtual_media_eject_uri = data.obj['Actions']['#VirtualMedia.EjectMedia']['target']
                post_body = {"Image": iso_url}
                if iso_url:
                    # power_off_server(_redfishobj)
                    eject = _redfishobj.post(virtual_media_eject_uri, {})
                    print('eject status: {}'.format(eject.status))
                    print('Mounting virtual media...')
                    resp = _redfishobj.post(virtual_media_mount_uri, post_body)
                    print('insert status: {}'.format(resp.status))
                    if boot_on_next_server_reset is not None:
                        patch_body = {}
                        patch_body["Oem"] = {"Hpe": {"BootOnNextServerReset": \
                                                         boot_on_next_server_reset}}
                        print('Setting BootOnNextServerReset...')
                        boot_resp = _redfishobj.patch(data.obj['@odata.id'], patch_body)
                        if not boot_resp.status == 200:
                            sys.stderr.write("Failure setting BootOnNextServerReset")
                    if resp.status == 400:
                        try:
                            print(json.dumps(resp.obj['error']['@Message.ExtendedInfo'], indent=4, \
                                                                                    sort_keys=True))
                        except Exception as excp:
                            print(json.dumps(resp.obj['error']['@Message.ExtendedInfo'], indent=4, \
                                             sort_keys=True))
                            sys.stderr.write("A response error occurred, unable to access iLO"
                                             "Extended Message Info...")
                    elif resp.status != 200:
                        sys.stderr.write("An http response of \'%s\' was returned.\n" % resp.status)
                    else:
                        print("Success!\n")
                        # print(json.dumps(resp.dict, indent=4, sort_keys=True))
                    # if boot_on_next_server_reset is not None:
                    #     patch_body = {}
                    #     patch_body["Oem"] = {"Hpe": {"BootOnNextServerReset": \
                    #                                      boot_on_next_server_reset}}
                    #     print(patch_body)
                    #     boot_resp = _redfishobj.patch(data.obj['@odata.id'], patch_body)
                    #     if not boot_resp.status == 200:
                    #         sys.stderr.write("Failure setting BootOnNextServerReset\n")
                    #         print(boot_resp.status)
                    #         print(json.dumps(boot_resp.obj['error']['@Message.ExtendedInfo'], indent=4, \
                    #                          sort_keys=True))
                break


def change_bios_setting(_redfishobj, bios_property, property_value):
    #change bios properties in the action settings
    #Alter one ore more BIOS attributes
    bios_uri = None
    bios_data = None
    global bios_res
    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_u = None
        systems_members_response = systems_path(systems_u)
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
    if bios_uri:
        #BIOS settings URI is needed
        bios_settings_uri = bios_data.obj['@Redfish.Settings']['SettingsObject']['@odata.id']
        body = {'Attributes': {bios_property: property_value}}
        #update BIOS password
        if bios_property:
            _redfishobj.property_value = property_value
        resp = _redfishobj.patch(bios_settings_uri, body)
        print('Setting {} to {}'.format(bios_property, property_value))
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

def check_response(resp,_redfishobj):
    if resp.obj['error']:
        error_msg = (json.dumps(resp.obj['error']['@Message.ExtendedInfo'][0].get("MessageId"), indent=4,
                                sort_keys=True))
        if 'SystemResetRequired' in error_msg:
            print("Restarting server!")
            reboot_server(_redfishobj)
        elif 'Success' in error_msg:
            print("Success")
        else:
            print("Other reponse on error")
    else:
        print ("Didn't find error")

def get_logicalvolume_actions(volumeIds):
    #getting the logical volumes
    body = dict()
    body["LogicalDrives"] = dict()
    body["LogicalDrives"]["Actions"] = dict()
    body["LogicalDrives"]["Actions"]["Action"] = "LogicalDriveDelete"
    body["LogicalDrives"]["VolumeUniqueIdentifier"] = str(volumeIds)
    body["DataGuard"] = "Disabled"
 
    # print(body)
    print(json.dumps(body, indent=4, sort_keys=True))
    return body

def create_logicaldrive_json(Disks):
    # creating logical drive disks with sorting the disks for which raid
    logicalDrive = dict()
    logicalDrive['DataDrives'] = list()
    numberOfDisks = len(Disks)
    diskSize = int(Disks[0]["CapacityGB"])
    for disk in Disks:
        logicalDrive['DataDrives'].append(disk["Location"])
        if int(disk["CapacityGB"]) <  diskSize:
            print("Smaller disk found")
            diskSize = int(disk["CapacityGB"])
    if numberOfDisks == 2:
        totalStorage = diskSize
        raid_type = 'Raid1'
    elif numberOfDisks > 3:
        totalStorage = (numberOfDisks / 2) * diskSize
        raid_type = 'Raid10'
    elif len(Disks) < 2:
        print("ERROR!")

    logicalDrive['CapacityGiB'] = int(totalStorage * 0.9)
    logicalDrive['Raid'] = raid_type
    # logicalDrive['StripSizeBytes'] = 262144
    logicalDrive['LogicalDriveName'] = 'RADCOM'+''.join((random.choice(string.digits) for i in range(5)))
    logicalDrive['Accelerator'] = 'ControllerCache'

    # print(json.dumps(logicalDrive, indent=4))
    #resp = _redfishobj.put(smartstorage_uri_config, body)

    return logicalDrive

def create_logicaldrive_body(disks):
    # creating logical drive disks with sorting the disks for which raid
    body = dict()
    logicalDrive = dict()
    body['DataGuard'] = "Permissive"
    body["LogicalDrives"] = list()
    if len(disks) > 2:
        raid1_loc = disks[:2]
        body["LogicalDrives"].append(create_logicaldrive_json(raid1_loc))
        raid10_loc = disks[2:]
        body["LogicalDrives"].append(create_logicaldrive_json(raid10_loc))
    elif len(disks) == 2:
        body["LogicalDrives"].append(create_logicaldrive_json(disks))
    print(json.dumps(body, indent=4))

    return body


def createLogicalDrive(_redfishobj):
    # Creates a new logical drive on the selected controller

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_u = None
        systems_members_response = systems_path(systems_u)
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
                # sys.stdout.write("Logical Drive URIs for Smart Storage Array Controller " \
                  #  "'%s\' : \n" % smartstorage_resp.get('Id'))
                PysicalDrives_uri = str(smartstorage_resp.Links['PhysicalDrives']['@odata.id'])
                print(PysicalDrives_uri)
                Pysicaldrives_resp = _redfishobj.get(PysicalDrives_uri)
                if not Pysicaldrives_resp.dict['Members']:
                    sys.stderr.write("\tPysical drives are not available for this controller.\n")
                for drives in Pysicaldrives_resp.dict['Members']:
                    sys.stdout.write("\t An associated logical drive: %s\n" % drives)
                    drive_data = _redfishobj.get(drives['@odata.id']).dict
                    # drive_ids.append(drive_data["VolumeUniqueIdentifier"])
                   # print(drive_data["Location"])
                    drive_locations.append(drive_data)
                # print(totalStorage)
                #print(drive_locations)

            elif '#SmartStorageConfig.' in instance['@odata.type']:
               smartstorage_uri_config = instance['@odata.id']
               print(smartstorage_uri_config)
               # print("uri")
        body = create_logicaldrive_body(drive_locations)
        resp = _redfishobj.put(smartstorage_uri_config, body)
        check_response(resp,_redfishobj)

def change_temporary_boot_order(_redfishobj, boottarget):
    #getting response boot - Alter the temporary boot order

    systems_members_uri = None
    systems_members_response = None

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_u = None
        systems_members_response = systems_path(systems_u)
    else:
        for instance in resource_instances:
            if '#ComputerSystem.' in instance['@odata.type']:
                systems_members_uri = instance['@odata.id']
                systems_members_response = _redfishobj.get(systems_members_uri)

    if systems_members_response:
        print("\n\nShowing bios attributes before changes:\n\n")
        #print(json.dumps(systems_members_response.dict.get('Boot'), indent=4, sort_keys=True))
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
        #print(json.dumps(resp.dict, indent=4, sort_keys=True))
        if systems_members_response:
            print("\n\nShowing boot override target:\n\n")
            print(json.dumps(systems_members_response.dict.get('Boot'), indent=4, sort_keys=True))

def power_off_server(_redfishobj):
    systems_members_response = None
    print("POWERING OFF THE SERVER")
    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_u = None
        systems_members_response = systems_path(systems_u)
    else:
        print('went in else')
        for instance in resource_instances:
            # Use Resource directory to find the relevant URI
            if '#HpeComputerSystemExt.' in instance['@odata.type']:
                print('went inside if')
                systems_uri = instance['@odata.id']
                systems_members_response = _redfishobj.get(systems_uri)
                print(systems_members_response)

    if systems_members_response:
        system_reboot_uri = systems_members_response.obj['Actions']['#HpeComputerSystemExt.PowerButton']['target']
        print(system_reboot_uri)
        body = dict()
        body['Action'] = 'HpeComputerSystemExt.PowerButton'
        body['PushType'] = "Press"
        resp = _redfishobj.post(system_reboot_uri, body)
        print('server power off')
        print(resp.status)

        # If iLO responds with soemthing outside of 200 or 201 then lets check the iLO extended info
        # error message to see what went wrong
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



def reboot_server(_redfishobj):
    # Reboot a server

    systems_members_response = None

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_u = None
        systems_members_response = systems_path(systems_u)
    else:
        for instance in resource_instances:
            #Use Resource directory to find the relevant URI
            if '#ComputerSystem.' in instance['@odata.type']:
                systems_uri = instance['@odata.id']
                systems_members_response = _redfishobj.get(systems_uri)

    if systems_members_response:
        system_reboot_uri = systems_members_response.obj['Actions']['#ComputerSystem.Reset']['target']
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
            time.sleep(25)



def delete_SmartArray_LogicalDrives(_redfishobj):
    #deleting an iLO logical drives
    deleteAlljson = {
        "LogicalDrives": [],
        "DataGuard": "Disabled"
    }
    smartstorage_response = []
    smartarraycontrollers = dict()

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_u = None
        systems_members_response = systems_path(systems_u)
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
                logicaldrives_uri = str(smartstorage_resp.Links['LogicalDrives']['@odata.id'])
                logicaldrives_resp = _redfishobj.get(logicaldrives_uri)
                if not logicaldrives_resp.dict['Members']:
                    sys.stderr.write("\tLogical drives are not available for this controller.\n")
                    return()
                for drives in logicaldrives_resp.dict['Members']:
                    sys.stdout.write("\t An associated logical drive: %s\n" % drives)
                    drive_data = _redfishobj.get(drives['@odata.id']).dict
                    drive_ids.append(str(drive_data["VolumeUniqueIdentifier"]))
                    print(drive_data["VolumeUniqueIdentifier"])
            elif '#SmartStorageConfig.' in instance['@odata.type']:
                smartstorage_uri_config = instance['@odata.id']
                # print("uri")
                # print(smartstorage_uri_config)

    body = get_logicalvolume_actions(drive_ids)
    #print(smartstorage_uri_config)
    # print(body)
    # res = _redfishobj.put("https://febm-probe3.ilo.ps.radcom.co.il/redfish/v1/Systems/1/SmartStorageConfig/Settings/", )
    resp = _redfishobj.put(smartstorage_uri_config, deleteAlljson)
    check_response(resp,_redfishobj)

    return resp.status




def get_SmartArray_Drives(_redfishobj):
    #List all logical drives associated with a smart array controller

    smartstorage_response = []
    smartarraycontrollers = dict()

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        systems_u = None
        systems_members_response = systems_path(systems_u)
        smart_storage_uri = systems_members_response.obj.Oem.Hpe.Links\
                                                                ['SmartStorage']['@odata.id']
        smart_storage_arraycontrollers_uri = _redfishobj.get(smart_storage_uri).obj.Links\
                                                                ['ArrayControllers']['@odata.id']
        smartstorage_response = _redfishobj.get(smart_storage_arraycontrollers_uri).obj['Members']
        print(smartstorage_response)
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
                    #print(json.dumps(drive_data, indent=4, sort_keys=True))
                if logicaldrives_resp.dict['Members']:
                    for logicalDrive in logicaldrives_resp.dict['Members']:
                        print("Found Logical drive:")
                        drive_data = _redfishobj.get(logicalDrive['@odata.id']).dict
                        print(json.dumps(drive_data, indent=4, sort_keys=True))
                else:
                    print ("Couldn't find logical drives")

def systems_path(_redfishobj):
    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR or not resource_instances:
        #if we do not have a resource directory or want to force it's non use to find the
        #relevant URI
        systems_uri = _redfishobj.root.obj['Systems']['@odata.id']
        systems_response = _redfishobj.get(systems_uri)
        systems_members_uri = next(iter(systems_response.obj['Members']))['@odata.id']
        systems_members_response = _redfishobj.get(systems_members_uri)

        return (systems_members_response)


def get_SmartArray_EncryptionSettings(_redfishobj, desired_properties):
    #Obtain Smart Array controller encryption property data

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


    BOOT_ON_NEXT_SERVER_RESET = True

    parser = argparse.ArgumentParser(description = "Script to upload and flash NVMe FW")

    parser.add_argument('-i','--ilo',dest='ilo_address',action="store",help="iLO IP address or FQDN",default="febm-probe.ilo.ps.radcom.co.il")
    parser.add_argument('-u','--user',dest='ilo_user',action="store",help="iLO username to login",default="admin")
    parser.add_argument('-p','--password',dest='ilo_pass',action="store",help="iLO password to log in.",default="Radmin1234")
    parser.add_argument('-m','--uri',dest='media_url',action="store",help="HTTP Server URI",default="http://172.29.169.106/CentOS-7-x86_64-Minimal-2009-KS-UEFI-GR.iso")
    parser.add_argument('-o','--os',dest='os',help="OS install only",action='store_true')
    parser.add_argument('-d','--drives',dest='logical_drives',action="store_true",help="Get Logical Drives olny")

    args = parser.parse_args()
    system_url = "https://" + args.ilo_address

    #specify the type of content the media represents
    MEDIA_TYPE = "CD" #current possible options: Floppy, USBStick, CD, DVD

    DISABLE_RESOURCE_DIR = False

    try:
        # Create a Redfish client object
        REDFISHOBJ = RedfishClient(base_url=system_url, username=args.ilo_user, password=args.ilo_pass)
        # Login with the Redfish client
        REDFISHOBJ.login()
    except ServerDownOrUnreachableError as excp:
        sys.stderr.write("ERROR: server not reachable or does not support RedFish.\n")
        sys.exit()
    Att_bios = {'ExtendedMemTest': 'Disabled', 'InternalSDCardSlot': 'Disabled','AutoPowerOn': 'PowerOn' \
                , 'PostF1Prompt': 'Delayed20Sec', 'BootMode': 'Uefi', 'FlexLom1Enable': 'Auto', \
                'RedundantPowerSupply': 'HighEfficiencyAuto', 'PciSlot1Enable': 'HighEfficiencyAuto' \
                , 'EmbVideoConnection': 'AlwaysEnabled', 'ThermalConfig': 'IncreasedCooling'}

    AttributesElements = Att_bios.items()
    for ATTRIBUTE, ATTRIBUTE_VAL in AttributesElements:
        # print("--------------------")
        # print(ATTRIBUTE)
        # print("--------------------")
        change_bios_setting(REDFISHOBJ, ATTRIBUTE, ATTRIBUTE_VAL)

    # Disable PXE to all NICS on board
    Nics = []
    for val, att in bios_res['Attributes'].items():
        if re.match(r'^Slot\dNic*', val):
            Nics.append(val)
    for nic in Nics:
        change_bios_setting(REDFISHOBJ, nic, "Disabled")

    if args.os:
        mount_virtual_media_iso(REDFISHOBJ, args.media_url, MEDIA_TYPE, BOOT_ON_NEXT_SERVER_RESET)
        REDFISHOBJ.logout()
        sys.exit()

    if args.logical_drives:
        get_SmartArray_Drives(REDFISHOBJ)
        REDFISHOBJ.logout()
        sys.exit()

    # get_SmartArray_Drives(REDFISHOBJ)
    # delete_SmartArray_LogicalDrives(REDFISHOBJ)
    # createLogicalDrive(REDFISHOBJ)
    # get_SmartArray_EncryptionSettings(REDFISHOBJ, DESIRED_PROPERTIES)
    reboot_server(REDFISHOBJ)
    mount_virtual_media_iso(REDFISHOBJ, args.media_url, MEDIA_TYPE, BOOT_ON_NEXT_SERVER_RESET)



    REDFISHOBJ.logout()
