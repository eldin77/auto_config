import json
from global_value import * 

def return_patch_attachment_body(body):
    url_str = json.loads(body)
    url_list = url_str['peer_port_href'].split("/")

    url_list[3] = change_lrouter_uuid[url_list[3]] 
    url_list[5] = change_lrouter_port_uuid[url_list[5]]

    peer_port_href = "/".join(url_list)

    url_str['peer_port_href'] = peer_port_href
    url_str['peer_port_uuid'] = url_list[5] 

    return json.dumps(url_str)

def return_l3_gateway_body(body):
    #print "1.return l3 gateway bod ===========",body
    tmp_body = json.loads(body) 
    
    tmp_uuid = change_gateway_service_uuid[tmp_body['l3_gateway_service_uuid']]

    tmp_body['l3_gateway_service_uuid'] = tmp_uuid 

    #print "2.return l3 gateway bod ===========",body
    return json.dumps(tmp_body)

def return_l2_gateway_body(body):
    #print "1.return l3 gateway bod ===========",body
    tmp_body = json.loads(body) 
    
    tmp_uuid = change_gateway_service_uuid[tmp_body['l2_gateway_service_uuid']]

    tmp_body['l2_gateway_service_uuid'] = tmp_uuid 

    #print "2.return l3 gateway bod ===========",body
    return json.dumps(tmp_body)


def return_body(body):
    return body
