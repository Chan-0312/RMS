from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import LoginManager, logout_user, login_user, login_required
from json import load, dump
from utils import User, TestPasswd


login_bp = Blueprint('login_bp', __name__)
login_manager = LoginManager()


# 定义获取登录用户的方法
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# 退出登录
@login_bp.route('/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_bp.login'))


# 登录
@login_bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        if request.form['key'] == '登录':
            user_name = request.form.get('account')
            password = request.form.get('password')
            with open(User.user_json_path, 'r') as load_f:
                LOGIN_USERS = load(load_f)
            
            for u in LOGIN_USERS:
                if u.get("username") == user_name:
                    if TestPasswd(user_name, password):
                        user = User(u)
                        login_user(user)
                        if user.administrator:
                            return redirect(url_for('admin_bp.admin'))
                        else:
                            return redirect(url_for('user_bp.user'))
                    else:
                        return render_template('popup.html', popup='用户不存在或密码错误', returnUrl='')
                  
            # 未注册，进行注册
            if TestPasswd(user_name, password):
                id_num = 0
                if len(LOGIN_USERS) > 0:
                    id_num = LOGIN_USERS[-1].get("id") + 1
                else:
                    id_num = 1
                LOGIN_USERS.append({
                        "id": id_num,
                        "username": user_name,
                        # "password": password,
                        # "registered": True,
                        "administrator": False,
                        "container_list": [],
                    }
                )
                with open(User.user_json_path, 'w') as f:
                    dump(LOGIN_USERS, f)

                login_user(User(LOGIN_USERS[-1]))
                return redirect(url_for('user_bp.user'))
            else:
                return render_template('popup.html', popup='用户不存在或密码错误', returnUrl='')
            
            
    return render_template('login.html')
