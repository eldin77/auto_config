import os
from paramiko import SSHClient,AutoAddPolicy
import getpass
from errno import * 

class SSH_Client_Obj:
    def __init__(self):
        self.username = None
        self.password = None
        self.server_ip = None

    def set(self,c_username,c_passwrod, c_server_ip):
        self.username = c_username
        self.password = c_passwrod
        self.server_ip = c_server_ip

    def SSH_Connector(self):
        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(self.server_ip, username=self.username, password=self.password)	
        return client

def mkdir_p(path):
    try:
        os.mkdir(path)
    except OSError as exc:
	if exc.errno == EEXIST and os.path.isdir(path):
            pass
	else: raise	

def get_cert():
    connect_server = []
    server_ip = raw_input("server count :") 
    username = raw_input("username :") 
    password = getpass.getpass() 
    mkdir_p("cert") 
    #cnt = 1

    nsx_connect_client = SSH_Client_Obj()
    ssh_server_ip = server_ip 
    nsx_connect_client.set(username,password,ssh_server_ip) 
    client = nsx_connect_client.SSH_Connector()
    certificate_file = file('cert/'+ssh_server_ip,'w')

    stdin, stdout, stderr = client.exec_command('show nsx certificate | begin -----')
    for line in stdout:
	certificate_file.write(line.strip('\n'))
	print "show nsx certificate | begin -----",line.strip('\n')
	
    certificate_file.close()
    commnad = 'cat cert/'+ssh_server_ip
    test = str(os.system(commnad))
    print test.strip(' ')
    client.close()
	
if __name__ == "__main__":
    get_cert()
