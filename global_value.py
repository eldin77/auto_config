import os

nsx_port = 443
nax_ip = str() 
username = "admin"
password = "admin"

SWITCH_NAME = 'NAIM_SW_'
ROUTER_NAME = 'NAIM_ROUTER_'
TRANSPORT_ZONE = 'NAIM_TRANSPORT_ZONE_'
TRANSPORT_NODE = 'NAIM_TRANSPORT_NODE_'
GATEWAY = 'NAIM_HW_L2GW_'
GATEWAY_SERVICE = 'NAIM_HVTEP_'
LSWITCH_PORT = 'NAIM_LSWITCH_PORT_'
PATH = os.getcwd()+'/nsx_conf/'
CONF_PATH = os.getcwd() 
BACKUPCONF_PATH = os.getcwd()+'/configs'
NSX_API_VERSION = "ws.v2"

nsx_conf_names = ['lrouter.conf',
        'lswitch.conf',
        'transport_node.conf',
        'gateway_service.conf',
        'lrouter_port.conf',
        'lrouter_port_attatchment.conf',
        'lswitch_port.conf',
        'lswitch_port_attatchment.conf']

change_lswitch_uuid = {}
change_lswitch_port_uuid = {}
change_transport_node_uuid = {}
change_lrouter_uuid = {}
change_lrouter_port_uuid = {}
change_gateway_service_uuid = {}


