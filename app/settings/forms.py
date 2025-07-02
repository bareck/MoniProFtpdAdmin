from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

class SystemSettingsForm(FlaskForm):
    """系統設定表單"""
    
    # FTP 設定
    ftp_server_name = StringField('FTP 伺服器名稱', 
                                 validators=[DataRequired(), Length(1, 100)],
                                 description='顯示在 FTP 連線時的伺服器名稱')
    
    ftp_max_clients = IntegerField('最大連線數', 
                                  validators=[DataRequired(), NumberRange(1, 1000)],
                                  description='同時允許的最大 FTP 連線數')
    
    ftp_max_per_ip = IntegerField('每個 IP 最大連線數', 
                                 validators=[DataRequired(), NumberRange(1, 100)],
                                 description='單一 IP 位址允許的最大連線數')
    
    ftp_passive_ports = StringField('被動模式連接埠範圍', 
                                   validators=[Optional(), Length(0, 50)],
                                   description='格式: 60000-65000')
    
    ftp_umask = StringField('檔案權限遮罩', 
                           validators=[Optional(), Length(0, 10)],
                           description='預設檔案權限遮罩，例如: 000')
    
    ftp_base_dir = StringField('FTP 根目錄路徑', 
                              validators=[DataRequired(), Length(1, 200)],
                              description='FTP 伺服器的根目錄路徑，例如: /backup/ftpdata')
    
    # 日誌設定
    log_access_enabled = BooleanField('啟用存取日誌', 
                                     description='記錄所有 FTP 存取活動')
    
    log_auth_enabled = BooleanField('啟用認證日誌', 
                                   description='記錄登入和認證活動')
    
    log_level = SelectField('日誌等級', 
                           choices=[('info', 'Info'), ('warn', 'Warning'), ('error', 'Error'), ('debug', 'Debug')],
                           description='設定日誌記錄的詳細程度')
    
    log_rotate_days = IntegerField('日誌保留天數', 
                                  validators=[Optional(), NumberRange(1, 365)],
                                  description='自動刪除超過指定天數的日誌')
    
    # 安全設定
    security_login_attempts = IntegerField('最大登入嘗試次數', 
                                          validators=[DataRequired(), NumberRange(3, 20)],
                                          description='達到次數後暫時封鎖 IP')
    
    security_ban_duration = IntegerField('封鎖時間（分鐘）', 
                                        validators=[DataRequired(), NumberRange(5, 1440)],
                                        description='IP 被封鎖的時間長度')
    
    security_allow_root = BooleanField('允許 root 登入', 
                                      description='是否允許 root 用戶進行 FTP 登入')
    
    security_require_ssl = BooleanField('強制使用 SSL/TLS', 
                                       description='要求所有連線使用加密')
    
    # 系統設定
    system_backup_enabled = BooleanField('啟用自動備份', 
                                        description='定期備份配置檔和用戶資料')
    
    system_backup_interval = SelectField('備份頻率', 
                                        choices=[('daily', '每日'), ('weekly', '每週'), ('monthly', '每月')],
                                        description='自動備份的執行頻率')
    
    system_maintenance_mode = BooleanField('維護模式', 
                                          description='啟用後將拒絕所有 FTP 連線')
    
    system_notification_email = StringField('通知電子郵件', 
                                           validators=[Optional(), Length(0, 100)],
                                           description='接收系統警告的電子郵件地址')
    
    submit = SubmitField('儲存設定')

class BackupRestoreForm(FlaskForm):
    """備份還原表單"""
    
    backup_description = TextAreaField('備份描述', 
                                      validators=[Optional(), Length(0, 200)],
                                      description='此次備份的說明或備註')
    
    backup_include_logs = BooleanField('包含日誌檔案', 
                                      description='備份時是否包含系統日誌')
    
    backup_include_data = BooleanField('包含用戶資料', 
                                      description='備份時是否包含 FTP 用戶檔案',
                                      default=True)
    
    create_backup = SubmitField('建立備份')

class ConfigGenerateForm(FlaskForm):
    """配置生成表單"""
    
    generate_config = SubmitField('重新生成配置檔')
    reload_service = BooleanField('重新載入服務', 
                                 description='生成後自動重新載入 ProFTPD 服務',
                                 default=True)
    
class AdminPasswordForm(FlaskForm):
    """管理員密碼變更表單"""
    
    current_password = StringField('目前密碼', 
                                  validators=[DataRequired()],
                                  render_kw={'type': 'password'})
    
    new_password = StringField('新密碼', 
                              validators=[DataRequired(), Length(8, 50)],
                              render_kw={'type': 'password'})
    
    confirm_password = StringField('確認新密碼', 
                                  validators=[DataRequired()],
                                  render_kw={'type': 'password'})
    
    change_password = SubmitField('變更密碼')
    
    def validate_confirm_password(self, field):
        if field.data != self.new_password.data:
            raise ValidationError('密碼確認不一致')