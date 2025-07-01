from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, ValidationError
from flask_babel import lazy_gettext as _l

class LoginForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired(), Length(1, 64)])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Login'))

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l('Current Password'), validators=[DataRequired()])
    new_password = PasswordField(_l('New Password'), validators=[DataRequired(), Length(6, 128)])
    confirm_password = PasswordField(_l('Confirm New Password'), validators=[DataRequired()])
    submit = SubmitField(_l('Change Password'))
    
    def validate_confirm_password(self, field):
        if field.data != self.new_password.data:
            raise ValidationError(_l('Password confirmation does not match'))

class CreateAdminForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired(), Length(1, 64)])
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[DataRequired(), Length(6, 128)])
    submit = SubmitField(_l('Create Administrator'))