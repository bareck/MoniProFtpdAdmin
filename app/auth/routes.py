from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from . import bp
from .forms import LoginForm, ChangePasswordForm
from ..models import AdminUser, AccessLog, db
from ..utils import log_action

@bp.app_context_processor
def inject_user():
    return dict(current_user=current_user)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = AdminUser.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log_action('login', 'admin', user.id, description_key='user_logged_in', username=user.username)
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            return redirect(next_page)
        flash('無效的用戶名或密碼', 'error')
    
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    log_action('logout', 'admin', current_user.id, description_key='user_logged_out', username=current_user.username)
    logout_user()
    flash('您已成功登出', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            log_action('change_password', 'admin', current_user.id, description_key='password_changed')
            flash('密碼已成功更改', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('目前密碼不正確', 'error')
    
    return render_template('auth/change_password.html', form=form)