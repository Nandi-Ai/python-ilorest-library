import sys
import json
from redfish import RedfishClient
from redfish.rest.v1 import ServerDownOrUnreachableError

from get_resource_directory import get_resource_directory


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


def get_SmartArray_LogicalDrives(_redfishobj):

    smartstorage_response = []
    smartarraycontrollers = dict()

    resource_instances = get_resource_directory(_redfishobj)
    if DISABLE_RESOURCE_DIR:
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
                    print()
                    print(json.dumps(drive_data, indent=4, sort_keys=True))
                    sys.stderr.write(logicaldrives_resp)





if __name__ == "__main__":

    SYSTEM_URL = "https://febm-probe3.ilo.ps.radcom.co.il"
    LOGIN_ACCOUNT = "admin"
    LOGIN_PASSWORD = "Radmin1234"


    try:
        # Create a Redfish client object
        REDFISHOBJ = RedfishClient(base_url=SYSTEM_URL, username=LOGIN_ACCOUNT, password=LOGIN_PASSWORD)
        # Login with the Redfish client
        REDFISHOBJ.login()
    except ServerDownOrUnreachableError as excp:
        sys.stderr.write("ERROR: server not reachable or does not support RedFish.\n")
        sys.exit()

    # Do a GET on a given path
    response = REDFISHOBJ.get("/redfish/v1/systems/1/smartstorageconfig/Settings/")
    # Print out the response
    sys.stdout.write("%s\n" % response)


    DISABLE_RESOURCE_DIR = True

    get_SmartArray_EncryptionSettings(REDFISHOBJ, response)
    print(get_SmartArray_EncryptionSettings)

    get_SmartArray_LogicalDrives(REDFISHOBJ)
    print(get_SmartArray_LogicalDrives)

    REDFISHOBJ.logout()


