from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy import and_, or_
from . import bp
from .forms import DirectoryForm, PermissionForm, BulkPermissionForm, PermissionSearchForm
from ..models import Directory, DirectoryPermission, FtpUser, FtpGroup, db
from ..utils import log_action, sync_proftpd_files, reload_proftpd
import os

@bp.route('/')
@bp.route('/list')
@login_required
def list():
    """權限管理首頁"""
    search_form = PermissionSearchForm()
    
    # 基礎查詢
    query = DirectoryPermission.query.join(Directory).filter(Directory.is_active == True)
    
    # 處理篩選
    directory_filter = request.args.get('directory_filter', type=int)
    if directory_filter and directory_filter > 0:
        query = query.filter(DirectoryPermission.directory_id == directory_filter)
    
    user_filter = request.args.get('user_filter', type=int)
    if user_filter and user_filter > 0:
        query = query.filter(DirectoryPermission.user_id == user_filter)
    
    group_filter = request.args.get('group_filter', type=int)
    if group_filter and group_filter > 0:
        query = query.filter(DirectoryPermission.group_id == group_filter)
    
    permission_type = request.args.get('permission_type', 'all')
    if permission_type == 'read':
        query = query.filter(DirectoryPermission.can_read == True)
    elif permission_type == 'write':
        query = query.filter(DirectoryPermission.can_write == True)
    elif permission_type == 'delete':
        query = query.filter(DirectoryPermission.can_delete == True)
    elif permission_type == 'full':
        query = query.filter(and_(
            DirectoryPermission.can_read == True,
            DirectoryPermission.can_write == True,
            DirectoryPermission.can_delete == True
        ))
    elif permission_type == 'none':
        query = query.filter(and_(
            DirectoryPermission.can_read == False,
            DirectoryPermission.can_write == False,
            DirectoryPermission.can_delete == False
        ))
    
    # 分頁
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('PERMISSIONS_PER_PAGE', 20)
    
    permissions = query.order_by(Directory.name, DirectoryPermission.created_at).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('permissions/list.html', permissions=permissions, search_form=search_form)

@bp.route('/directories')
@login_required
def directories():
    """目錄管理頁面"""
    directories = Directory.query.order_by(Directory.name).all()
    return render_template('permissions/directories.html', directories=directories)

@bp.route('/directories/create', methods=['GET', 'POST'])
@login_required
def create_directory():
    """創建新目錄"""
    form = DirectoryForm()
    
    # 設定預設路徑
    if request.method == 'GET':
        base_dir = current_app.config.get('PROFTPD_BASE_DIR', '/backup/ftpdata')
        form.path.data = f"{base_dir}/"
    
    if form.validate_on_submit():
        try:
            directory = Directory(
                name=form.name.data,
                path=form.path.data,
                description=form.description.data,
                is_active=form.is_active.data
            )
            
            db.session.add(directory)
            db.session.commit()
            
            # 如果選擇建立實體目錄，則嘗試建立
            if form.create_physical_dir.data:
                try:
                    import os
                    import pwd
                    import grp
                    import shutil
                    
                    dir_path = form.path.data.rstrip('/')
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path, mode=0o755, exist_ok=True)
                        
                        # 設定目錄擁有者為 nobody:nobody
                        try:
                            nobody_uid = pwd.getpwnam('nobody').pw_uid
                            nobody_gid = grp.getgrnam('nobody').gr_gid
                            os.chown(dir_path, nobody_uid, nobody_gid)
                            flash(f'目錄創建成功，實體目錄已建立於: {dir_path} (nobody:nobody)', 'success')
                        except (KeyError, OSError) as e:
                            flash(f'目錄創建成功，實體目錄已建立於: {dir_path}，但設定擁有者失敗: {str(e)}', 'warning')
                    else:
                        flash(f'目錄創建成功，實體目錄已存在於: {dir_path}', 'info')
                except Exception as e:
                    flash(f'目錄創建成功，但建立實體目錄失敗: {str(e)}', 'warning')
            else:
                flash('目錄創建成功', 'success')
            
            # 根據設定決定是否同步配置
            if form.sync_config.data:
                sync_all_configs()
            
            log_action('create_directory', 'directory', directory.id, description_key='directory_created', name=directory.name)
            return redirect(url_for('permissions.directories'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'創建目錄失敗: {str(e)}', 'error')
    
    return render_template('permissions/create_directory.html', form=form)

@bp.route('/directories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_directory(id):
    """編輯目錄"""
    directory = Directory.query.get_or_404(id)
    form = DirectoryForm(original_directory=directory, obj=directory)
    
    if form.validate_on_submit():
        try:
            directory.name = form.name.data
            directory.path = form.path.data
            directory.description = form.description.data
            directory.is_active = form.is_active.data
            
            db.session.commit()
            
            # 根據設定決定是否同步配置
            if form.sync_config.data:
                sync_all_configs()
            
            flash('目錄更新成功', 'success')
            log_action('edit_directory', 'directory', directory.id, description_key='directory_edited', name=directory.name)
            return redirect(url_for('permissions.directories'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新目錄失敗: {str(e)}', 'error')
    
    return render_template('permissions/edit_directory.html', form=form, directory=directory)

@bp.route('/directories/<int:id>/delete', methods=['POST'])
@login_required
def delete_directory(id):
    """刪除目錄"""
    directory = Directory.query.get_or_404(id)
    name = directory.name
    path = directory.path
    
    # 檢查是否有權限依賴此目錄
    permission_count = DirectoryPermission.query.filter_by(directory_id=id).count()
    if permission_count > 0:
        flash(f'無法刪除目錄 {name}，因為仍有 {permission_count} 個權限設定', 'error')
        return redirect(url_for('permissions.directories'))
    
    # 檢查是否要刪除實體目錄
    delete_physical = request.form.get('delete_physical_dir') == 'true'
    
    try:
        # 先刪除資料庫記錄
        db.session.delete(directory)
        db.session.commit()
        
        # 如果選擇刪除實體目錄
        if delete_physical:
            try:
                import os
                import shutil
                dir_path = path.rstrip('/')
                
                if os.path.exists(dir_path):
                    if os.path.isdir(dir_path):
                        shutil.rmtree(dir_path)
                        flash(f'目錄 {name} 及實體目錄已成功刪除', 'success')
                    else:
                        flash(f'目錄 {name} 已刪除，但指定路徑不是目錄: {dir_path}', 'warning')
                else:
                    flash(f'目錄 {name} 已刪除，但實體目錄不存在: {dir_path}', 'info')
            except Exception as e:
                flash(f'目錄 {name} 已刪除，但刪除實體目錄失敗: {str(e)}', 'warning')
        else:
            flash(f'目錄 {name} 已刪除（實體目錄保留）', 'success')
        
        log_action('delete_directory', 'directory', id, description_key='directory_deleted', 
                  name=name, delete_physical=delete_physical)
        
    except Exception as e:
        db.session.rollback()
        flash(f'刪除目錄失敗: {str(e)}', 'error')
    
    return redirect(url_for('permissions.directories'))

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """創建權限設定"""
    form = PermissionForm()
    
    # 調試表單驗證
    if request.method == 'POST':
        print(f'=== DEBUG: Form submitted ===')
        print(f'Form data: {dict(request.form)}')
        print(f'Form validation result: {form.validate()}')
        print(f'Form errors: {form.errors}')
        print(f'Target type: {form.target_type.data}')
        print(f'Selected users: {form.selected_users.data}')
        print(f'Selected groups: {form.selected_groups.data}')
        print(f'Directory ID: {form.directory_id.data}')
        print('=== END DEBUG ===')
    
    if form.validate_on_submit():
        try:
            created_count = 0
            updated_count = 0
            target_type = form.target_type.data
            
            # 調試信息
            current_app.logger.info(f'Target type: {target_type}')
            current_app.logger.info(f'Selected users: {form.selected_users.data}')
            current_app.logger.info(f'Selected groups: {form.selected_groups.data}')
            
            # 獲取選中的目標列表
            if target_type == 'user':
                selected_targets = form.selected_users.data.split(',') if form.selected_users.data else []
            else:
                selected_targets = form.selected_groups.data.split(',') if form.selected_groups.data else []
            
            current_app.logger.info(f'Selected targets: {selected_targets}')
            
            # 驗證是否有選擇目標
            if not selected_targets or (len(selected_targets) == 1 and not selected_targets[0]):
                flash('請選擇至少一個目標', 'error')
                current_app.logger.warning('No targets selected')
                return render_template('permissions/create.html', form=form)
            
            # 為每個選中的目標創建權限設定
            for target_id in selected_targets:
                if not target_id.strip():
                    continue
                    
                target_id = int(target_id.strip())
                
                # 檢查是否已存在相同的權限設定
                existing = None
                if target_type == 'user':
                    existing = DirectoryPermission.query.filter_by(
                        directory_id=form.directory_id.data,
                        user_id=target_id
                    ).first()
                else:
                    existing = DirectoryPermission.query.filter_by(
                        directory_id=form.directory_id.data,
                        group_id=target_id
                    ).first()
                
                if existing:
                    # 更新現有權限
                    existing.can_read = form.can_read.data
                    existing.can_write = form.can_write.data
                    existing.can_delete = form.can_delete.data
                    updated_count += 1
                else:
                    # 創建新權限
                    permission = DirectoryPermission(
                        directory_id=form.directory_id.data,
                        can_read=form.can_read.data,
                        can_write=form.can_write.data,
                        can_delete=form.can_delete.data
                    )
                    
                    if target_type == 'user':
                        permission.user_id = target_id
                    else:
                        permission.group_id = target_id
                    
                    db.session.add(permission)
                    created_count += 1
            
            db.session.commit()
            
            # 提供適當的回饋訊息
            if created_count > 0 and updated_count > 0:
                flash(f'成功創建 {created_count} 個權限設定，更新 {updated_count} 個現有設定', 'success')
            elif created_count > 0:
                flash(f'成功創建 {created_count} 個權限設定', 'success')
            elif updated_count > 0:
                flash(f'成功更新 {updated_count} 個權限設定', 'success')
            
            # 根據設定決定是否同步配置
            if form.sync_config.data:
                sync_all_configs()
            else:
                # 只生成配置檔，不重新載入
                generate_and_reload_config()
            
            log_action('create_permission', 'permission', form.directory_id.data, 
                      description_key='permission_created', target_type=form.target_type.data, 
                      count=created_count + updated_count)
            return redirect(url_for('permissions.list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'設定權限失敗: {str(e)}', 'error')
    
    return render_template('permissions/create.html', form=form)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """編輯權限設定"""
    permission = DirectoryPermission.query.get_or_404(id)
    form = PermissionForm(obj=permission)
    
    # 設定表單初始值
    form.directory_id.data = permission.directory_id
    if permission.user_id:
        form.target_type.data = 'user'
        form.selected_users.data = str(permission.user_id)
    else:
        form.target_type.data = 'group'
        form.selected_groups.data = str(permission.group_id)
    
    if form.validate_on_submit():
        try:
            permission.can_read = form.can_read.data
            permission.can_write = form.can_write.data
            permission.can_delete = form.can_delete.data
            
            db.session.commit()
            
            # 根據設定決定是否同步配置
            if form.sync_config.data:
                sync_all_configs()
            else:
                # 只生成配置檔，不重新載入
                generate_and_reload_config()
            
            flash('權限設定已更新', 'success')
            log_action('edit_permission', 'permission', permission.id, description_key='permission_edited')
            return redirect(url_for('permissions.list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新權限失敗: {str(e)}', 'error')
    
    return render_template('permissions/edit.html', form=form, permission=permission)

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """刪除權限設定"""
    permission = DirectoryPermission.query.get_or_404(id)
    
    try:
        db.session.delete(permission)
        db.session.commit()
        
        # 生成配置檔
        generate_and_reload_config()
        
        flash('權限設定已刪除', 'success')
        log_action('delete_permission', 'permission', id, description_key='permission_deleted')
        
    except Exception as e:
        db.session.rollback()
        flash(f'刪除權限失敗: {str(e)}', 'error')
    
    return redirect(url_for('permissions.list'))

@bp.route('/matrix')
@login_required
def matrix():
    """權限矩陣視圖"""
    directories = Directory.query.filter_by(is_active=True).order_by(Directory.name).all()
    users = FtpUser.query.filter_by(is_enabled=True).order_by(FtpUser.username).all()
    groups = FtpGroup.query.order_by(FtpGroup.groupname).all()
    
    # 構建權限矩陣
    user_permissions = {}
    group_permissions = {}
    
    for user in users:
        user_permissions[user.id] = {}
        for directory in directories:
            perm = DirectoryPermission.query.filter_by(
                directory_id=directory.id, user_id=user.id
            ).first()
            user_permissions[user.id][directory.id] = perm
    
    for group in groups:
        group_permissions[group.id] = {}
        for directory in directories:
            perm = DirectoryPermission.query.filter_by(
                directory_id=directory.id, group_id=group.id
            ).first()
            group_permissions[group.id][directory.id] = perm
    
    return render_template('permissions/matrix.html',
                         directories=directories,
                         users=users,
                         groups=groups,
                         user_permissions=user_permissions,
                         group_permissions=group_permissions)

@bp.route('/api/targets/<target_type>')
@login_required
def api_targets(target_type):
    """獲取目標列表 (AJAX)"""
    if target_type == 'user':
        targets = [(u.id, f'{u.username} (UID: {u.uid})') 
                  for u in FtpUser.query.filter_by(is_enabled=True).order_by(FtpUser.username).all()]
    elif target_type == 'group':
        targets = [(g.id, f'{g.groupname} (GID: {g.gid})') 
                  for g in FtpGroup.query.order_by(FtpGroup.groupname).all()]
    else:
        targets = []
    
    return jsonify(targets)

@bp.route('/api/matrix/update', methods=['POST'])
@login_required
def api_update_matrix():
    """批量更新權限矩陣 (AJAX)"""
    data = request.get_json()
    
    try:
        directory_id = data.get('directory_id')
        target_type = data.get('target_type')  # 'user' or 'group'
        target_id = data.get('target_id')
        permission_type = data.get('permission_type')  # 'read', 'write', 'delete'
        value = data.get('value', False)
        
        # 查找或創建權限記錄
        if target_type == 'user':
            permission = DirectoryPermission.query.filter_by(
                directory_id=directory_id, user_id=target_id
            ).first()
            
            if not permission:
                permission = DirectoryPermission(
                    directory_id=directory_id,
                    user_id=target_id,
                    can_read=False,
                    can_write=False,
                    can_delete=False
                )
                db.session.add(permission)
        else:
            permission = DirectoryPermission.query.filter_by(
                directory_id=directory_id, group_id=target_id
            ).first()
            
            if not permission:
                permission = DirectoryPermission(
                    directory_id=directory_id,
                    group_id=target_id,
                    can_read=False,
                    can_write=False,
                    can_delete=False
                )
                db.session.add(permission)
        
        # 更新權限
        if permission_type == 'read':
            permission.can_read = value
        elif permission_type == 'write':
            permission.can_write = value
        elif permission_type == 'delete':
            permission.can_delete = value
        
        db.session.commit()
        
        # 如果所有權限都是False，刪除該記錄
        if not (permission.can_read or permission.can_write or permission.can_delete):
            db.session.delete(permission)
            db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

def generate_and_reload_config():
    """生成配置檔並重新載入服務"""
    try:
        from ..proftpd import generate_proftpd_config
        success, message = generate_proftpd_config()
        if success:
            reload_proftpd()
        return success, message
    except Exception as e:
        current_app.logger.error(f'配置生成失敗: {e}')
        return False, str(e)

@bp.route('/sync', methods=['POST'])
@login_required
def sync_config():
    """手動同步配置"""
    try:
        # 生成並重新載入配置
        generate_and_reload_config()
        flash('配置已同步', 'success')
        log_action('sync_config', 'system', None, description_key='config_synced_manually')
    except Exception as e:
        flash(f'同步失敗: {str(e)}', 'error')
    
    return redirect(url_for('permissions.list'))

def sync_all_configs():
    """同步所有配置檔案（用戶、群組、權限）並重新載入服務"""
    try:
        from ..proftpd import validate_proftpd_config
        
        # 同步用戶和群組檔案以及動態配置
        success, message = sync_proftpd_files()
        
        if success:
            # 驗證配置
            validate_success, validate_message = validate_proftpd_config()
            if validate_success:
                # 重新載入服務
                reload_success, reload_message = reload_proftpd()
                if reload_success:
                    flash('所有配置已同步並重新載入服務', 'success')
                else:
                    flash(f'配置同步成功，但服務重新載入失敗: {reload_message}', 'warning')
            else:
                flash(f'配置同步成功，但驗證失敗: {validate_message}', 'warning')
        else:
            flash(f'配置同步失敗: {message}', 'error')
        
        log_action('sync_all_config', 'config', None, description_key='all_config_synced')
        
    except Exception as e:
        flash(f'配置同步失敗: {str(e)}', 'error')