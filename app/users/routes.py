from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy import or_
from . import bp
from .forms import FtpUserForm, FtpUserEditForm, UserGroupForm, UserSearchForm
from ..models import FtpUser, FtpGroup, GroupMembership, db
from ..utils import log_action, get_next_uid, sync_proftpd_files, reload_proftpd
import os

@bp.route('/')
@bp.route('/list')
@login_required
def list():
    """用戶列表頁面"""
    search_form = UserSearchForm()
    
    # 基礎查詢
    query = FtpUser.query
    
    # 處理搜尋
    if request.args.get('search'):
        search_term = request.args.get('search')
        query = query.filter(or_(
            FtpUser.username.contains(search_term),
            FtpUser.comment.contains(search_term)
        ))
    
    # 處理狀態篩選
    status = request.args.get('status', 'all')
    if status == 'enabled':
        query = query.filter_by(is_enabled=True)
    elif status == 'disabled':
        query = query.filter_by(is_enabled=False)
    
    # 處理群組篩選
    group_filter = request.args.get('group_filter', type=int)
    if group_filter and group_filter > 0:
        query = query.join(GroupMembership).filter(GroupMembership.group_id == group_filter)
    
    # 分頁
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('USERS_PER_PAGE', 20)
    
    users = query.order_by(FtpUser.username).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('users/list.html', users=users, search_form=search_form)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """創建新用戶"""
    form = FtpUserForm()
    
    # 設定預設值
    if request.method == 'GET':
        from ..models import SystemSetting
        form.uid.data = get_next_uid()
        form.gid.data = 5001  # 預設 users 群組
        base_dir = SystemSetting.get_value('ftp_base_dir', '/backup/ftpdata')
        form.home_directory.data = base_dir
    
    if form.validate_on_submit():
        try:
            user = FtpUser(
                username=form.username.data,
                home_directory=form.home_directory.data,
                uid=form.uid.data,
                gid=form.gid.data,
                shell=form.shell.data,
                comment=form.comment.data,
                is_enabled=form.is_enabled.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            # 同步 ProFTPD 檔案
            success, message = sync_proftpd_files()
            if not success:
                flash(f'用戶創建成功，但同步失敗: {message}', 'warning')
            else:
                # 重新載入 ProFTPD
                reload_success, reload_message = reload_proftpd()
                if not reload_success:
                    flash(f'用戶創建成功，但重新載入失敗: {reload_message}', 'warning')
                else:
                    flash('用戶創建成功', 'success')
            
            log_action('create_user', 'user', user.id, f'創建用戶: {user.username}')
            return redirect(url_for('users.list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'創建用戶失敗: {str(e)}', 'error')
    
    return render_template('users/create.html', form=form)

@bp.route('/<int:id>')
@login_required
def detail(id):
    """用戶詳情頁面"""
    user = FtpUser.query.get_or_404(id)
    return render_template('users/detail.html', user=user)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """編輯用戶"""
    user = FtpUser.query.get_or_404(id)
    form = FtpUserEditForm(original_user=user, obj=user)
    
    if form.validate_on_submit():
        try:
            user.username = form.username.data
            if form.password.data:  # 只有提供新密碼時才更新
                user.set_password(form.password.data)
            user.home_directory = form.home_directory.data
            user.uid = form.uid.data
            user.gid = form.gid.data
            user.shell = form.shell.data
            user.comment = form.comment.data
            user.is_enabled = form.is_enabled.data
            
            db.session.commit()
            
            # 同步 ProFTPD 檔案
            success, message = sync_proftpd_files()
            if success:
                reload_proftpd()
                flash('用戶更新成功', 'success')
            else:
                flash(f'用戶更新成功，但同步失敗: {message}', 'warning')
            
            log_action('edit_user', 'user', user.id, f'編輯用戶: {user.username}')
            return redirect(url_for('users.detail', id=user.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新用戶失敗: {str(e)}', 'error')
    
    return render_template('users/edit.html', form=form, user=user)

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """刪除用戶"""
    user = FtpUser.query.get_or_404(id)
    username = user.username
    
    try:
        db.session.delete(user)
        db.session.commit()
        
        # 同步 ProFTPD 檔案
        success, message = sync_proftpd_files()
        if success:
            reload_proftpd()
            flash(f'用戶 {username} 已刪除', 'success')
        else:
            flash(f'用戶已刪除，但同步失敗: {message}', 'warning')
        
        log_action('delete_user', 'user', id, f'刪除用戶: {username}')
        
    except Exception as e:
        db.session.rollback()
        flash(f'刪除用戶失敗: {str(e)}', 'error')
    
    return redirect(url_for('users.list'))

@bp.route('/<int:id>/toggle_status', methods=['POST'])
@login_required
def toggle_status(id):
    """切換用戶啟用狀態"""
    user = FtpUser.query.get_or_404(id)
    
    try:
        user.is_enabled = not user.is_enabled
        db.session.commit()
        
        status = '啟用' if user.is_enabled else '停用'
        flash(f'用戶 {user.username} 已{status}', 'success')
        
        # 同步 ProFTPD 檔案
        success, message = sync_proftpd_files()
        if success:
            reload_proftpd()
        
        log_action('toggle_user_status', 'user', user.id, 
                  f'{status}用戶: {user.username}')
        
    except Exception as e:
        db.session.rollback()
        flash(f'狀態更新失敗: {str(e)}', 'error')
    
    return redirect(url_for('users.detail', id=user.id))

@bp.route('/<int:id>/groups', methods=['GET', 'POST'])
@login_required
def manage_groups(id):
    """管理用戶群組"""
    user = FtpUser.query.get_or_404(id)
    form = UserGroupForm()
    
    if form.validate_on_submit():
        group = FtpGroup.query.get(form.group_id.data)
        if group:
            # 檢查是否已經是成員
            existing = GroupMembership.query.filter_by(
                user_id=user.id, group_id=group.id
            ).first()
            
            if existing:
                flash(f'用戶已經是 {group.groupname} 群組的成員', 'info')
            else:
                membership = GroupMembership(user_id=user.id, group_id=group.id)
                db.session.add(membership)
                db.session.commit()
                
                flash(f'已將用戶加入 {group.groupname} 群組', 'success')
                log_action('add_user_to_group', 'user', user.id, 
                          f'將用戶 {user.username} 加入群組 {group.groupname}')
                
                # 同步檔案
                sync_proftpd_files()
                reload_proftpd()
    
    return render_template('users/groups.html', user=user, form=form)

@bp.route('/<int:user_id>/remove_group/<int:group_id>', methods=['POST'])
@login_required
def remove_from_group(user_id, group_id):
    """從群組中移除用戶"""
    membership = GroupMembership.query.filter_by(
        user_id=user_id, group_id=group_id
    ).first_or_404()
    
    try:
        group_name = membership.group.groupname
        user_name = membership.user.username
        
        db.session.delete(membership)
        db.session.commit()
        
        flash(f'已將用戶 {user_name} 從群組 {group_name} 中移除', 'success')
        log_action('remove_user_from_group', 'user', user_id, 
                  f'將用戶 {user_name} 從群組 {group_name} 中移除')
        
        # 同步檔案
        sync_proftpd_files()
        reload_proftpd()
        
    except Exception as e:
        db.session.rollback()
        flash(f'移除失敗: {str(e)}', 'error')
    
    return redirect(url_for('users.manage_groups', id=user_id))

@bp.route('/api/check_username')
@login_required
def check_username():
    """檢查用戶名是否可用 (AJAX)"""
    username = request.args.get('username', '').strip()
    user_id = request.args.get('user_id', type=int)
    
    if not username:
        return jsonify({'available': False, 'message': '用戶名不能為空'})
    
    query = FtpUser.query.filter_by(username=username)
    if user_id:  # 編輯模式，排除當前用戶
        query = query.filter(FtpUser.id != user_id)
    
    existing = query.first()
    
    return jsonify({
        'available': existing is None,
        'message': '用戶名可用' if existing is None else '用戶名已存在'
    })

@bp.route('/api/suggest_uid')
@login_required
def suggest_uid():
    """建議下一個可用的 UID (AJAX)"""
    uid = get_next_uid()
    return jsonify({'uid': uid})