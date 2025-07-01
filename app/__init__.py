from flask import Flask, request, session
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel, _, get_locale
from config import config
import os

login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '請先登入以存取此頁面。'
    login_manager.login_message_category = 'info'
    
    csrf.init_app(app)
    
    def get_locale():
        # 1. 檢查URL參數
        if request.args.get('lang'):
            session['lang'] = request.args.get('lang')
        # 2. 檢查session  
        if 'lang' in session and session['lang'] in app.config['LANGUAGES']:
            return session['lang']
        # 3. 使用瀏覽器偏好設定
        return request.accept_languages.best_match(app.config['LANGUAGES']) or app.config['BABEL_DEFAULT_LOCALE']
    
    # Initialize Babel with locale selector  
    babel = Babel(app, locale_selector=get_locale)
    
    # Register template functions
    @app.template_global()
    def get_current_locale():
        from flask_babel import get_locale
        return str(get_locale())
    
    # Import models
    from .models import db
    db.init_app(app)
    
    # Register blueprints
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from .main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from .users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix='/users')
    
    from .groups import bp as groups_bp
    app.register_blueprint(groups_bp, url_prefix='/groups')
    
    from .permissions import bp as permissions_bp
    app.register_blueprint(permissions_bp, url_prefix='/permissions')
    
    from .monitoring import bp as monitoring_bp
    app.register_blueprint(monitoring_bp, url_prefix='/monitoring')
    
    from .settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')
    
    from .config import bp as config_bp
    app.register_blueprint(config_bp, url_prefix='/config')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        from .models import AdminUser
        if not AdminUser.query.filter_by(username=app.config['DEFAULT_ADMIN_USER']).first():
            admin = AdminUser(
                username=app.config['DEFAULT_ADMIN_USER'],
                email='admin@localhost'
            )
            admin.set_password(app.config['DEFAULT_ADMIN_PASSWORD'])
            db.session.add(admin)
            
            # 創建預設 FTP 群組
            from .models import FtpGroup
            if not FtpGroup.query.filter_by(groupname='admins').first():
                admins_group = FtpGroup(
                    groupname='admins',
                    gid=5000,
                    description='系統管理員群組，擁有完整的檔案和目錄權限'
                )
                db.session.add(admins_group)

            if not FtpGroup.query.filter_by(groupname='users').first():
                users_group = FtpGroup(
                    groupname='users', 
                    gid=5001,
                    description='一般用戶群組，受限的檔案權限'
                )
                db.session.add(users_group)
            
            db.session.commit()
    
    return app