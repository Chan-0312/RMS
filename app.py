from flask import Flask


from login import login_bp, login_manager
from admin import admin_bp
from user import user_bp

app = Flask("RMS")
app.secret_key = 'RMS'

login_manager.init_app(app)
app.register_blueprint(login_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login_bp.login'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6060, debug=False, threaded=True)