from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from ..models import FtpGroup, FtpUser

class FtpGroupForm(FlaskForm):
    groupname = StringField('群組名稱', validators=[
        DataRequired(message='群組名稱不能為空'),
        Length(1, 80, message='群組名稱長度必須在1-80字符之間')
    ])
    gid = IntegerField('GID', validators=[
        DataRequired(message='GID不能為空'),
        NumberRange(min=1000, max=65535, message='GID必須在1000-65535之間')
    ])
    description = TextAreaField('描述', validators=[
        Length(0, 500, message='描述不能超過500字符')
    ])
    submit = SubmitField('儲存')
    
    def __init__(self, original_group=None, *args, **kwargs):
        super(FtpGroupForm, self).__init__(*args, **kwargs)
        self.original_group = original_group
    
    def validate_groupname(self, field):
        if self.original_group and field.data == self.original_group.groupname:
            return
        group = FtpGroup.query.filter_by(groupname=field.data).first()
        if group:
            raise ValidationError('群組名稱已存在')
    
    def validate_gid(self, field):
        if self.original_group and field.data == self.original_group.gid:
            return
        group = FtpGroup.query.filter_by(gid=field.data).first()
        if group:
            raise ValidationError('GID已被使用')

class GroupMembersForm(FlaskForm):
    """群組成員管理表單"""
    members = SelectMultipleField('選擇成員', coerce=int)
    submit = SubmitField('更新成員')
    
    def __init__(self, *args, **kwargs):
        super(GroupMembersForm, self).__init__(*args, **kwargs)
        self.members.choices = [(u.id, f'{u.username} (UID: {u.uid})') 
                               for u in FtpUser.query.filter_by(is_enabled=True).order_by(FtpUser.username).all()]

class GroupSearchForm(FlaskForm):
    """群組搜尋表單"""
    search = StringField('搜尋群組', validators=[Length(0, 64)])
    submit = SubmitField('搜尋')