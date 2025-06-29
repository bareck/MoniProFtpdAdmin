from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, ValidationError

class LoginForm(FlaskForm):
    username = StringField('用戶名', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('密碼', validators=[DataRequired()])
    remember_me = BooleanField('記住我')
    submit = SubmitField('登入')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('目前密碼', validators=[DataRequired()])
    new_password = PasswordField('新密碼', validators=[DataRequired(), Length(6, 128)])
    confirm_password = PasswordField('確認新密碼', validators=[DataRequired()])
    submit = SubmitField('更改密碼')
    
    def validate_confirm_password(self, field):
        if field.data != self.new_password.data:
            raise ValidationError('密碼確認不符')

class CreateAdminForm(FlaskForm):
    username = StringField('用戶名', validators=[DataRequired(), Length(1, 64)])
    email = StringField('電子郵件', validators=[DataRequired(), Email()])
    password = PasswordField('密碼', validators=[DataRequired(), Length(6, 128)])
    submit = SubmitField('創建管理員')