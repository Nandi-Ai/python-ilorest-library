python-ilorest-library
======================

Description
----------
The python-ilorest-library is a python library built remoting iLO 5.
Automatically connecting iLO by login with the redfish client. After connection it will alter update the Bios Attributes.
It deleting an iLO Logical Drives, then it's creates a new logical drives.
If the Logical Drive has 2 Physical Disks, the raid will be Raid1. more than 2 Disks first two disks will be Raid1, the rest of disks will be Raid10.
After creating a new Logical Drive, mounting virtual media for HPE iLO systems and makes a reboot server to iLo for updating.



installation
------------

$ mkdir /radcom

$ git clone git@github.com:Nandi-Ai/python-ilorest-library.git


running
-------

$ cd radcom

$ python radcom.py


Default connection with ilo is: febm-probe.ilo.ps.radcom.co.il

to run it with other serve do:
$ python radcom.py -i <new_URI> -u <new_USER> -p <new_PASS>

another iLO server - (3) :
$ python radcom.py -i febm-prrootobe3.ilo.ps.radcom.co.il -u admin -p Radmin1234



flags
-----

'-i' , '-u' , '-p'


