from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from ..models import Directory, FtpUser, FtpGroup

class DirectoryForm(FlaskForm):
    """目錄管理表單"""
    name = StringField('目錄名稱', validators=[
        DataRequired(message='目錄名稱不能為空'),
        Length(1, 100, message='目錄名稱長度必須在1-100字符之間')
    ])
    path = StringField('目錄路徑', validators=[
        DataRequired(message='目錄路徑不能為空'),
        Length(1, 200, message='目錄路徑不能超過200字符')
    ])
    description = TextAreaField('描述', validators=[
        Length(0, 500, message='描述不能超過500字符')
    ])
    is_active = BooleanField('啟用', default=True)
    create_physical_dir = BooleanField('建立實體目錄', default=True)
    sync_config = BooleanField('同步所有配置並重新載入', default=True)
    submit = SubmitField('儲存')
    
    def __init__(self, original_directory=None, *args, **kwargs):
        super(DirectoryForm, self).__init__(*args, **kwargs)
        self.original_directory = original_directory
    
    def validate_path(self, field):
        if self.original_directory and field.data == self.original_directory.path:
            return
        directory = Directory.query.filter_by(path=field.data).first()
        if directory:
            raise ValidationError('目錄路徑已存在')

class PermissionForm(FlaskForm):
    """權限設定表單"""
    directory_id = SelectField('目錄', coerce=int, validators=[DataRequired()])
    target_type = SelectField('權限目標', choices=[
        ('user', '用戶'),
        ('group', '群組')
    ], validators=[DataRequired()])
    
    # 用戶選項 (使用字串列表存儲選中的用戶ID)
    selected_users = StringField('選擇用戶')
    # 群組選項 (使用字串列表存儲選中的群組ID) 
    selected_groups = StringField('選擇群組')
    
    can_read = BooleanField('讀取權限 (LIST, CWD, PWD, NLST, STAT, MLSD)')
    can_write = BooleanField('寫入權限 (STOR, STOU, APPE)')
    can_delete = BooleanField('刪除權限 (DELE, MKD, RMD, RNFR, RNTO, SITE_CHMOD)')
    
    sync_config = BooleanField('同步所有配置並重新載入', default=True)
    submit = SubmitField('儲存權限')
    
    def __init__(self, *args, **kwargs):
        super(PermissionForm, self).__init__(*args, **kwargs)
        
        # 設定目錄選項
        self.directory_id.choices = [(d.id, f'{d.name} ({d.path})') 
                                    for d in Directory.query.filter_by(is_active=True).order_by(Directory.name).all()]
    
    def validate(self, extra_validators=None):
        rv = FlaskForm.validate(self, extra_validators)
        if not rv:
            return False
            
        # 驗證必須選擇至少一個目標
        if self.target_type.data == 'user':
            if not self.selected_users.data or not self.selected_users.data.strip():
                self.selected_users.errors.append('請選擇至少一個用戶')
                return False
        elif self.target_type.data == 'group':
            if not self.selected_groups.data or not self.selected_groups.data.strip():
                self.selected_groups.errors.append('請選擇至少一個群組')
                return False
        
        return True

class BulkPermissionForm(FlaskForm):
    """批量權限設定表單"""
    directory_ids = SelectField('目錄', coerce=int, validators=[DataRequired()])
    apply_to_users = BooleanField('套用到所有用戶')
    apply_to_groups = BooleanField('套用到所有群組')
    selected_users = StringField('選擇用戶 (逗號分隔的用戶ID)')
    selected_groups = StringField('選擇群組 (逗號分隔的群組ID)')
    
    can_read = BooleanField('讀取權限')
    can_write = BooleanField('寫入權限')
    can_delete = BooleanField('刪除權限')
    
    submit = SubmitField('批量設定')

class PermissionSearchForm(FlaskForm):
    """權限搜尋表單"""
    directory_filter = SelectField('目錄篩選', coerce=int)
    user_filter = SelectField('用戶篩選', coerce=int)
    group_filter = SelectField('群組篩選', coerce=int)
    permission_type = SelectField('權限類型', choices=[
        ('all', '全部'),
        ('read', '僅讀取'),
        ('write', '僅寫入'),
        ('delete', '僅刪除'),
        ('full', '完整權限'),
        ('none', '無權限')
    ], default='all')
    submit = SubmitField('篩選')
    
    def __init__(self, *args, **kwargs):
        super(PermissionSearchForm, self).__init__(*args, **kwargs)
        
        # 目錄選項
        directories = [(0, '全部目錄')] + [(d.id, d.name) 
                                        for d in Directory.query.filter_by(is_active=True).order_by(Directory.name).all()]
        self.directory_filter.choices = directories
        
        # 用戶選項
        users = [(0, '全部用戶')] + [(u.id, u.username) 
                                    for u in FtpUser.query.filter_by(is_enabled=True).order_by(FtpUser.username).all()]
        self.user_filter.choices = users
        
        # 群組選項
        groups = [(0, '全部群組')] + [(g.id, g.groupname) 
                                     for g in FtpGroup.query.order_by(FtpGroup.groupname).all()]
        self.group_filter.choices = groups