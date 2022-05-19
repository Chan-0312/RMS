from json import load
from flask_login import UserMixin
from os import popen
from psutil import virtual_memory

import crypt 


conf = None
with open("./conf.json",'r') as load_f:
    conf = load(load_f)


def TestPasswd(username: str, passwd: str):
    passFile = open('/etc/shadow')
    for line in passFile.readlines():
        if ":" in line:
            user = line.split(":")[0]
            if user != username:
                continue
            cryptPass = line.split(":")[1].strip(' ')
            salt = cryptPass[cryptPass.find("$"):cryptPass.rfind("$")]
            cryptWord = crypt.crypt(passwd, salt)
            return cryptWord == cryptPass
    return False

class User(UserMixin):
    user_json_path = conf["user_json_path"]

    """用户类"""
    def __init__(self, user):
        self.username = user.get("username")
        self.password = user.get("password")
        self.id = user.get("id")
        self.administrator = user.get("administrator")
        self.registered = user.get("registered")
        self.container_list = user.get("container_list")

    def verify_password(self, password):
        """密码验证"""
        if self.password is None or not self.registered:
            return False
        return self.password == password

    def get_id(self):
        """获取用户ID"""
        return self.id

    @staticmethod
    def get(user_id):
        """根据用户ID获取用户实体，为 login_user 方法提供支持"""
        if not user_id:
            return None
        with open(User.user_json_path, 'r') as load_f:
            LOGIN_USERS = load(load_f)
        for user in LOGIN_USERS:
            if user.get('id') == user_id:
                return User(user)
        return None


class Container:
    container_json_path = conf["container_json_path"]
    docker_images = conf["docker_images"]
    user_max_container_num = conf["user_max_container_num"]
    port_mapping_scope = conf["port_mapping_scope"]
    docker_data_path = conf["docker_data_path"]

    def __init__(self, container):

        self.container = container.get("container")
        self.user = container.get("user")
        self.image = container.get("image")
        self.resource_type = container.get("resource_type")
        self.port_mapping = container.get("port_mapping")
        self.container_status = container.get("container_status")
    


    

def get_valid_mapping_port(port_amount=1):
    with open(Container.container_json_path, 'r') as load_f:
        Container_INFO = load(load_f)

    used_port = []
    for c in Container_INFO:
        port_mapping = c.get("port_mapping").split("|")
        for port in port_mapping:
            used_port.append(int(port.split(":")[0]))

    valid_port = []
    for i in range(Container.port_mapping_scope[0], Container.port_mapping_scope[1]):
        if i not in used_port:
            valid_port.append(i)
            if len(valid_port) >= port_amount:
                return valid_port

        
def get_valid_resource_id():
    with open(conf["resource_json_path"], 'r') as load_f:
        resource_INFO = load(load_f)

    used_id = []
    for i in range(len(resource_INFO)):
        used_id.append(resource_INFO[i].get("resource_id"))

    for i in range(conf["max_resource_table_num"]):
        if i not in used_id:
            return i

    

def get_server_usage(username="all"):

    EXPAND = 1024 ** 2
    mem = virtual_memory()


    # 获取内存
    cpumem = "%dMiB/%dMiB"%(((mem.total - mem.available) / EXPAND), (mem.total / EXPAND))
    # 获取显存
    try:
        gpumem = popen('nvidia-smi', 'r').read().split("=|")[1].split("\n+-")[0].split("\n")[-2].split("|")[2].replace(' ', '')
    except:
        gpumem = "None"

    pid_list = []
    container_list = []
    if username == "all":
        with open(Container.container_json_path, 'r') as load_f:
            Container_INFO = load(load_f)

        for c in Container_INFO:
            jupyter_url = "---"
            if c.get("container_status") == "运行":
                p_read = popen('docker top %s'%c["container"], 'r').read()
                for str in p_read.split('\n')[1:]:
                    if str != '':
                        str = ' '.join(str.split()) # 去除重复空格
                        pid = str.split(" ")[1]
                        pid_read = popen('ps aux |sort -k1nr| awk \'{print $1,$2,$3,$4,$11,$12,$13,$14}\'| grep %s'%pid, 'r').read().split('\n')[0]
                        str_info = pid_read.split(' ')
                        str_cmd = ''
                        for i in str_info[4:]:
                            str_cmd = str_cmd + ' ' + i
                        str_cmd = ' '.join(str_cmd.split()) # 去除重复空格
                        if float(str_info[2])>0.0 or float(str_info[3])>0.0 : # 占用太小不显示
                            pid_list.append([c["container"], pid, str_info[2], str_info[3], str_cmd])
                        # pid_list.append([c["container"], pid, str_info[2], str_info[3], str_cmd])
                    
                jupyter_port = "8888"
                for port in c["port_mapping"].split("|"):
                    port_split = port.split(":")
                    if port_split[1] == jupyter_port:
                        jupyter_port = port_split[0]
                
                jupyter_url = "http://%s:%s"%(conf["local_IP"], jupyter_port) 
            container_list.append([c["container"], jupyter_url, "%s(%s)"%(c["image"], c["resource_type"]), c["port_mapping"], c["container_status"]])        
    else:
        with open(Container.container_json_path, 'r') as load_f:
            Container_INFO = load(load_f)
        
        for c in Container_INFO:
            if username == c.get("user"):
                jupyter_url = "---"
                if c["container_status"] == "运行":
                    p_read = popen('docker top %s'%c["container"], 'r').read()
                    for str in p_read.split('\n')[1:]:
                        if str != '':
                            str = ' '.join(str.split()) # 去除重复空格
                            pid = str.split(" ")[1]
                            pid_read = popen('ps aux |sort -k1nr| awk \'{print $1,$2,$3,$4,$11,$12,$13,$14}\'| grep %s'%pid, 'r').read().split('\n')[0]
                            str_info = pid_read.split(' ')
                            str_cmd = ''
                            for i in str_info[4:]:
                                str_cmd = str_cmd + ' ' + i
                            str_cmd = ' '.join(str_cmd.split()) # 去除重复空格
                            if float(str_info[2])>0.0 or float(str_info[3])>0.0 : # 占用太小不显示
                                pid_list.append([c["container"], pid, str_info[2], str_info[3], str_cmd])
                            # pid_list.append([c["container"], pid, str_info[2], str_info[3], str_cmd])
                    jupyter_port = "8888"
                    for port in c["port_mapping"].split("|"):
                        port_split = port.split(":")
                        if port_split[1] == jupyter_port:
                            jupyter_port = port_split[0]
                    jupyter_url = "http://%s:%s"%(conf["local_IP"], jupyter_port) 

                container_list.append([c["container"], jupyter_url, "%s(%s)"%(c["image"], c["resource_type"]), c["port_mapping"], c["container_status"]])        


    server_usage = []
    server_usage.append(cpumem)
    server_usage.append(gpumem)
    server_usage.append(len(pid_list))
    server_usage.append(pid_list)

    my_container = []
    my_container.append(len(container_list))
    my_container.append(container_list)

    return server_usage, my_container




def get_resource_requests(username="all"):
    with open(conf["resource_json_path"], 'r') as load_f:
        resource_INFO = load(load_f)

    # by xsc0519
    if len(resource_INFO) > 10:
        resource_INFO = resource_INFO[-10:]


    resource_list = []

    unreview_num = 0

    if username == "all":
        for r in resource_INFO[::-1]: # 倒叙
            resource_list.append([
                r["resource_id"], 
                "%s(%d)"%(r["resource_user"], r["resource_pid"]),
                "%d/%d"%(r["resource_CPU"], r["resource_GPU"]),
                "%s(%d)"%(r["resource_time"], r["resource_duration"]),
                r["resource_status"], 
                r["resource_instruction"]
                ]
            )
            if r["resource_status"] == "待审核":
                unreview_num += 1
    else:
        for r in resource_INFO[::-1]: # 倒叙
            if r["resource_user"] == username:
                resource_list.append([
                    r["resource_id"], 
                    "%s(%d)"%(r["resource_user"], r["resource_pid"]),
                    "%d/%d"%(r["resource_CPU"], r["resource_GPU"]),
                    "%s(%d)"%(r["resource_time"], r["resource_duration"]),
                    r["resource_status"], 
                    r["resource_instruction"]
                    ]
                )
                if r["resource_status"] == "待审核":
                    unreview_num += 1
    
    resource_requests = []
    resource_requests.append(len(resource_list))
    resource_requests.append(resource_list)
    resource_requests.append(unreview_num)

    return resource_requests




