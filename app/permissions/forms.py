from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from flask_babel import lazy_gettext as _l
from ..models import Directory, FtpUser, FtpGroup

class DirectoryForm(FlaskForm):
    """目錄管理表單"""
    name = StringField(_l('Directory Name'), validators=[
        DataRequired(message=_l('Directory name cannot be empty')),
        Length(1, 100, message=_l('Directory name length must be between 1-100 characters'))
    ])
    path = StringField(_l('Directory Path'), validators=[
        DataRequired(message=_l('Directory path cannot be empty')),
        Length(1, 200, message=_l('Directory path cannot exceed 200 characters'))
    ])
    description = TextAreaField(_l('Description'), validators=[
        Length(0, 500, message=_l('Description cannot exceed 500 characters'))
    ])
    is_active = BooleanField(_l('Enable'), default=True)
    create_physical_dir = BooleanField(_l('Create Physical Directory'), default=True)
    sync_config = BooleanField(_l('Sync All Configurations and Reload'), default=True)
    submit = SubmitField(_l('Save'))
    
    def __init__(self, original_directory=None, *args, **kwargs):
        super(DirectoryForm, self).__init__(*args, **kwargs)
        self.original_directory = original_directory
    
    def validate_path(self, field):
        if self.original_directory and field.data == self.original_directory.path:
            return
        directory = Directory.query.filter_by(path=field.data).first()
        if directory:
            raise ValidationError(_l('Directory path already exists'))

class PermissionForm(FlaskForm):
    """權限設定表單"""
    directory_id = SelectField(_l('Directory'), coerce=int, validators=[DataRequired()])
    target_type = SelectField(_l('Permission Target'), choices=[
        ('user', _l('User')),
        ('group', _l('Group'))
    ], validators=[DataRequired()])
    
    # 用戶選項 (使用字串列表存儲選中的用戶ID)
    selected_users = StringField(_l('Select Users'))
    # 群組選項 (使用字串列表存儲選中的群組ID) 
    selected_groups = StringField(_l('Select Groups'))
    
    can_read = BooleanField(_l('Read Permission (LIST, CWD, PWD, NLST, STAT, MLSD)'))
    can_write = BooleanField(_l('Write Permission (STOR, STOU, APPE)'))
    can_delete = BooleanField(_l('Delete Permission (DELE, MKD, RMD, RNFR, RNTO, SITE_CHMOD)'))
    
    sync_config = BooleanField(_l('Sync All Configurations and Reload'), default=True)
    submit = SubmitField(_l('Save Permissions'))
    
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
                self.selected_users.errors.append(_l('Please select at least one user'))
                return False
        elif self.target_type.data == 'group':
            if not self.selected_groups.data or not self.selected_groups.data.strip():
                self.selected_groups.errors.append(_l('Please select at least one group'))
                return False
        
        return True

class BulkPermissionForm(FlaskForm):
    """批量權限設定表單"""
    directory_ids = SelectField(_l('Directory'), coerce=int, validators=[DataRequired()])
    apply_to_users = BooleanField(_l('Apply to All Users'))
    apply_to_groups = BooleanField(_l('Apply to All Groups'))
    selected_users = StringField(_l('Select Users (comma-separated user IDs)'))
    selected_groups = StringField(_l('Select Groups (comma-separated group IDs)'))
    
    can_read = BooleanField(_l('Read Permission'))
    can_write = BooleanField(_l('Write Permission'))
    can_delete = BooleanField(_l('Delete Permission'))
    
    submit = SubmitField(_l('Bulk Settings'))

class PermissionSearchForm(FlaskForm):
    """權限搜尋表單"""
    directory_filter = SelectField(_l('Directory Filter'), coerce=int)
    user_filter = SelectField(_l('User Filter'), coerce=int)
    group_filter = SelectField(_l('Group Filter'), coerce=int)
    permission_type = SelectField(_l('Permission Type'), choices=[
        ('all', _l('All')),
        ('read', _l('Read Only')),
        ('write', _l('Write Only')),
        ('delete', _l('Delete Only')),
        ('full', _l('Full Permissions')),
        ('none', _l('No Permissions'))
    ], default='all')
    submit = SubmitField(_l('Filter'))
    
    def __init__(self, *args, **kwargs):
        super(PermissionSearchForm, self).__init__(*args, **kwargs)
        
        # 目錄選項
        directories = [(0, _l('All Directories'))] + [(d.id, d.name) 
                                        for d in Directory.query.filter_by(is_active=True).order_by(Directory.name).all()]
        self.directory_filter.choices = directories
        
        # 用戶選項
        users = [(0, _l('All Users'))] + [(u.id, u.username) 
                                    for u in FtpUser.query.filter_by(is_enabled=True).order_by(FtpUser.username).all()]
        self.user_filter.choices = users
        
        # 群組選項
        groups = [(0, _l('All Groups'))] + [(g.id, g.groupname) 
                                     for g in FtpGroup.query.order_by(FtpGroup.groupname).all()]
        self.group_filter.choices = groups