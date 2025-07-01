from flask import render_template, redirect, url_for, flash, request, make_response, jsonify
from flask_login import login_required
from flask_babel import _
from . import bp
from ..proftpd import ProFTPDConfigGenerator, validate_proftpd_config, backup_proftpd_config
from ..utils import log_action, sync_proftpd_files, reload_proftpd
import os

@bp.route('/')
@login_required
def index():
    """Configuration management homepage"""
    generator = ProFTPDConfigGenerator()
    
    # 檢查配置檔狀態
    config_exists = os.path.exists(generator.dynamic_config_file)
    config_size = 0
    config_mtime = None
    
    if config_exists:
        stat = os.stat(generator.dynamic_config_file)
        config_size = stat.st_size
        config_mtime = stat.st_mtime
    
    return render_template('config/index.html', 
                         config_exists=config_exists,
                         config_size=config_size,
                         config_mtime=config_mtime,
                         config_file=generator.dynamic_config_file)

@bp.route('/preview', methods=['GET', 'POST'])
@login_required
def preview():
    """Preview configuration file content"""
    generator = ProFTPDConfigGenerator()
    try:
        from ..models import SystemSetting, db
        
        # 檢查預覽類型
        preview_type = 'dynamic'
        if request.method == 'POST':
            preview_type = request.form.get('preview_type', 'dynamic')
            # 如果是主配置預覽，需要先保存表單數據到臨時設定
            if preview_type == 'main':
                temp_settings = {}
                for key in request.form:
                    if key.startswith('ftp_') or key.startswith('log_') or key.startswith('security_') or key.startswith('system_'):
                        temp_settings[key] = request.form.get(key)
                
                # 臨時更新設定用於預覽
                original_values = {}
                for key, value in temp_settings.items():
                    setting = SystemSetting.query.filter_by(key=key).first()
                    if setting:
                        original_values[key] = setting.value
                        setting.value = value
                    else:
                        new_setting = SystemSetting(key=key, value=value)
                        db.session.add(new_setting)
                        original_values[key] = None
                
                try:
                    # 生成預覽
                    config_content = generator.get_config_preview('main')
                    
                    # 恢復原始設定
                    for key, original_value in original_values.items():
                        setting = SystemSetting.query.filter_by(key=key).first()
                        if original_value is None:
                            if setting:
                                db.session.delete(setting)
                        else:
                            setting.value = original_value
                    
                    db.session.rollback()  # 不提交變更
                    
                except Exception as preview_error:
                    # 恢復原始設定
                    for key, original_value in original_values.items():
                        setting = SystemSetting.query.filter_by(key=key).first()
                        if original_value is None:
                            if setting:
                                db.session.delete(setting)
                        else:
                            setting.value = original_value
                    
                    db.session.rollback()
                    raise preview_error
            else:
                config_content = generator.get_config_preview()
        else:
            config_content = generator.get_config_preview()
        
        # 檢查是否為 AJAX 請求
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            # 返回 JSON 格式
            from ..utils import generate_ftpd_passwd, generate_ftpd_group
            return jsonify({
                'main_config': generator.generate_main_config(),
                'users_config': generate_ftpd_passwd(),
                'directories_config': generator.generate_dynamic_config()
            })
        
        # 如果是 POST 請求（從系統設置頁面的 AJAX 調用），直接返回配置內容
        if request.method == 'POST':
            return config_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
        # 如果是 GET 請求，返回完整的預覽頁面
        return render_template('config/preview.html', config_content=config_content)
    except Exception as e:
        if request.method == 'POST':
            return f"{_('Failed to generate configuration preview')}: {str(e)}", 500, {'Content-Type': 'text/plain; charset=utf-8'}
        flash(f"{_('Failed to generate configuration preview')}: {str(e)}", 'error')
        return redirect(url_for('config.index'))

@bp.route('/generate', methods=['POST'])
@login_required
def generate():
    """Generate configuration file"""
    try:
        # 備份現有配置
        backup_success, backup_message = backup_proftpd_config()
        if not backup_success:
            flash(f"{_('Backup failed')}: {backup_message}", 'warning')
        
        # 生成新配置
        generator = ProFTPDConfigGenerator()
        success, message = generator.write_dynamic_config()
        
        if success:
            # 驗證配置檔語法
            validate_success, validate_message = validate_proftpd_config()
            if validate_success:
                flash(_('Configuration file generated successfully and passed syntax validation'), 'success')
            else:
                flash(f"{_('Configuration file generated successfully, but syntax validation failed')}: {validate_message}", 'warning')
            
            log_action('generate_config', 'config', None, description_key='config_generated')
        else:
            flash(f"{_('Configuration file generation failed')}: {message}", 'error')
    
    except Exception as e:
        flash(f"{_('Configuration file generation failed')}: {str(e)}", 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/validate', methods=['POST'])
@login_required
def validate():
    """Validate configuration file"""
    try:
        success, message = validate_proftpd_config()
        
        # 檢查是否為 AJAX 請求
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({
                'valid': success,
                'message': message
            })
        
        if success:
            flash(f"{_('Configuration file validation successful')}: {message}", 'success')
        else:
            flash(f"{_('Configuration file validation failed')}: {message}", 'error')
        
        log_action('validate_config', 'config', None, description_key='config_validated')
        
    except Exception as e:
        error_message = f"{_('Configuration file validation failed')}: {str(e)}"
        
        # 檢查是否為 AJAX 請求
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({
                'valid': False,
                'error': str(e)
            })
        
        flash(error_message, 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/reload', methods=['POST'])
@login_required
def reload():
    """Reload ProFTPD service"""
    try:
        success, message = reload_proftpd()
        if success:
            flash(_('ProFTPD service reloaded successfully'), 'success')
        else:
            flash(f"{_('ProFTPD service reload failed')}: {message}", 'error')
        
        log_action('reload_proftpd', 'service', None, description_key='proftpd_reloaded')
        
    except Exception as e:
        flash(f"{_('Service reload failed')}: {str(e)}", 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/backup', methods=['POST'])
@login_required
def backup():
    """Manual backup configuration file"""
    try:
        success, message = backup_proftpd_config()
        if success:
            flash(f"{_('Configuration file backup successful')}: {message}", 'success')
        else:
            flash(f"{_('Configuration file backup failed')}: {message}", 'error')
        
        log_action('backup_config', 'config', None, description_key='config_backed_up')
        
    except Exception as e:
        flash(f"{_('Configuration file backup failed')}: {str(e)}", 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/download')
@login_required
def download():
    """Download configuration file"""
    try:
        generator = ProFTPDConfigGenerator()
        config_content = generator.get_config_preview()
        
        response = make_response(config_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = 'attachment; filename=dynamic.conf'
        
        log_action('download_config', 'config', None, description_key='config_downloaded')
        return response
        
    except Exception as e:
        flash(f"{_('Download configuration file failed')}: {str(e)}", 'error')
        return redirect(url_for('config.index'))

@bp.route('/sync_all', methods=['POST'])
@login_required
def sync_all():
    """Sync all configuration files (users, groups, permissions)"""
    try:
        # 同步用戶和群組檔案以及動態配置
        success, message = sync_proftpd_files()
        
        if success:
            # 驗證配置
            validate_success, validate_message = validate_proftpd_config()
            if validate_success:
                # 重新載入服務
                reload_success, reload_message = reload_proftpd()
                if reload_success:
                    flash(_('All configurations synced and service reloaded'), 'success')
                else:
                    flash(f"{_('Configuration synced successfully, but service reload failed')}: {reload_message}", 'warning')
            else:
                flash(f"{_('Configuration synced successfully, but validation failed')}: {validate_message}", 'warning')
        else:
            flash(f"{_('Configuration sync failed')}: {message}", 'error')
        
        log_action('sync_all_config', 'config', None, description_key='all_config_synced')
        
    except Exception as e:
        flash(f"{_('Configuration sync failed')}: {str(e)}", 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/view')
@login_required
def view():
    """View configuration file content"""
    from flask import current_app
    filename = request.args.get('file', 'main')
    
    try:
        if filename == 'main':
            config_file = current_app.config.get('PROFTPD_MAIN_CONFIG', '/etc/proftpd/proftpd.conf')
        else:
            # 安全檢查，只允許檢視特定目錄下的配置檔
            config_dir = current_app.config.get('PROFTPD_CONFIG_DIR', '/etc/proftpd')
            config_file = os.path.join(config_dir, filename)
            
            # 確保檔案路徑在允許的目錄內
            if not config_file.startswith(config_dir):
                return _('Access to this file is not allowed'), 403
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return _('File does not exist'), 404
            
    except Exception as e:
        return f"{_('Failed to read file')}: {str(e)}", 500