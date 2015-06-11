import sys
import traceback
import string

def ip_check(ip):
    import socket
    """
    Check the validity of an IPv4 address
    """
    try:
        socket.inet_pton(socket.AF_INET, ip)
    except AttributeError:
        try:
            socket.inet_aton(ip)
        except socket.error:
            return False
        return ip_str.count('.') == 3
    except socket.error:
        return False
    return True

def port_check(port):
    if port <= 65535 and port >= 0:
        return port
    else:
        print "invalid port"
    return None
