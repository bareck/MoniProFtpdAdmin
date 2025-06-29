from flask import render_template, redirect, url_for, flash, request, make_response, jsonify
from flask_login import login_required
from . import bp
from ..proftpd import ProFTPDConfigGenerator, validate_proftpd_config, backup_proftpd_config
from ..utils import log_action, sync_proftpd_files, reload_proftpd
import os

@bp.route('/')
@login_required
def index():
    """配置管理首頁"""
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
    """預覽配置檔內容"""
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
            return f'生成配置預覽失敗: {str(e)}', 500, {'Content-Type': 'text/plain; charset=utf-8'}
        flash(f'生成配置預覽失敗: {str(e)}', 'error')
        return redirect(url_for('config.index'))

@bp.route('/generate', methods=['POST'])
@login_required
def generate():
    """生成配置檔"""
    try:
        # 備份現有配置
        backup_success, backup_message = backup_proftpd_config()
        if not backup_success:
            flash(f'備份失敗: {backup_message}', 'warning')
        
        # 生成新配置
        generator = ProFTPDConfigGenerator()
        success, message = generator.write_dynamic_config()
        
        if success:
            # 驗證配置檔語法
            validate_success, validate_message = validate_proftpd_config()
            if validate_success:
                flash('配置檔生成成功並通過語法驗證', 'success')
            else:
                flash(f'配置檔生成成功，但語法驗證失敗: {validate_message}', 'warning')
            
            log_action('generate_config', 'config', None, '生成 ProFTPD 配置檔')
        else:
            flash(f'配置檔生成失敗: {message}', 'error')
    
    except Exception as e:
        flash(f'配置檔生成失敗: {str(e)}', 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/validate', methods=['POST'])
@login_required
def validate():
    """驗證配置檔"""
    try:
        success, message = validate_proftpd_config()
        
        # 檢查是否為 AJAX 請求
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({
                'valid': success,
                'message': message
            })
        
        if success:
            flash(f'配置檔驗證成功: {message}', 'success')
        else:
            flash(f'配置檔驗證失敗: {message}', 'error')
        
        log_action('validate_config', 'config', None, '驗證 ProFTPD 配置檔')
        
    except Exception as e:
        error_message = f'配置檔驗證失敗: {str(e)}'
        
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
    """重新載入 ProFTPD 服務"""
    try:
        success, message = reload_proftpd()
        if success:
            flash('ProFTPD 服務重新載入成功', 'success')
        else:
            flash(f'ProFTPD 服務重新載入失敗: {message}', 'error')
        
        log_action('reload_proftpd', 'service', None, '重新載入 ProFTPD 服務')
        
    except Exception as e:
        flash(f'服務重新載入失敗: {str(e)}', 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/backup', methods=['POST'])
@login_required
def backup():
    """手動備份配置檔"""
    try:
        success, message = backup_proftpd_config()
        if success:
            flash(f'配置檔備份成功: {message}', 'success')
        else:
            flash(f'配置檔備份失敗: {message}', 'error')
        
        log_action('backup_config', 'config', None, '手動備份 ProFTPD 配置檔')
        
    except Exception as e:
        flash(f'配置檔備份失敗: {str(e)}', 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/download')
@login_required
def download():
    """下載配置檔"""
    try:
        generator = ProFTPDConfigGenerator()
        config_content = generator.get_config_preview()
        
        response = make_response(config_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = 'attachment; filename=dynamic.conf'
        
        log_action('download_config', 'config', None, '下載 ProFTPD 配置檔')
        return response
        
    except Exception as e:
        flash(f'下載配置檔失敗: {str(e)}', 'error')
        return redirect(url_for('config.index'))

@bp.route('/sync_all', methods=['POST'])
@login_required
def sync_all():
    """同步所有配置檔案（用戶、群組、權限）"""
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
                    flash('所有配置已同步並重新載入服務', 'success')
                else:
                    flash(f'配置同步成功，但服務重新載入失敗: {reload_message}', 'warning')
            else:
                flash(f'配置同步成功，但驗證失敗: {validate_message}', 'warning')
        else:
            flash(f'配置同步失敗: {message}', 'error')
        
        log_action('sync_all_config', 'config', None, '同步所有 ProFTPD 配置')
        
    except Exception as e:
        flash(f'配置同步失敗: {str(e)}', 'error')
    
    return redirect(url_for('config.index'))

@bp.route('/view')
@login_required
def view():
    """檢視配置檔內容"""
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
                return "不允許存取此檔案", 403
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "檔案不存在", 404
            
    except Exception as e:
        return f"讀取檔案失敗: {str(e)}", 500