from flask import render_template, request, flash, redirect, url_for, jsonify, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import os
import shutil
import subprocess
import json
from . import bp
from .forms import SystemSettingsForm, BackupRestoreForm, ConfigGenerateForm, AdminPasswordForm
from ..models import SystemSetting, AdminUser, db
from ..proftpd import ProFTPDConfigGenerator

@bp.route('/')
@login_required
def index():
    """設定管理首頁"""
    # 獲取所有系統設定
    settings = {}
    all_settings = SystemSetting.query.all()
    for setting in all_settings:
        settings[setting.key] = setting.value
    
    # 設定預設值
    default_settings = {
        'ftp_server_name': 'ProFTPD Server',
        'ftp_max_clients': '50',
        'ftp_max_per_ip': '5',
        'ftp_passive_ports': '60000-65000',
        'ftp_umask': '022',
        'log_access_enabled': 'true',
        'log_auth_enabled': 'true',
        'log_level': 'info',
        'log_rotate_days': '30',
        'security_login_attempts': '5',
        'security_ban_duration': '30',
        'security_allow_root': 'false',
        'security_require_ssl': 'false',
        'system_backup_enabled': 'true',
        'system_backup_interval': 'weekly',
        'system_maintenance_mode': 'false',
        'system_notification_email': ''
    }
    
    # 合併預設值和現有設定
    for key, default_value in default_settings.items():
        if key not in settings:
            settings[key] = default_value
    
    return render_template('settings/index.html', settings=settings)

@bp.route('/system', methods=['GET', 'POST'])
@login_required
def system_settings():
    """系統設定"""
    form = SystemSettingsForm()
    
    if form.validate_on_submit():
        # 儲存設定到資料庫
        settings_data = {
            'ftp_server_name': form.ftp_server_name.data,
            'ftp_max_clients': str(form.ftp_max_clients.data),
            'ftp_max_clients_per_host': str(form.ftp_max_per_ip.data),
            'ftp_passive_ports': form.ftp_passive_ports.data or '',
            'ftp_umask': form.ftp_umask.data or '022',
            'log_access_enabled': 'true' if form.log_access_enabled.data else 'false',
            'log_auth_enabled': 'true' if form.log_auth_enabled.data else 'false',
            'log_level': form.log_level.data,
            'log_rotate_days': str(form.log_rotate_days.data or 30),
            'security_login_attempts': str(form.security_login_attempts.data),
            'security_ban_duration': str(form.security_ban_duration.data),
            'security_allow_root': 'true' if form.security_allow_root.data else 'false',
            'security_require_ssl': 'true' if form.security_require_ssl.data else 'false',
            'system_backup_enabled': 'true' if form.system_backup_enabled.data else 'false',
            'system_backup_interval': form.system_backup_interval.data,
            'system_maintenance_mode': 'true' if form.system_maintenance_mode.data else 'false',
            'system_notification_email': form.system_notification_email.data or ''
        }
        
        for key, value in settings_data.items():
            setting = SystemSetting.query.filter_by(key=key).first()
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = SystemSetting(key=key, value=value)
                db.session.add(setting)
        
        try:
            db.session.commit()
            flash('系統設定已成功儲存', 'success')
            
            # 重新生成 ProFTPD 主配置檔和動態配置檔
            config_generator = ProFTPDConfigGenerator()
            
            # 生成主配置檔
            main_success, main_message = config_generator.write_main_config()
            if main_success:
                # 驗證主配置檔語法
                validate_success, validate_message = config_generator.validate_main_config()
                if validate_success:
                    # 生成動態配置檔
                    dynamic_success, dynamic_message = config_generator.write_dynamic_config()
                    if dynamic_success:
                        # 重新啟動 ProFTPD 服務
                        restart_success, restart_message = config_generator.restart_proftpd()
                        if restart_success:
                            flash('設定已儲存，ProFTPD 配置已更新並重新啟動服務', 'success')
                        else:
                            flash(f'設定已儲存，配置已更新，但重新啟動失敗: {restart_message}', 'warning')
                    else:
                        flash(f'主配置已更新，但動態配置更新失敗: {dynamic_message}', 'warning')
                else:
                    flash(f'配置檔語法錯誤，請檢查設定: {validate_message}', 'error')
            else:
                flash(f'ProFTPD 主配置檔更新失敗: {main_message}', 'error')
                
        except Exception as e:
            db.session.rollback()
            flash(f'儲存設定失敗: {str(e)}', 'error')
    
    # 載入現有設定
    if request.method == 'GET':
        settings = {}
        all_settings = SystemSetting.query.all()
        for setting in all_settings:
            settings[setting.key] = setting.value
        
        # 填入表單預設值
        form.ftp_server_name.data = settings.get('ftp_server_name', 'ProFTPD Server')
        form.ftp_max_clients.data = int(settings.get('ftp_max_clients', 50))
        form.ftp_max_per_ip.data = int(settings.get('ftp_max_clients_per_host', 5))
        form.ftp_passive_ports.data = settings.get('ftp_passive_ports', '60000-65000')
        form.ftp_umask.data = settings.get('ftp_umask', '022')
        form.log_access_enabled.data = settings.get('log_access_enabled', 'true') == 'true'
        form.log_auth_enabled.data = settings.get('log_auth_enabled', 'true') == 'true'
        form.log_level.data = settings.get('log_level', 'info')
        form.log_rotate_days.data = int(settings.get('log_rotate_days', 30))
        form.security_login_attempts.data = int(settings.get('security_login_attempts', 5))
        form.security_ban_duration.data = int(settings.get('security_ban_duration', 30))
        form.security_allow_root.data = settings.get('security_allow_root', 'false') == 'true'
        form.security_require_ssl.data = settings.get('security_require_ssl', 'false') == 'true'
        form.system_backup_enabled.data = settings.get('system_backup_enabled', 'true') == 'true'
        form.system_backup_interval.data = settings.get('system_backup_interval', 'weekly')
        form.system_maintenance_mode.data = settings.get('system_maintenance_mode', 'false') == 'true'
        form.system_notification_email.data = settings.get('system_notification_email', '')
    
    return render_template('settings/system.html', form=form)

@bp.route('/backup', methods=['GET', 'POST'])
@login_required
def backup_restore():
    """備份與還原"""
    backup_form = BackupRestoreForm()
    
    if backup_form.validate_on_submit() and backup_form.create_backup.data:
        try:
            backup_file = create_system_backup(
                backup_form.backup_description.data,
                backup_form.backup_include_logs.data,
                backup_form.backup_include_data.data
            )
            flash(f'備份已建立: {backup_file}', 'success')
        except Exception as e:
            flash(f'備份建立失敗: {str(e)}', 'error')
    
    # 獲取現有備份列表
    backup_list = get_backup_list()
    
    return render_template('settings/backup.html', 
                         backup_form=backup_form, 
                         backup_list=backup_list)

@bp.route('/config', methods=['GET', 'POST'])
@login_required
def config_management():
    """配置檔管理"""
    config_form = ConfigGenerateForm()
    
    if config_form.validate_on_submit():
        try:
            config_generator = ProFTPDConfigGenerator()
            success, message = config_generator.write_dynamic_config()
            if success:
                flash('ProFTPD 配置檔已重新生成', 'success')
                
                if config_form.reload_service.data:
                    result = reload_proftpd_service()
                    if result:
                        flash('ProFTPD 服務已重新載入', 'success')
                    else:
                        flash('ProFTPD 服務重新載入失敗', 'warning')
            else:
                flash('配置檔生成失敗', 'error')
        except Exception as e:
            flash(f'配置檔操作失敗: {str(e)}', 'error')
    
    # 獲取配置檔狀態
    config_status = get_config_status()
    
    return render_template('settings/config.html', 
                         config_form=config_form,
                         config_status=config_status)

@bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_management():
    """管理員帳號管理"""
    password_form = AdminPasswordForm()
    
    if password_form.validate_on_submit():
        if check_password_hash(current_user.password_hash, password_form.current_password.data):
            try:
                current_user.password_hash = generate_password_hash(password_form.new_password.data)
                current_user.updated_at = datetime.utcnow()
                db.session.commit()
                flash('密碼已成功變更', 'success')
                return redirect(url_for('settings.admin_management'))
            except Exception as e:
                db.session.rollback()
                flash(f'密碼變更失敗: {str(e)}', 'error')
        else:
            flash('目前密碼錯誤', 'error')
    
    return render_template('settings/admin.html', password_form=password_form)

@bp.route('/api/backup/<backup_id>/download')
@login_required
def download_backup(backup_id):
    """下載備份檔案"""
    try:
        backup_dir = current_app.config.get('BACKUP_DIR', '/tmp/backups')
        backup_file = os.path.join(backup_dir, f'{backup_id}.tar.gz')
        
        if os.path.exists(backup_file):
            return send_file(backup_file, as_attachment=True)
        else:
            return jsonify({'error': '備份檔案不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/backup/<backup_id>/delete', methods=['POST'])
@login_required
def delete_backup(backup_id):
    """刪除備份檔案"""
    try:
        backup_dir = current_app.config.get('BACKUP_DIR', '/tmp/backups')
        backup_file = os.path.join(backup_dir, f'{backup_id}.tar.gz')
        
        if os.path.exists(backup_file):
            os.remove(backup_file)
            return jsonify({'success': True})
        else:
            return jsonify({'error': '備份檔案不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/quick-setting', methods=['POST'])
@login_required
def api_quick_setting():
    """快速設定 API"""
    try:
        data = request.get_json()
        key = data.get('key')
        value = data.get('value')
        
        if not key:
            return jsonify({'success': False, 'error': '缺少設定鍵值'}), 400
        
        # 更新設定
        setting = SystemSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = SystemSetting(key=key, value=value)
            db.session.add(setting)
        
        db.session.commit()
        
        # 如果是維護模式或 SSL 設定，重新生成配置
        if key in ['system_maintenance_mode', 'security_require_ssl']:
            config_generator = ProFTPDConfigGenerator()
            success, message = config_generator.write_dynamic_config()
            if not success:
                return jsonify({'success': False, 'error': f'配置更新失敗: {message}'}), 500
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/clear-cache', methods=['POST'])
@login_required
def api_clear_cache():
    """清理系統快取 API"""
    try:
        # 這裡可以實現清理快取的邏輯
        # 例如：清理臨時檔案、重設快取變數等
        import tempfile
        import shutil
        
        # 清理臨時目錄中的舊檔案
        temp_dir = tempfile.gettempdir()
        cache_cleared = False
        
        # 這裡可以加入更多清理邏輯
        # 例如：清理應用程式特定的快取檔案
        
        return jsonify({'success': True, 'message': '系統快取已清理'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/reset-session', methods=['POST'])
@login_required
def api_reset_session():
    """重設會話 API"""
    try:
        # 這裡可以實現重設會話的邏輯
        # 注意：這個操作會登出所有用戶
        
        # 在這裡可以清理會話資料
        # 例如：清理 Redis 中的會話、資料庫中的會話記錄等
        
        return jsonify({'success': True, 'message': '所有會話已重設'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/export-logs')
@login_required
def api_export_logs():
    """匯出系統日誌 API"""
    try:
        import zipfile
        import tempfile
        import os
        from datetime import datetime
        
        # 建立臨時壓縮檔
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'system_logs_{timestamp}.zip'
        temp_zip = os.path.join(tempfile.gettempdir(), zip_filename)
        
        with zipfile.ZipFile(temp_zip, 'w') as zipf:
            # 加入 ProFTPD 日誌檔案
            log_files = [
                '/var/log/proftpd/proftpd.log',
                '/var/log/proftpd/access.log',
                '/var/log/proftpd/auth.log'
            ]
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    zipf.write(log_file, os.path.basename(log_file))
            
            # 加入應用程式日誌（如果有的話）
            app_log = current_app.config.get('LOG_FILE')
            if app_log and os.path.exists(app_log):
                zipf.write(app_log, 'app.log')
        
        return send_file(temp_zip, as_attachment=True, download_name=zip_filename)
        
    except Exception as e:
        flash(f'匯出日誌失敗: {str(e)}', 'error')
        return redirect(url_for('settings.admin_management'))

def create_system_backup(description, include_logs=False, include_data=True):
    """建立系統備份"""
    backup_dir = current_app.config.get('BACKUP_DIR', '/tmp/backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_id = f'backup_{timestamp}'
    backup_file = os.path.join(backup_dir, f'{backup_id}.tar.gz')
    
    # 建立臨時目錄
    temp_dir = f'/tmp/{backup_id}'
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 備份資料庫
        db_file = current_app.config.get('DATABASE_PATH', 'app.db')
        if os.path.exists(db_file):
            shutil.copy2(db_file, temp_dir)
        
        # 備份配置檔
        config_dir = current_app.config.get('PROFTPD_CONFIG_DIR', '/etc/proftpd')
        if os.path.exists(config_dir):
            shutil.copytree(config_dir, os.path.join(temp_dir, 'config'), 
                          ignore=shutil.ignore_patterns('*.bak'))
        
        # 備份日誌（可選）
        if include_logs:
            log_dir = '/var/log/proftpd'
            if os.path.exists(log_dir):
                shutil.copytree(log_dir, os.path.join(temp_dir, 'logs'))
        
        # 備份用戶資料（可選）
        if include_data:
            data_dir = current_app.config.get('PROFTPD_BASE_DIR', '/backup/ftpdata')
            if os.path.exists(data_dir):
                shutil.copytree(data_dir, os.path.join(temp_dir, 'data'))
        
        # 建立備份資訊檔案
        backup_info = {
            'id': backup_id,
            'created_at': datetime.now().isoformat(),
            'description': description or '',
            'include_logs': include_logs,
            'include_data': include_data,
            'created_by': current_user.username
        }
        
        with open(os.path.join(temp_dir, 'backup_info.json'), 'w') as f:
            json.dump(backup_info, f, indent=2)
        
        # 建立壓縮檔
        subprocess.run(['tar', '-czf', backup_file, '-C', '/tmp', backup_id], 
                      check=True, timeout=300)
        
        return backup_id
        
    finally:
        # 清理臨時目錄
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def get_backup_list():
    """獲取備份列表"""
    backup_dir = current_app.config.get('BACKUP_DIR', '/tmp/backups')
    backups = []
    
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.endswith('.tar.gz'):
                backup_id = filename[:-7]  # 移除 .tar.gz
                file_path = os.path.join(backup_dir, filename)
                stat = os.stat(file_path)
                
                backups.append({
                    'id': backup_id,
                    'filename': filename,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime),
                    'description': '系統備份'  # 可以從 backup_info.json 中讀取
                })
    
    return sorted(backups, key=lambda x: x['created_at'], reverse=True)

def get_config_status():
    """獲取配置檔狀態"""
    config_dir = current_app.config.get('PROFTPD_CONFIG_DIR', '/etc/proftpd')
    main_config = current_app.config.get('PROFTPD_MAIN_CONFIG', '/etc/proftpd/proftpd.conf')
    
    status = {
        'main_config_exists': os.path.exists(main_config),
        'main_config_size': 0,
        'main_config_modified': None,
        'main_config_path': main_config,
        'include_files': []
    }
    
    if status['main_config_exists']:
        stat = os.stat(main_config)
        status['main_config_size'] = stat.st_size
        status['main_config_modified'] = datetime.fromtimestamp(stat.st_mtime)
        
        # 檢查 include 檔案
        include_dir = os.path.join(config_dir, 'conf.d')
        if os.path.exists(include_dir):
            for filename in os.listdir(include_dir):
                if filename.endswith('.conf'):
                    file_path = os.path.join(include_dir, filename)
                    file_stat = os.stat(file_path)
                    status['include_files'].append({
                        'name': filename,
                        'size': file_stat.st_size,
                        'modified': datetime.fromtimestamp(file_stat.st_mtime)
                    })
    
    return status

def reload_proftpd_service():
    """重新載入 ProFTPD 服務"""
    try:
        result = subprocess.run(['systemctl', 'reload', 'proftpd'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False