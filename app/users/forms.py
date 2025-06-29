from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
from ..models import FtpUser, FtpGroup

class FtpUserForm(FlaskForm):
    username = StringField('用戶名', validators=[
        DataRequired(message='用戶名不能為空'),
        Length(1, 64, message='用戶名長度必須在1-64字符之間')
    ])
    password = PasswordField('密碼', validators=[
        DataRequired(message='密碼不能為空'),
        Length(6, 128, message='密碼長度必須在6-128字符之間')
    ])
    home_directory = StringField('家目錄', validators=[
        DataRequired(message='家目錄不能為空'),
        Length(1, 200, message='家目錄路徑不能超過200字符')
    ])
    uid = IntegerField('UID', validators=[
        DataRequired(message='UID不能為空'),
        NumberRange(min=1000, max=65535, message='UID必須在1000-65535之間')
    ])
    gid = IntegerField('預設GID', validators=[
        DataRequired(message='GID不能為空'),
        NumberRange(min=1000, max=65535, message='GID必須在1000-65535之間')
    ])
    shell = StringField('Shell', validators=[
        Length(0, 100, message='Shell路徑不能超過100字符')
    ], default='/sbin/nologin')
    comment = TextAreaField('註解', validators=[
        Length(0, 500, message='註解不能超過500字符')
    ])
    is_enabled = BooleanField('啟用帳號', default=True)
    submit = SubmitField('儲存')
    
    def __init__(self, original_user=None, *args, **kwargs):
        super(FtpUserForm, self).__init__(*args, **kwargs)
        self.original_user = original_user
    
    def validate_username(self, field):
        if self.original_user and field.data == self.original_user.username:
            return
        user = FtpUser.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('用戶名已存在')
    
    def validate_uid(self, field):
        if self.original_user and field.data == self.original_user.uid:
            return
        user = FtpUser.query.filter_by(uid=field.data).first()
        if user:
            raise ValidationError('UID已被使用')

class FtpUserEditForm(FtpUserForm):
    password = PasswordField('密碼', validators=[
        Optional(),
        Length(6, 128, message='密碼長度必須在6-128字符之間')
    ])

class UserGroupForm(FlaskForm):
    """用戶群組分配表單"""
    group_id = SelectField('群組', coerce=int, validators=[DataRequired()])
    submit = SubmitField('加入群組')
    
    def __init__(self, *args, **kwargs):
        super(UserGroupForm, self).__init__(*args, **kwargs)
        self.group_id.choices = [(g.id, f'{g.groupname} (GID: {g.gid})') 
                                for g in FtpGroup.query.order_by(FtpGroup.groupname).all()]

class UserSearchForm(FlaskForm):
    """用戶搜尋表單"""
    search = StringField('搜尋用戶', validators=[Length(0, 64)])
    status = SelectField('狀態', choices=[
        ('all', '全部'),
        ('enabled', '已啟用'),
        ('disabled', '已停用')
    ], default='all')
    group_filter = SelectField('群組篩選', coerce=int)
    submit = SubmitField('搜尋')
    
    def __init__(self, *args, **kwargs):
        super(UserSearchForm, self).__init__(*args, **kwargs)
        groups = [(0, '全部群組')] + [(g.id, g.groupname) 
                                    for g in FtpGroup.query.order_by(FtpGroup.groupname).all()]
        self.group_filter.choices = groups