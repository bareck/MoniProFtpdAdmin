from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from flask_babel import lazy_gettext as _l
from ..models import FtpGroup, FtpUser

class FtpGroupForm(FlaskForm):
    groupname = StringField(_l('Group Name'), validators=[
        DataRequired(message=_l('Group name cannot be empty')),
        Length(1, 80, message=_l('Group name length must be between 1-80 characters'))
    ])
    gid = IntegerField('GID', validators=[
        DataRequired(message=_l('GID cannot be empty')),
        NumberRange(min=1000, max=65535, message=_l('GID must be between 1000-65535'))
    ])
    description = TextAreaField(_l('Description'), validators=[
        Length(0, 500, message=_l('Description cannot exceed 500 characters'))
    ])
    submit = SubmitField(_l('Save'))
    
    def __init__(self, original_group=None, *args, **kwargs):
        super(FtpGroupForm, self).__init__(*args, **kwargs)
        self.original_group = original_group
    
    def validate_groupname(self, field):
        if self.original_group and field.data == self.original_group.groupname:
            return
        group = FtpGroup.query.filter_by(groupname=field.data).first()
        if group:
            raise ValidationError(_l('Group name already exists'))
    
    def validate_gid(self, field):
        if self.original_group and field.data == self.original_group.gid:
            return
        group = FtpGroup.query.filter_by(gid=field.data).first()
        if group:
            raise ValidationError(_l('GID already in use'))

class GroupMembersForm(FlaskForm):
    """群組成員管理表單"""
    members = SelectMultipleField(_l('Select Members'), coerce=int)
    submit = SubmitField(_l('Update Members'))
    
    def __init__(self, *args, **kwargs):
        super(GroupMembersForm, self).__init__(*args, **kwargs)
        self.members.choices = [(u.id, f'{u.username} (UID: {u.uid})') 
                               for u in FtpUser.query.filter_by(is_enabled=True).order_by(FtpUser.username).all()]

class GroupSearchForm(FlaskForm):
    """群組搜尋表單"""
    search = StringField(_l('Search Groups'), validators=[Length(0, 64)])
    submit = SubmitField(_l('Search'))