NSX auto config script
======================
###설명
NSX auto backup &amp; restore

### Dependency
```
NSX REST API version 1

python 2.7.3

sudo apt-get install python-pip

pip install colorama
```

### Excute Example
```
python auto_config_v_0_1.py

nsx_ip > 192.168.1.100

//nsx에 설정되어 있는 transport_zone_uuid 입력
transport_zone_uuid > 7308c889-ef2d-43db-80f0-f49226d7f86b

4. Backup Config
5. Restore
6. Clear
7. Reload Config.
H. Help
Q. Quit
Command : 

```

### help
```
1. Delete Lswitch: NSX Delete Logical Switch Delete                     command: 1, Delete
2. Create Lswitch: NSX Create Logical Switch, Port, Port ,attachment    command: 2, Create
4. Backup Config : NSX config backup.                                   command: 4, backup
5. Restore : NSX config restore. not implementation.                    command: 5, restore
6. Clear : all clear nsx config.                                        command: 6, clear
H. Help.                                                                command: H, help, h
Q. Quit.                                                                command: q, Q, quit
```


