from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class AdminUser(UserMixin, db.Model):
    """Web管理介面的管理員用戶"""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'

class FtpUser(db.Model):
    """FTP虛擬用戶"""
    __tablename__ = 'ftp_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    home_directory = db.Column(db.String(200), nullable=False)
    uid = db.Column(db.Integer, unique=True, nullable=False)
    gid = db.Column(db.Integer, nullable=False)
    shell = db.Column(db.String(100), default='/sbin/nologin')
    comment = db.Column(db.Text)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    group_memberships = db.relationship('GroupMembership', back_populates='user', cascade='all, delete-orphan')
    permissions = db.relationship('DirectoryPermission', back_populates='user', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """設定FTP用戶密碼（使用crypt加密，ProFTPD兼容）"""
        import crypt
        self.password_hash = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    
    def get_groups(self):
        """取得用戶所屬的群組列表"""
        return [membership.group for membership in self.group_memberships]
    
    def __repr__(self):
        return f'<FtpUser {self.username}>'

class FtpGroup(db.Model):
    """FTP用戶群組"""
    __tablename__ = 'ftp_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    groupname = db.Column(db.String(80), unique=True, nullable=False)
    gid = db.Column(db.Integer, unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = db.relationship('GroupMembership', back_populates='group', cascade='all, delete-orphan')
    permissions = db.relationship('DirectoryPermission', back_populates='group', cascade='all, delete-orphan')
    
    def get_members(self):
        """取得群組成員列表"""
        return [membership.user for membership in self.members]
    
    def __repr__(self):
        return f'<FtpGroup {self.groupname}>'

class GroupMembership(db.Model):
    """群組成員關係表"""
    __tablename__ = 'group_memberships'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('ftp_users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('ftp_groups.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('FtpUser', back_populates='group_memberships')
    group = db.relationship('FtpGroup', back_populates='members')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'group_id', name='unique_user_group'),)
    
    def __repr__(self):
        return f'<GroupMembership {self.user.username}@{self.group.groupname}>'

class Directory(db.Model):
    """FTP目錄管理"""
    __tablename__ = 'directories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    permissions = db.relationship('DirectoryPermission', back_populates='directory', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Directory {self.name}>'

class DirectoryPermission(db.Model):
    """目錄權限設定"""
    __tablename__ = 'directory_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    directory_id = db.Column(db.Integer, db.ForeignKey('directories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('ftp_users.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('ftp_groups.id'), nullable=True)
    
    # 權限類型
    can_read = db.Column(db.Boolean, default=False)  # LIST, CWD, PWD, NLST, STAT, MLSD
    can_write = db.Column(db.Boolean, default=False)  # STOR, STOU, APPE
    can_delete = db.Column(db.Boolean, default=False)  # DELE, MKD, RMD, RNFR, RNTO, SITE_CHMOD
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    directory = db.relationship('Directory', back_populates='permissions')
    user = db.relationship('FtpUser', back_populates='permissions')
    group = db.relationship('FtpGroup', back_populates='permissions')
    
    # Constraints: 每個權限項目必須指定用戶或群組（不能兩者都空）
    __table_args__ = (
        db.CheckConstraint('user_id IS NOT NULL OR group_id IS NOT NULL', name='check_user_or_group'),
        db.UniqueConstraint('directory_id', 'user_id', name='unique_dir_user'),
        db.UniqueConstraint('directory_id', 'group_id', name='unique_dir_group'),
    )
    
    def __repr__(self):
        target = self.user.username if self.user else self.group.groupname
        return f'<DirectoryPermission {self.directory.name}:{target}>'

class SystemSetting(db.Model):
    """系統設定"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, integer, boolean, path
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_value(cls, key, default=None):
        """取得設定值"""
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            return default
        
        if setting.data_type == 'boolean':
            return setting.value.lower() in ('true', '1', 'yes', 'on')
        elif setting.data_type == 'integer':
            try:
                return int(setting.value)
            except (ValueError, TypeError):
                return default
        else:
            return setting.value
    
    @classmethod
    def set_value(cls, key, value, description=None, data_type='string'):
        """設定值"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            setting.updated_at = datetime.utcnow()
        else:
            setting = cls(
                key=key,
                value=str(value),
                description=description,
                data_type=data_type
            )
            db.session.add(setting)
        db.session.commit()
        return setting
    
    def __repr__(self):
        return f'<SystemSetting {self.key}={self.value}>'

class AccessLog(db.Model):
    """存取記錄"""
    __tablename__ = 'access_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50))  # user, group, directory, setting
    target_id = db.Column(db.String(100))
    description = db.Column(db.Text)  # 保留原有描述欄位用於向後兼容
    description_key = db.Column(db.String(200))  # 翻譯鍵值
    description_params = db.Column(db.Text)  # JSON格式的翻譯參數
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    admin_user = db.relationship('AdminUser', backref='access_logs')
    
    def get_description_params_dict(self):
        """取得翻譯參數字典"""
        if not self.description_params:
            return {}
        try:
            import json
            return json.loads(self.description_params)
        except:
            return {}
    
    def get_localized_description(self):
        """取得本地化描述"""
        from flask_babel import gettext
        if self.description_key:
            params = self.get_description_params_dict()
            return gettext(self.description_key, **params)
        return self.description or self.action
    
    def __repr__(self):
        return f'<AccessLog {self.action}>'