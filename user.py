from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from utils import User, Container, get_valid_mapping_port, conf, get_server_usage, get_resource_requests, get_valid_resource_id
from json import load, dump


from os import popen, makedirs
from os.path import exists

from time import strftime, localtime


user_bp = Blueprint('user_bp', __name__)


@user_bp.route('/user', methods=('GET', 'POST'))   # 首页
@login_required                                 # 需要登录才能访问
def user():

    # 获取用户
    user = current_user._get_current_object()

    if  request.method == 'POST':
        if request.form['key'] == '杀死进程':
            pid_list = request.form.getlist('checkbox_server_usage')
            if len(pid_list) > 0:
                for pid in pid_list:
                    popen('kill -9 %s'%pid, 'r')
                return render_template('popup.html', popup='杀死进程成功', returnUrl='')
        elif request.form['key'] == '申请容器':
            select_image = request.form.get('select_image')
            select_resource_type = request.form.get('select_resource_type')
            port = request.form.get('port_mapping').split("|")

            with open(User.user_json_path, 'r') as load_f:
                LOGIN_USERS = load(load_f)
            
            if len(user.container_list) >= Container.user_max_container_num:
                return render_template('popup.html', popup='已达到可申请的上限', returnUrl='')

            # 获取可用容器名
            for i in range(Container.user_max_container_num):
                if "%s_%d"%(user.username, i) not in user.container_list:
                    container_name = "%s_%d"%(user.username, i)
                    break
            # 获取可用端口
            if len(port) > 0 and port != "":
                port_mapping = ""
                valid_port = get_valid_mapping_port(port_amount=len(port))
                for i in range(len(port)):
                    port_mapping += "%d:%s|"%(valid_port[i], port[i])
                port_mapping = port_mapping[:-1]
            else:
                port_mapping = ""

            c = {
                "container": container_name,
                "user": user.username,
                "image": select_image,
                "resource_type": select_resource_type,
                "port_mapping": port_mapping,
                "container_status": "待审核"
            }
            with open(Container.container_json_path, 'r') as load_f:
                Container_INFO = load(load_f)
            Container_INFO.append(c)
            with open(Container.container_json_path, 'w') as f:
                dump(Container_INFO, f)

            for i in range(len(LOGIN_USERS)):
                if LOGIN_USERS[i].get("username") == user.username:
                    LOGIN_USERS[i]["container_list"].append(container_name)
                    user.container_list.append(container_name) # 当前的user要加入不然不同步
            with open(User.user_json_path, 'w') as f:
                dump(LOGIN_USERS, f)
            return render_template('popup.html', popup='申请容器成功，等待管理员审核', returnUrl='')

        elif request.form['key'] == '启动容器':
            container_list = request.form.getlist('checkbox_my_container')
            if len(container_list) == 1:
                with open(Container.container_json_path, 'r') as load_f:
                    Container_INFO = load(load_f)
                for i in range(len(Container_INFO)):
                    if Container_INFO[i].get("container") in container_list and Container_INFO[i].get("container_status") == "待审核":
                        return render_template('popup.html', popup='容器待审核中，请稍等', returnUrl='')

                    if Container_INFO[i].get("container") in container_list and Container_INFO[i].get("container_status") != "运行":

                        # 启动容器
                        popen("docker start %s"%Container_INFO[i].get("container"), 'r')

                        start_cmd = Container.docker_images[Container_INFO[i].get("image")]["start_cmd"]

                        for cmd in start_cmd.split("|"):
                            popen(cmd.replace("container_name", Container_INFO[i].get("container")), 'r')
                           
                        # ----
                        Container_INFO[i]["container_status"] = "运行"

                with open(Container.container_json_path, 'w') as f:
                    dump(Container_INFO, f)
                return render_template('popup.html', popup='启动容器成功', returnUrl='')
            elif len(container_list) > 1:
                return render_template('popup.html', popup='每次仅执行一个操作', returnUrl='')
        elif request.form['key'] == '停止容器':
            container_list = request.form.getlist('checkbox_my_container')
            if len(container_list) == 1:
                with open(Container.container_json_path, 'r') as load_f:
                    Container_INFO = load(load_f)
                for i in range(len(Container_INFO)):
                    if Container_INFO[i].get("container") in container_list and Container_INFO[i].get("container_status") == "待审核":
                        return render_template('popup.html', popup='容器待审核中，请稍等', returnUrl='')

                    if Container_INFO[i].get("container") in container_list and Container_INFO[i].get("container_status") == "运行":
                        popen("docker stop %s"%Container_INFO[i].get("container"), 'r')
                        Container_INFO[i]["container_status"] = "停止"

                with open(Container.container_json_path, 'w') as f:
                    dump(Container_INFO, f)
                return render_template('popup.html', popup='停止容器成功，请稍等10s再进行其他操作', returnUrl='')
            elif len(container_list) > 1:
                return render_template('popup.html', popup='每次仅执行一个操作', returnUrl='')

        elif request.form['key'] == '删除容器':
            container_list = request.form.getlist('checkbox_my_container')
            if len(container_list) == 1:
                with open(Container.container_json_path, 'r') as load_f:
                    Container_INFO = load(load_f)
                
                del_name_list = []
                del_container_list = []
                for c in Container_INFO:
                    if c.get("container") in container_list:
                        if c.get("container_status") == "运行":
                            return render_template('popup.html', popup='请先停止容器', returnUrl='')
                        if c.get("container_status") != "待审核":
                            popen("docker rm %s"%c.get("container"), 'r')

                        del_name_list.append(c.get("user"))
                        del_container_list.append(c.get("container"))
                        Container_INFO.remove(c)
                
                                            
                with open(User.user_json_path, 'r') as load_f:
                    LOGIN_USERS = load(load_f)
                for i in range(len(LOGIN_USERS)):
                    if LOGIN_USERS[i].get("username") in del_name_list:
                        for container in LOGIN_USERS[i]["container_list"]:
                            if container in del_container_list:
                                LOGIN_USERS[i]["container_list"].remove(container)
                with open(User.user_json_path, 'w') as f:
                    dump(LOGIN_USERS, f)

                with open(Container.container_json_path, 'w') as f:
                    dump(Container_INFO, f)

                return render_template('popup.html', popup='删除容器成功', returnUrl='')
            elif len(container_list) > 1:
                return render_template('popup.html', popup='每次仅执行一个操作', returnUrl='')


        elif request.form['key'] == '申请使用资源':            
            r = {
                "resource_id" : get_valid_resource_id(),
                "resource_user": user.username,
                "resource_pid" : int(request.form.get('apply_pid')),
                "resource_CPU" : int(request.form.get('apply_CPU')),
                "resource_GPU" : int(request.form.get('apply_GPU')),
                "resource_time" : strftime("%Y-%m-%d-%H-%M-%S", localtime()),
                "resource_duration" : int(request.form.get('apply_duration')),
                "resource_instruction" : request.form.get('apply_instruction'),
                "resource_status" : "待审核",
            }

            with open(conf["resource_json_path"], 'r') as load_f:
                resource_INFO = load(load_f)
            
            resource_INFO.append(r)

            with open(conf["resource_json_path"], 'w') as f:
                dump(resource_INFO, f)

            return render_template('popup.html', popup='申请资源成功，等待管理员审核', returnUrl='')
        elif request.form['key'] == '修改申请使用': 
            resource_id = int(request.form.get('apply_resource_id'))

            with open(conf["resource_json_path"], 'r') as load_f:
                resource_INFO = load(load_f)
            
            for i in range(len(resource_INFO)):
                if resource_INFO[i].get("resource_id") == resource_id and resource_INFO[i].get("resource_user") == user.username:
                    resource_INFO[i]["resource_pid"] = int(request.form.get('apply_pid'))
                    resource_INFO[i]["resource_CPU"] = int(request.form.get('apply_CPU'))
                    resource_INFO[i]["resource_GPU"] = int(request.form.get('apply_GPU'))
                    resource_INFO[i]["resource_time"] = strftime("%Y-%m-%d-%H-%M-%S", localtime())
                    resource_INFO[i]["resource_duration"] = int(request.form.get('apply_duration'))
                    resource_INFO[i]["resource_instruction"] = request.form.get('apply_instruction')
            
                    with open(conf["resource_json_path"], 'w') as f:
                        dump(resource_INFO, f)
                    return render_template('popup.html', popup='修改申请使用成功', returnUrl='')
            
            return render_template('popup.html', popup='资源号不存在', returnUrl='')
        elif request.form['key'] == '释放申请资源':

            resource_list = request.form.getlist('checkbox_resource_requests')
            if len(resource_list) > 0:
                with open(conf["resource_json_path"], 'r') as load_f:
                    resource_INFO = load(load_f)
                
                for i in range(len(resource_INFO)):
                    if str(resource_INFO[i]["resource_id"]) in resource_list:
                        resource_INFO[i]["resource_status"] = "已释放"

                with open(conf["resource_json_path"], 'w') as f:
                    dump(resource_INFO, f)

                return render_template('popup.html', popup='释放申请资源成功', returnUrl='')
            
        elif request.form['key'] == '删除申请资源':

            resource_list = request.form.getlist('checkbox_resource_requests')
            if len(resource_list) == 1:
                with open(conf["resource_json_path"], 'r') as load_f:
                    resource_INFO = load(load_f)
                
                for r in resource_INFO:
                    if str(r["resource_id"]) in resource_list:
                        resource_INFO.remove(r)

                with open(conf["resource_json_path"], 'w') as f:
                    dump(resource_INFO, f)

                return render_template('popup.html', popup='删除申请资源成功', returnUrl='')
            elif len(resource_list) > 1:
                return render_template('popup.html', popup='每次仅执行一个操作', returnUrl='')
        elif request.form['key'] == '退出':
            return redirect(url_for('login_bp.logout'))
        

    server_usage, my_container = get_server_usage(username=user.username)

    resource_requests = get_resource_requests(username=user.username)

    return render_template('user.html', 
                            username = user.username,
                            docker_images = [len(Container.docker_images), list(Container.docker_images.keys())],
                            server_usage=server_usage,
                            my_container=my_container,
                            resource_requests=resource_requests,
    )