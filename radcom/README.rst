python-ilorest-library
======================

Description
----------
The python-ilorest-library is a python library built remoting iLO 5.
Automatically connecting iLO by login with the redfish client. After connection it will alter and update the Bios Attributes.
It deleting an iLO Logical Drives, then it's creates a new logical drives.
If the Logical Drive has 2 Physical Disks, the raid will be Raid1. more than 2 Disks first two disks will be Raid1, the rest of disks will be Raid10.
For mounting virtual media for HPE iLO systems, the iso (media url) is uploaded by Dockerfile then it's starts a reboot server to iLo for updating.


pre-req:
pip install redfish

running
-------


Default connection with ilo is: febm-probe.ilo.ps.radcom.co.il

to run it with other serve do:
$ python radcom/radcom.py -i <new_URI> -u <new_USER> -p <new_PASS> -m <media_URL>

$ python radcom.py -m 172.29.169.106/CentOS-7-x86_64-Minimal-2009-KS-UEFI-GR.iso

another iLO server - (3) :
$ python radcom.py -i febm-prrootobe3.ilo.ps.radcom.co.il -u admin -p Radmin1234 -m 172.29.169.106/CentOS-7-x86_64-Minimal-2009-KS-UEFI-GR.iso

Running webserver:
docker run -d -p 80:80  -v <local_image_path>:/usr/local/apache2/htdocs httpd


flags
-----

'-i' - ilo address
'-u' - ilo user name
'-p' - ilo password
'-m' -  media url

