import httplib
import urllib
import urlparse
import json
import hashlib
import os
import commands
import shutil
from array import *
from errno import *
from logo import *
from global_value import *
from make_body import *
from time import localtime, strftime

nsx_port_attach_type = {'VifAttachment':return_body,
			'PatchAttachment':return_patch_attachment_body,
                        'L3GatewayAttachment':return_l3_gateway_body,
                        'L2GatewayAttachment':return_l2_gateway_body}

class NSXApiHelper:
 
    def __init__(self):
        engine = create_engine(sql_connection)
        try:
            engine.connect()
            print "setp"
        except:
            print "Unable to connect to %s " % sql_connection

        self.db = SqlSoup(engine)
 

def nsx_login(username, password):
    session_cookie = None
    body = urllib.urlencode({"username": username, "password": password })
    headers = {"Content-Type":"application/x-www-form-urlencoded"}
    conn = httplib.HTTPSConnection(nsx_ip, nsx_port)
    conn.request("POST", "/"+NSX_API_VERSION+"/login", body, headers)
    response = conn.getresponse()
    if response.status in [httplib.OK]:
        cookies = response.getheader("Set-Cookie")
        session_cookie = filter(lambda x: x.find("nvp_sessionid")==0,
                                cookies.split(";"))[0]
    else:
        print "error: login failed, http response status: %s" % response.status
        print response.read()

    conn.close()
    return session_cookie

def nsx_create_lswitch(session_cookie, displayname, vxlan_id, transport_zone_uuid):
    headers = {"Cookie": session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)  

    body = {'display_name': displayname,
            'transport_zones':
                [{'zone_uuid': transport_zone_uuid,
		  'binding_config': 
		 	{'vxlan_transport': 
				[{'transport': vxlan_id}], 
		  	#'vlan_translation': 
                               # [{}]
                                }, 
                 'transport_type': 'vxlan'}],
            'replication_mode': 'service',
            'type': 'LogicalSwitchConfig'
            }
    
    print json.dumps(body) 
    conn.request("POST", "/"+NSX_API_VERSION+"/lswitch", json.dumps(body), headers)
    response = conn.getresponse()

    if response.status != 201:
        print "ERROR create network"
        print response.read()
        conn.close()
        #return None
        exit(1)
    else:
        response = json.loads(response.read())
       
    conn.close()
    return response['uuid']

def nsx_delete_send_message(session_cookie, tmp_url, uuid_list, end_count):
    for start_count in range(len(uuid_list)):
        headers = {'Cookie': session_cookie}
        conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
        url = tmp_url+str(uuid_list[start_count])
        conn.request("DELETE", url, None ,headers)
        
        response = conn.getresponse()
        print start_count,".",uuid_list[start_count],": ", response.status
        if response.status != 204:
            print "ERROR nsx_delete"
            print response.read()
            conn.close()
            exit(1)
        else:
            response = response.read()
        
        conn.close()
    return None
   
def nsx_delete_all_lswitchs(session_cookie):
    lswitch_uuid_list = []
    lswitch_response = nsx_show_lswitch_conf(session_cookie)
    lswitch_count = lswitch_response['result_count']
    print lswitch_count

    for x in range(lswitch_count):
        lswitch_uuid_list.append(lswitch_response['results'][x]['uuid'])
    
    tmp_url = '/'+NSX_API_VERSION+'/lswitch/'
    response = nsx_delete_send_message(session_cookie, tmp_url, lswitch_uuid_list, len(lswitch_uuid_list))
    return response

def nsx_delete_all_lrouters(session_cookie):
    lrouter_uuid_list = []
    lrouter_response = nsx_show_lrouter_conf(session_cookie)
    lrouter_count = lrouter_response['result_count']
    print lrouter_count

    for x in range(lrouter_count):
        lrouter_uuid_list.append(lrouter_response['results'][x]['uuid'])
    
    tmp_url = '/'+NSX_API_VERSION+'/lrouter/'
    response = nsx_delete_send_message(session_cookie, tmp_url, lrouter_uuid_list, len(lrouter_uuid_list))
    return response

def nsx_transport_node_delete_send_message(session_cookie, transport_node_uuid):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = '/'+NSX_API_VERSION+'/transport-node/'+str(transport_node_uuid)
    conn.request("DELETE", url, None ,headers)

    print url

    response = conn.getresponse()
    if response.status != 204:
        print "ERROR nsx_delete transport node"
        print response.read()
        conn.close()
        return None
    else:
        response = response.read()
        
    conn.close()
    return None

def nsx_gateway_service_delete_send_message(session_cookie, gateway_service_uuid):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = '/'+NSX_API_VERSION+'/gateway-service/'+str(gateway_service_uuid)
    conn.request("DELETE", url, None ,headers)

    print url

    response = conn.getresponse()
    if response.status != 204:
        print "ERROR nsx_delete_gateway service"
        print response.read()
        conn.close()
        return None
    else:
        response = response.read()
        
    conn.close()
    return None

def nsx_delete_all_gateway_service(session_cookie):
    def get_gateway_service_uuid(session_cookie, line):
        gateway_service_uuid_list = []
        gateway_service_uuid = json.loads(line)['uuid']
        nsx_gateway_service_delete_send_message(session_cookie, gateway_service_uuid)

    file_path = PATH+'gateway_service.conf'
    nsx_config_read(file_path, get_gateway_service_uuid, session_cookie)
    config_file_unlink('gateway_service.conf')

    return None

def nsx_delete_all_transport_node(session_cookie):
    def get_transport_node_uuid(session_cookie, line):
        transport_node_uuid_list = []
        transport_node_uuid = json.loads(line)['uuid']
        nsx_transport_node_delete_send_message(session_cookie, transport_node_uuid)

    file_path = PATH+'transport_node.conf'
    nsx_config_read(file_path, get_transport_node_uuid, session_cookie)
    config_file_unlink('transport_node.conf')
    return None

def nsx_create_range_lswitchs(session_cookie, transport_zone_uuid, port_count):
    port_id = {}
    gateway_service_list = {} 
    port_list = []
    port_list.append("VTEP-MLAG_PO1")
    port_list.append("VTEP-3_Eth11(ixia)")
    
    port_id[port_list[0]] = ("VXLAN_Mlag1") 
    port_id[port_list[1]] = ("Ethernet10") 
    
    switch_count = int(raw_input("switch_count :"))

    gws_response = nsx_show_gateway_service(session_cookie)
    for z in range(gws_response['result_count']):
        if (gws_response['results'][z]['display_name'] == port_list[0]) or (gws_response['results'][z]['display_name'] == port_list[1]):
           gateway_service_list[gws_response['results'][z]['display_name']] = gws_response['results'][z]['uuid']
    
    for x in range(switch_count):
        vxlan_id = x+2
        sname = SWITCH_NAME + str(vxlan_id)
        lswitch_uuid = nsx_create_lswitch(session_cookie, sname, vxlan_id, transport_zone_uuid)
        #if lswitch_uuid == None:
        #    continue
        for y in range(port_count):
            
            port_name = sname+"_"+port_list[y]
            lswitch_port_uuid = nsx_create_lswitch_port(session_cookie, 
                                                        port_name, 
                                                        lswitch_uuid, 
                                                        gateway_service_list[port_list[y]])

            lswitch_port_att_response = nsx_lswitch_port_attachment2(session_cookie,
                                                                    lswitch_uuid,
                                                                    lswitch_port_uuid,
                                                                    gateway_service_list[port_list[y]],
                                                                    port_id[port_list[y]],
                                                                    vxlan_id)
        
        print lswitch_uuid

def nsx_import_create_lswitch(session_cookie, body):
    headers = {"Cookie": session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)  
    
    before_lswitch_uuid = json.loads(body)['uuid']
    conn.request("POST", "/"+NSX_API_VERSION+"/lswitch", body, headers)
    response = conn.getresponse()
    print response.status
    if response.status != 201:
        print "ERROR Create Lswtich "
        print response.read()
        conn.close()
        return None 
    else:
        response = json.loads(response.read())

    conn.close()
    after_lswitch_uuid = response['uuid']
    change_lswitch_uuid[before_lswitch_uuid] = after_lswitch_uuid

    return response['uuid']

def nsx_show_lswitch_conf(session_cookie):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = '/'+NSX_API_VERSION+'/lswitch?_page_length=5000&fields=*'
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    print response.status
    if response.status != 200:
	print "ERROR load_lswitch_conf"
	print response.read()
        conn.close()
        return None
    else:
	response=json.loads(response.read())

    #return json.dumps(response['results'])
    conn.close()
    return response

def nsx_import_create_lrouter(session_cookie, body):
    headers = {"Cookie": session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port) 

    before_lrouter_uuid = json.loads(body)['uuid']

    tmp_body = json.loads(body)
    del tmp_body['uuid']

    conn.request("POST", "/"+NSX_API_VERSION+"/lrouter", json.dumps(tmp_body), headers)
    response = conn.getresponse()
    print body
    print response.status
    if response.status != 201:
        print "ERROR Create Lrouter "
        print response.read()
        conn.close()
        return None 
    else:
        response = json.loads(response.read())

    conn.close()
    after_lrouter_uuid = response['uuid']
    change_lrouter_uuid[before_lrouter_uuid] = after_lrouter_uuid

    return response['uuid']

def nsx_import_create_lrouter_port(session_cookie, body):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url_str = json.loads(body)
    url_list =  url_str['_href'].split("/")
    
    before_lrouter_uuid = url_list[3] 
    before_lrouter_port_uuid = url_list[5] 

    try :
        after_lrouter_uuid = change_lrouter_uuid[before_lrouter_uuid]
    except: 
        print "error: Import lrouter port error" 
        return None

    url = "/"+NSX_API_VERSION+"/lrouter/"+after_lrouter_uuid+"/lport"

    conn.request("POST", url, body, headers)
    response = conn.getresponse()

    if response.status != 201:
        print "ERROR lrouter port create network"
        print response.read()
        conn.close()
        return None
    else:
        response = json.loads(response.read())

    change_lrouter_port_uuid[before_lrouter_port_uuid] = response['uuid']
    conn.close()
    return response['uuid']

def nsx_import_create_lrouter_port_attachment(session_cookie, body):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)

    url_str = json.loads(body)
    url_list =  url_str['_href'].split("/")

    before_lrouter_uuid = url_list[3] 
    before_lrouter_port_uuid = url_list[5]

    temp = json.loads(body)
    print temp['type']
    t_body = nsx_port_attach_type[temp['type']](body)

    try:
        after_lrouter_uuid = change_lrouter_uuid[url_list[3]]
        after_lrouter_port_uuid = change_lrouter_port_uuid[url_list[5]]
    
    except:
        print "error: Import lrouter port attachmenet error" 
        return None

    url = "/"+NSX_API_VERSION+"/lrouter/"+after_lrouter_uuid+"/lport/"+after_lrouter_port_uuid+"/attachment" 
    conn.request("PUT", url, t_body, headers)
    response = conn.getresponse()

    print response.status
    if response.status != 200:
	    print "ERROR test load_lrouter_conf"
	    print response.read()
            conn.close()
	    return None 
    else:
	    response=json.loads(response.read())
    conn.close()
    return response

def nsx_create_lroute(session_cookie, displayname):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)  

    body = {'display_name': displayname,
            'tags':[],
            'type': 'LogicalSwitchConfig',
            'replication_mode': 'service',
            'type': 'LogicalRouterConfig'
            }
    print json.dumps(body) 
    conn.request("POST", "/"+NSX_API_VERSION+"/lroute", json.dumps(body), headers)
    response = conn.getresponse()

    if response.status != 201:
        print "ERROR create network"
        print response.read()
        conn.close()
        exit(1)
    else:
        response = json.loads(response.read())
        
    conn.close()
    return response['uuid']

def nsx_show_lrouter_port_attachement(session_cookie, lrouter_uuid, lport_uuid):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/lrouter/"+lrouter_uuid+"/lport/"+lport_uuid+"/attachment"
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    print response.status
    if response.status != 200:
	print "ERROR show lswitch port conf"
        print response.read()
        conn.close()
        return None	
    else:
	response = json.loads(response.read())

    conn.close()
    return response

def nsx_show_lrouter_port(session_cookie,lrouter_uuid):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/lrouter/"+lrouter_uuid+"/lport?_page_length=5000&fields=*" 
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    print response.status
    if response.status != 200:
	print "ERROR show lswitch port conf"
	#print response.read()
        conn.close()
	exit(1)
    else:
	response = json.loads(response.read())

    conn.close()
    return response

def nsx_show_lrouter_conf(session_cookie):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/lrouter?_page_length=5000&fields=*"
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    print response.status
    if response.status != 200:
	print "ERROR load lrouter conf"
	print response.read()
        conn.close()
        return None
    else:
	response = json.loads(response.read())
    
    conn.close()
    return response

def nsx_create_transport_zone(session_cookie, displayname):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)  

    body = {'display_name': displayname}
    print json.dumps(body) 
    conn.request("POST", "/"+NSX_API_VERSION+"/transport-zone", json.dumps(body), headers)
    response = conn.getresponse()

    if response.status != 201:
        print "ERROR create transport node"
        print response.read()
        conn.close()
        exit(1)
    else:
        response = json.loads(response.read())
        print "Okay create transport node"

    conn.close()
    return response['uuid']

def nsx_show_transport_zone_conf(session_cookie):
    headers = {'Cookie': session_cookie}
    transport_zone_uuid = '395ec839-8529-4fa0-b126-ce74336274a3' 
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/transport-zone/"+transport_zone_uuid 
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    print response.status
    if response.status != 200:
	print "ERROR show transport zone conf"
	print response.read()
        conn.close()
	exit(1)
    else:
	response = json.loads(response.read())

    conn.close()
    return response

def nsx_create_transport_node(session_cookie, displayname, transport_zone_uuid, ip_address, pem_encoded):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)  
    body = {'credential': {'type':'SecurityCertificateCredential',
	                   'client_certificate': {'pem_encoded':pem_encoded}},
	    'display_name': displayname,
	    'transport_connectors': [{'type': 'VXLANConnector',
				      'ip_address': ip_address[0],
				      '_schema': '/'+NSX_API_VERSION+'/schema/VXLANConnector',
				      'transport_zone_uuid': transport_zone_uuid},
                                     {'type': 'VXLANConnector',
				      'ip_address': ip_address[1],
				      '_schema': '/'+NSX_API_VERSION+'/schema/VXLANConnector',
				      'transport_zone_uuid': transport_zone_uuid},
                                     {'type': 'VXLANConnector',
				      'ip_address': ip_address[2],
				      '_schema': '/'+NSX_API_VERSION+'/schema/VXLANConnector',
				      'transport_zone_uuid': transport_zone_uuid}],
	    'integration_bridge_id': '',
	    'vtep_enabled' : True,
	    'zone_forwarding' : False,
	    'tags':[]}
    print json.dumps(body) 
    conn.request("POST", "/"+NSX_API_VERSION+"/transport-node", json.dumps(body), headers)
    response = conn.getresponse()

    if response.status != 201:
        print "ERROR create transport node"
        print response.read()
        conn.close()
        exit(1)
    else:
        response = json.loads(response.read())

    conn.close()
    return response['uuid']

def nsx_import_create_transport_node(session_cookie, body):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)  
    before_transport_node_uuid =  json.loads(body)['uuid'] 
    conn.request("POST", "/"+NSX_API_VERSION+"/transport-node", body, headers)
    response = conn.getresponse()

    if response.status != 201:
        print "ERROR create transport node"
        print response.read()
        conn.close()
        return None 
    else:
        response = json.loads(response.read())

    conn.close()
    change_transport_node_uuid[before_transport_node_uuid] = response['uuid']
    #print "before:",before_transport_node_uuid,"after:",change_transport_node_uuid[before_transport_node_uuid] 
    return response['uuid']

def nsx_show_transport_nodes(session_cookie):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/transport-node?_page_length=5000&fields=*"
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    #print response
    if response.status != 200:
	print "ERROR show transport node conf"
	print response.read()
        conn.close()
	exit(1)
    else:
	response = json.loads(response.read())
	#print response
    
    conn.close()
    return response

def nsx_show_gateway_service(session_cookie):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/gateway-service?_page_length=5000&fields=*"
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    print response.status
    if response.status != 200:
	print "ERROR show gateway service conf"
	print response.read()
        conn.close()
        return None 
    else:
	#print response.read()
	response = json.loads(response.read())
    
    conn.close()
    #return json.dumps(response['results'])
    return response

def nsx_create_gateway_service_body2(displayname, transport_node_uuid, set_interface_id, switch_name):
    body = {'display_name': displayname,
            'gateways': 
		     [{'type':'VtepL2Gateway',
		       'transport_node_uuid':transport_node_uuid,
		       'port_id': set_interface_id,
		       'switch_name': switch_name,
		     },
                      {'type':'VtepL2Gateway',
		       'transport_node_uuid':transport_node_uuid,
		       'port_id': set_interface_id,
		       'switch_name': 'VTEP-2',
		     },], 
	    'type': 'VtepL2GatewayServiceConfig'
	   }
    
    return body

def nsx_create_gateway_service_body(displayname, transport_node_uuid, set_interface_id, switch_name):
    body = {'display_name': displayname,
            'gateways': 
		     [{'type':'VtepL2Gateway',
		       'transport_node_uuid':transport_node_uuid,
		       'port_id': set_interface_id,
		       'switch_name': switch_name,
		     }], 
	    'type': 'VtepL2GatewayServiceConfig'
	   }
    
    return body

def nsx_create_gateway_service(session_cookie, displayname, transport_zone_uuid, transport_node_uuid, port_id, switch_name):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port) 
    if displayname == GATEWAY_SERVICE+'1':
        set_interface_id = port_id[1]
        body = nsx_create_gateway_service_body2(displayname, transport_node_uuid, set_interface_id, switch_name)
    else :
        set_interface_id = port_id[0]
        body = nsx_create_gateway_service_body(displayname, transport_node_uuid, set_interface_id, switch_name)

    """
    body = {'display_name': displayname,
	    'gateways': 
			[{'type':'VtepL2Gateway',
			  'transport_node_uuid':transport_node_uuid,
			  'port_id': port_id[0],
			}], 
            'type': 'VtepL2GatewayServiceConfig'
            }
    """  
    conn.request("POST", "/"+NSX_API_VERSION+"/gateway-service", json.dumps(body), headers)
    response = conn.getresponse()
    print response.status

    if response.status != 201:
        print "ERROR gateway-service create network"
        print response.read()
        conn.close()
        exit(1)
    else:
        response = json.loads(response.read())
    
    conn.close()
    return response['uuid']

def nsx_import_create_gateway_service(session_cookie, body):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    tmp_body = json.loads(body)
    
    gateway_count = len(tmp_body['gateways']) 

    for cnt in range(gateway_count):
        before_gateway_service_uuid = tmp_body['uuid']
        before_transport_node_uuid = tmp_body['gateways'][cnt]['transport_node_uuid']
        try:
            tmp_body['gateways'][cnt]['transport_node_uuid'] = change_transport_node_uuid[before_transport_node_uuid]
        except:
            print "ERROR import gateway service" 
            return None 

    body = json.dumps(tmp_body)
    conn.request("POST", "/"+NSX_API_VERSION+"/gateway-service", body, headers)
    response = conn.getresponse()
    print response.status

    if response.status != 201:
        print "ERROR gateway-service create network"
        print response.read()
        conn.close()
        return None
    else:
        response = json.loads(response.read())

    change_gateway_service_uuid[before_gateway_service_uuid] = response['uuid'] 
    conn.close()
    return response['uuid']

def nsx_show_lswitch_port(session_cookie,lswitch_uuid):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/lswitch/"+lswitch_uuid+"/lport?_page_length=5000&fields=*" 
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    print response.status
    if response.status != 200:
	print "ERROR show lswitch port conf"
	#print response.read()
        conn.close()
        return None
    else:
	response = json.loads(response.read())

    conn.close()
    return response

def nsx_show_lswitch_port_attachement(session_cookie, lswitch_uuid, lport_uuid):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/lswitch/"+lswitch_uuid+"/lport/"+lport_uuid+"/attachment"
    print url
    conn.request("GET", url,None ,headers)
    response = conn.getresponse()
    print response.status
    if response.status != 200:
	print "ERROR show lswitch port conf"
        print response.read()
        conn.close()
        return None	
    else:
	response = json.loads(response.read())

    conn.close()
    return response

def nsx_create_lswitch_port(session_cookie, displayname, lswitch_uuid, gateway_service_uuid):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)  
    body = {'display_name': displayname,
	    '_relations': {'LogicalPortAttachment':{'type': 'VtepL2GatewayAttachment',
						    'vtep_l2_gateway_service_uuid':gateway_service_uuid}},
            'type': 'LogicalSwitchPortConfig'
            }
    print body
    url = "/"+NSX_API_VERSION+"/lswitch/"+lswitch_uuid+"/lport"
    conn.request("POST", url, json.dumps(body), headers)
    response = conn.getresponse()

    if response.status != 201:
        print "ERROR lswitch port create network"
        print response.read()
        conn.close()
        exit(1)
    else:
        response = json.loads(response.read())

    conn.close()
    return response['uuid']

def nsx_import_create_lswitch_port(session_cookie, body):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url_str = json.loads(body)
    url_list =  url_str['_href'].split("/")

    before_lswitch_uuid = url_list[3] 
    before_lswitch_port_uuid = url_list[5] 

    try :
        after_lswitch_uuid = change_lswitch_uuid[before_lswitch_uuid]
    except: 
        print "error: Import lswitch port error" 
        return None

    url = "/"+NSX_API_VERSION+"/lswitch/"+after_lswitch_uuid+"/lport"

    conn.request("POST", url, body, headers)
    print body
    response = conn.getresponse()

    if response.status != 201:
        print "ERROR lswitch port create network"
        print response.read()
        conn.close()
        return None
    else:
        response = json.loads(response.read())

    change_lswitch_port_uuid[before_lswitch_port_uuid] = response['uuid']
    conn.close()
    return response['uuid']


def nsx_import_create_lswitch_port_attachment(session_cookie, body):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)

    url_str = json.loads(body)
    url_list =  url_str['_href'].split("/")

    before_lswitch_uuid = url_list[3] 
    before_lswitch_port_uuid = url_list[5]

    temp = json.loads(body)
    t_body = nsx_port_attach_type[temp['type']](body)

    try:
        after_lswitch_uuid = change_lswitch_uuid[before_lswitch_uuid]
        after_lswitch_port_uuid = change_lswitch_port_uuid[before_lswitch_port_uuid]
    except:
        print "error: Import lswitch port attachmenet error" 
        return None
    url = "/"+NSX_API_VERSION+"/lswitch/"+after_lswitch_uuid+"/lport/"+after_lswitch_port_uuid+"/attachment" 
    conn.request("PUT", url, t_body, headers)
    response = conn.getresponse()

    print response.status
    if response.status != 200:
	    print "ERROR test load_lswitch_conf"
	    print response.read()
            conn.close()
	    return None 
    else:
	    response=json.loads(response.read())
    conn.close()
    return response

def nsx_create_lswitch_port_attachment_body(set_interface_id, gateway_service_uuid, vlan_id):
    if set_interface_id == 'VXLAN_Mlag1': 
	body = {'type': 'VtepL2GatewayAttachment',
		'vtep_l2_gateway_service_uuid': gateway_service_uuid,
		'vlan_id': vlan_id,
	       }
    else :
	body = {'type': 'VtepL2GatewayAttachment',
		'vtep_l2_gateway_service_uuid': gateway_service_uuid,
		}
    return body

def nsx_create_lswitch_port_attachment_body2(set_interface_id, gateway_service_uuid, vlan_id):
    body = {'type': 'VtepL2GatewayAttachment',
            'vtep_l2_gateway_service_uuid': gateway_service_uuid,
            'vlan_id': vlan_id,
            }
    return body

def nsx_lswitch_port_attachment2(session_cookie, lswitch_uuid, lswitch_port_uuid, gateway_service_uuid, set_interface_id, vlan_id):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/lswitch/"+lswitch_uuid+"/lport/"+lswitch_port_uuid+"/attachment" 
    body = nsx_create_lswitch_port_attachment_body2(set_interface_id, gateway_service_uuid, vlan_id)
    conn.request("PUT", url, json.dumps(body) ,headers)
    response = conn.getresponse()

    print response.status
    if response.status != 200:
	    print "ERROR load_lswitch_conf"
	    print response.read()
            conn.close()
	    exit(1)
    else:
	    response=json.loads(response.read())
    
    conn.close()
    return response


def nsx_lswitch_port_attachment(session_cookie, lswitch_uuid, lswitch_port_uuid, gateway_service_uuid, set_interface_id, vlan_id):
    headers = {'Cookie': session_cookie}
    conn =  httplib.HTTPSConnection(nsx_ip, nsx_port)
    url = "/"+NSX_API_VERSION+"/lswitch/"+lswitch_uuid+"/lport/"+lswitch_port_uuid+"/attachment" 
    body = nsx_create_lswitch_port_attachment_body(set_interface_id, gateway_service_uuid, vlan_id)
    conn.request("PUT", url, json.dumps(body) ,headers)
    response = conn.getresponse()

    print response.status
    if response.status != 200:
	    print "ERROR load_lswitch_conf"
	    print response.read()
            conn.close()
	    exit(1)
    else:
	    response=json.loads(response.read())
    
    conn.close()
    return response

def mkdir_p(path):
    try:
        os.mkdir(path)
    except OSError as exc:
	if exc.errno == EEXIST and os.path.isdir(path):
            pass
	else: raise	

def nsx_config_write(nsx_conf_name, config_result):
    results = []
    if nsx_conf_name == 'lswitch_port_attatchment.conf':
        result = json.dumps(config_result)+'\n'
    
    elif nsx_conf_name == 'lrouter_port_attatchment.conf':
        result = json.dumps(config_result)+'\n'

    else:
        count =  config_result['result_count']
        #print json.dumps(config_result['results'])
        for x in range(count):
            #displayname = config_result['results'][x]['display_name']
            tmp_result = json.dumps(config_result['results'][x])
            results.append(tmp_result)
        result = '\n'.join(results)

    mkdir_p(PATH)
    file_path = PATH+nsx_conf_name
    
    if nsx_conf_name == 'lswitch_port_attatchment.conf' or nsx_conf_name == 'lrouter_port_attatchment.conf' : 
        f = file(file_path,'ab+')
    elif nsx_conf_name == 'lswitch_port.conf' or nsx_conf_name == 'lrouter_port.conf':
        file_size = int()
        try:
            file_size = os.path.getsize(file_path)
        except OSError as msg:
            print msg
        
        print file_size
        f = file(file_path,'ab+')
        if file_size != 0:
            f.write('\n')
    else :
        f = file(file_path,'wb+')

    f.write(result)
    f.close()

def config_file_unlinks(local_nsx_conf_names):
    for i in range(len(local_nsx_conf_names)):
        file_path = PATH+local_nsx_conf_names[i]
        try:
            os.unlink(file_path)
        except OSError as exc:
            #if exc.errno == EEXIST and os.path.isfile(file_path):
            pass
        #else: raise

def config_file_unlink(unlink_file_name):
    file_path = PATH+unlink_file_name
    try:
        os.unlink(file_path)
    except OSError as exc:
        print "unlink error"
        #if exc.errno == EEXIST and os.path.isfile(file_path):
        pass
        #else: raise

def nsx_config_read(file_path, func, session_cookie):
    try:
        f = open(file_path)
    except IOError as msg:
        print msg
        return None

    line = f.readline()
    while line:
        print line
        if(func != None):
            func(session_cookie, line)
        line = f.readline()

    return None

def nsx_config_read_and_import(file_path, func, session_cookie):
    try:
        f = open(file_path)
    except IOError as msg:
        print msg
        return None

    line = f.readline()
    while line:
        if(func == None):
            return None

        if line == '\n':
            print "line =>", line,"<=="

        try: 
            func(session_cookie, line)
        except:
            print "nsx_config_read_and_import err"
        line = f.readline()

    return None
    #return split_config

def kt_poc(session_cookie, transport_zone_uuid):
    #command = str()
    switch_name = []
    ip_address = ['10.16.11.11','10.16.11.13','10.0.0.14']
    commnad = 'cat cert/'+ip_address[2]
    pem_content = commands.getstatusoutput(commnad)
    #pem_encode.append(pem_content[1]) 
    pem_encode = pem_content[1] 

    print ip_address 
    print pem_encode

    port_id.append('Ethernet10')
    port_id.append('VXLAN_Mlag1')

    switch_name.append('VTEP-1')
    switch_name.append('VTEP-1')
    switch_name.append('VTEP-3')
    switch_name.append('VTEP-4')

    #localswitch create	
    #switch_count = 1 
    #for x in range(switch_count): 
    #vxlan_id = 5001+x
    sname = SWITCH_NAME+str(1)
    vxlan_id = 5001
    print "\t\t****Create Logical Switch****"
    lswitch_uuid = nsx_create_lswitch(session_cookie, sname, vxlan_id, transport_zone_uuid)

    print "\t\t****Create TransPort node****"
    #transport node gateway create(zone_forwarding = False) 
    #for tp_cnt in range(len(ip_address)):
    transport_node_uuid = nsx_create_transport_node(session_cookie, 
                        #GATEWAY+ip_address[tp_cnt], 
                        GATEWAY+str(1), 
                        transport_zone_uuid, 
                        #ip_address[tp_cnt],
                        ip_address,
                        pem_encode)
    #gateway service create
    print "\t\t****Create GateWay Service node****"
    for x in range(4):
        if x == 1:
            continue
        gw_displayname = GATEWAY_SERVICE+str(x+1)
        gateway_service_uuid = nsx_create_gateway_service(session_cookie, 
                            gw_displayname, 
                            transport_zone_uuid, 
                            transport_node_uuid,
                            port_id,
                            switch_name[x])

        #response = nsx_show_gateway_service_conf(session_cookie)
        switch_port_count = 1 
        print "\t\t****Create Logical Switch Port****"
        for sp_cnt in range(switch_port_count):
            lsw_displayname = LSWITCH_PORT+str(x+1)
            lswitch_port_uuid = nsx_create_lswitch_port(session_cookie, 
                                lsw_displayname, 
                                lswitch_uuid, 
                                gateway_service_uuid)
            print lswitch_port_uuid
            if gw_displayname == GATEWAY_SERVICE+str(1):
                set_interface_id = port_id[1] 
            else :
                set_interface_id = port_id[0] 

            vlan_id = 11
            port_attach_response = nsx_lswitch_port_attachment(session_cookie, 
                                lswitch_uuid, 
                                lswitch_port_uuid, 
                                gateway_service_uuid,
                                set_interface_id,
                                vlan_id)
            print port_attach_response

def lswitch_lrouter_port_setting(response, session_cookie, nsx_conf_member, port_name, port_attach_name):
    lcount = response['result_count'] 
    for sw_cnt in range(lcount):
        uuid = response['results'][sw_cnt]['uuid']
        ports_conf = nsx_conf_member[port_name](session_cookie, uuid)
        port_count = ports_conf['result_count']
               
        nsx_config_write(port_name, ports_conf)
        for port_count in range(ports_conf['result_count']):
            port_uuid = ports_conf['results'][port_count]['uuid']
            port_att_conf = nsx_conf_member[port_attach_name](session_cookie, uuid, port_uuid)
            nsx_config_write(port_attach_name, port_att_conf)

    return None

def backup_config_copy():
    file_name = strftime("%Y_%m_%d_%Hh_%Mm_%Ss", localtime())
    cp_command = 'cp -dRP '+PATH+' '+BACKUPCONF_PATH+'/'+file_name
    
    e = os.system(cp_command)
    print e
    return None

def backup_config(session_cookie, nsx_conf_member):
    config_file_unlinks(nsx_conf_names)
    
    for config_count in range(4):
        response = nsx_conf_member[nsx_conf_names[config_count]](session_cookie)
        nsx_config_write(nsx_conf_names[config_count], response)
        print nsx_conf_names[config_count] 
        if nsx_conf_names[config_count] == 'lswitch.conf':
            lswitch_lrouter_port_setting(response, 
                                         session_cookie, 
                                         nsx_conf_member, 
                                         'lswitch_port.conf',
                                         'lswitch_port_attatchment.conf')
        
        elif nsx_conf_names[config_count] == 'lrouter.conf':
            lswitch_lrouter_port_setting(response, 
                                         session_cookie, 
                                         nsx_conf_member, 
                                         'lrouter_port.conf',
                                         'lrouter_port_attatchment.conf')
    
    return None

def get_conf_files():
    config_files = []
    for root, dirs, files in os.walk("nsx_conf/", topdown=False):
	for name in files:
	    file_name = str((os.path.join(root, name)))
            print file_name
            config_files.append(file_name)
	for name in dirs:
	    print (os.path.join(root, name))

    return config_files

def reset_global_value():
    change_lswitch_uuid = None 
    change_lswitch_port_uuid = None 
    change_transport_node_uuid = None 
    change_lrouter_uuid = None 
    change_lrouter_port_uuid = None 
    change_gateway_service_uuid = None 


def restore_config(session_cookie, nsx_import_member):
    #config_file_list = get_conf_files()
    #file_count = len(config_file_list)

    # config_file_list sort need sort    
    for cnt in range(len(nsx_conf_names)):
        """
        file_path = CONF_PATH+config_file_list[cnt]
        func_name = config_file_list[cnt].split("nsx_conf/")
        """
        file_path = PATH+nsx_conf_names[cnt]
        func_name = nsx_conf_names[cnt] 
        func = nsx_import_member[func_name]
        nsx_config_read_and_import(file_path, func, session_cookie)

    reset_global_value()
    return None

def copy_config(path):
    print path
    cp_command = 'cp -dRP '+path+'/* '+PATH
    del_command = 'rm -rf '+PATH+'*'
    print cp_command
    print del_command
    e = os.system(del_command)
    e = os.system(cp_command)
    if e != 0:
        cp_command = 'cp -dRP '+path+'/ '+PATH
        os.system(cp_command)
    return None

def reload_config():
    config_dirs = []
    for root, dirs, files in os.walk(os.getcwd()+"/configs", topdown=True):
	for name in dirs:
	    file_dirs = str((os.path.join(root, name)))
            config_dirs.append(file_dirs)
	    #print (os.path.join(root, name))
   
    config_dirs.sort()
    dir_count = len(config_dirs)
    for x in range(dir_count):
        print x+1,".",config_dirs[x]
    
    command = raw_input("select > ")
    tmp_val = int(command)
    
    try:
        cp_config_path = config_dirs[tmp_val - 1]
    except IndexError as msg:
        print msg,"\nre setting plz"
        return None

    copy_config(cp_config_path)
    return None 

def all_clear_config(session_cookie, nsx_conf_member):
    backup_config(session_cookie, nsx_conf_member)
    nsx_delete_all_lswitchs(session_cookie)
    nsx_delete_all_lrouters(session_cookie)
    nsx_delete_all_gateway_service(session_cookie)
    nsx_delete_all_transport_node(session_cookie)
    return None

def main(args=None, prog=None):
    command = str()
    
    nsx_import_member = {}
    nsx_conf_member = {}
   
    nsx_import_funcs = [nsx_import_create_lrouter,
                        nsx_import_create_lswitch,
                        nsx_import_create_transport_node,
                        nsx_import_create_gateway_service,
                        nsx_import_create_lrouter_port,
                        nsx_import_create_lrouter_port_attachment,
                        nsx_import_create_lswitch_port,
                        nsx_import_create_lswitch_port_attachment]
    
    nsx_conf_funcs = [nsx_show_lrouter_conf,
                     nsx_show_lswitch_conf,
                     nsx_show_transport_nodes,
                     nsx_show_gateway_service,
                     nsx_show_lrouter_port,
                     nsx_show_lrouter_port_attachement,
                     nsx_show_lswitch_port,
                     nsx_show_lswitch_port_attachement]

    for conf_count in range(len(nsx_conf_names)):
        try:
            nsx_import_member[nsx_conf_names[conf_count]] = nsx_import_funcs[conf_count]
            nsx_conf_member[nsx_conf_names[conf_count]] = nsx_conf_funcs[conf_count]
        except:
            print "nsx_member insert error" 
            return
   
    session_cookie = nsx_login(username, password)
    #transport zone create
    #transport_zone_uuid = nsx_create_transport_zone(session_cookie, TRANSPORT_ZONE+'1')
    transport_zone_uuid = '7308c889-ef2d-43db-80f0-f49226d7f86b'


    while command != None:
        try: 
            command = raw_input("4. Backup Config\n5. Restore\n6. Clear\n7. Reload Config.\nH. Help\nQ. Quit\nCommand : ")
            if command == '1' or command == 'delete':
                nsx_delete_all_lswitchs(session_cookie)

            elif command == '2' or command == 'create':
                #session_cookie, transport_zone_uuid, portcount
                nsx_create_range_lswitchs(session_cookie, transport_zone_uuid, 2)            
            
            elif command == '4' or command == 'backup':
                backup_config(session_cookie, nsx_conf_member)
                backup_config_copy()
           
            elif command == '5' or command == 'restore':
                restore_config(session_cookie, nsx_import_member)

            elif command == '6' or command == 'clear':
                all_clear_config(session_cookie, nsx_conf_member)
                            
            elif command == '7' or command == 'reload':
                reload_config()

            elif command == 'h' or command == 'H' or command == 'help':
                print_help()

            elif command == 'Q' or command == 'q' or command == 'quit':
                print "bye bye~"
                break
            
            else :
                print "undefine commnad again input plz~~"
        
        except ValueError as msg:
            print msg
    
if __name__ == "__main__":
    main()
