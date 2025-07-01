from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
from flask_babel import lazy_gettext as _l
from ..models import FtpUser, FtpGroup

class FtpUserForm(FlaskForm):
    username = StringField(_l('Username'), validators=[
        DataRequired(message=_l('Username cannot be empty')),
        Length(1, 64, message=_l('Username length must be between 1-64 characters'))
    ])
    password = PasswordField(_l('Password'), validators=[
        DataRequired(message=_l('Password cannot be empty')),
        Length(6, 128, message=_l('Password length must be between 6-128 characters'))
    ])
    home_directory = StringField(_l('Home Directory'), validators=[
        DataRequired(message=_l('Home directory cannot be empty')),
        Length(1, 200, message=_l('Home directory path cannot exceed 200 characters'))
    ])
    uid = IntegerField('UID', validators=[
        DataRequired(message=_l('UID cannot be empty')),
        NumberRange(min=1000, max=65535, message=_l('UID must be between 1000-65535'))
    ])
    gid = IntegerField(_l('Default GID'), validators=[
        DataRequired(message=_l('GID cannot be empty')),
        NumberRange(min=1000, max=65535, message=_l('GID must be between 1000-65535'))
    ])
    shell = StringField('Shell', validators=[
        Length(0, 100, message=_l('Shell path cannot exceed 100 characters'))
    ], default='/sbin/nologin')
    comment = TextAreaField(_l('Comment'), validators=[
        Length(0, 500, message=_l('Comment cannot exceed 500 characters'))
    ])
    is_enabled = BooleanField(_l('Enable Account'), default=True)
    submit = SubmitField(_l('Save'))
    
    def __init__(self, original_user=None, *args, **kwargs):
        super(FtpUserForm, self).__init__(*args, **kwargs)
        self.original_user = original_user
    
    def validate_username(self, field):
        if self.original_user and field.data == self.original_user.username:
            return
        user = FtpUser.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError(_l('Username already exists'))
    
    def validate_uid(self, field):
        if self.original_user and field.data == self.original_user.uid:
            return
        user = FtpUser.query.filter_by(uid=field.data).first()
        if user:
            raise ValidationError(_l('UID already in use'))

class FtpUserEditForm(FtpUserForm):
    password = PasswordField(_l('Password'), validators=[
        Optional(),
        Length(6, 128, message=_l('Password length must be between 6-128 characters'))
    ])

class UserGroupForm(FlaskForm):
    """User group assignment form"""
    group_id = SelectField(_l('Group'), coerce=int, validators=[DataRequired()])
    submit = SubmitField(_l('Join Group'))
    
    def __init__(self, *args, **kwargs):
        super(UserGroupForm, self).__init__(*args, **kwargs)
        self.group_id.choices = [(g.id, f'{g.groupname} (GID: {g.gid})') 
                                for g in FtpGroup.query.order_by(FtpGroup.groupname).all()]

class UserSearchForm(FlaskForm):
    """User search form"""
    search = StringField(_l('Search Users'), validators=[Length(0, 64)])
    status = SelectField(_l('Status'), choices=[
        ('all', _l('All')),
        ('enabled', _l('Enabled')),
        ('disabled', _l('Disabled'))
    ], default='all')
    group_filter = SelectField(_l('Group Filter'), coerce=int)
    submit = SubmitField(_l('Search'))
    
    def __init__(self, *args, **kwargs):
        super(UserSearchForm, self).__init__(*args, **kwargs)
        groups = [(0, _l('All Groups'))] + [(g.id, g.groupname) 
                                    for g in FtpGroup.query.order_by(FtpGroup.groupname).all()]
        self.group_filter.choices = groups