import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///proftpd_admin.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # ProFTPD configuration - auto-detect config path
    PROFTPD_BASE_DIR = os.environ.get('PROFTPD_BASE_DIR') or '/backup/ftpdata'
    
    # Try to detect ProFTPD config directory
    def _detect_proftpd_config():
        # Check for self-compiled version first
        if os.path.exists('/usr/local/etc/proftpd.conf'):
            return '/usr/local/etc', '/usr/local/etc/proftpd.conf'
        # Check for package manager version
        elif os.path.exists('/etc/proftpd/proftpd.conf'):
            return '/etc/proftpd', '/etc/proftpd/proftpd.conf'
        # Default to package manager paths (will be created if needed)
        else:
            return '/etc/proftpd', '/etc/proftpd/proftpd.conf'
    
    PROFTPD_CONFIG_DIR, PROFTPD_MAIN_CONFIG = _detect_proftpd_config()
    PROFTPD_CONFIG_DIR = os.environ.get('PROFTPD_CONFIG_DIR') or PROFTPD_CONFIG_DIR
    PROFTPD_MAIN_CONFIG = os.environ.get('PROFTPD_MAIN_CONFIG') or PROFTPD_MAIN_CONFIG
    PROFTPD_PASSWD_FILE = os.path.join(PROFTPD_CONFIG_DIR, 'ftpd.passwd')
    PROFTPD_GROUP_FILE = os.path.join(PROFTPD_CONFIG_DIR, 'ftpd.group')
    PROFTPD_DYNAMIC_CONFIG = os.path.join(PROFTPD_CONFIG_DIR, 'dynamic.conf')
    
    # Log files
    PROFTPD_LOG_DIR = '/var/log/proftpd'
    PROFTPD_ACCESS_LOG = os.path.join(PROFTPD_LOG_DIR, 'access.log')
    PROFTPD_AUTH_LOG = os.path.join(PROFTPD_LOG_DIR, 'auth.log')
    
    # Admin settings
    DEFAULT_ADMIN_USER = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin123'  # Should be changed on first login

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}