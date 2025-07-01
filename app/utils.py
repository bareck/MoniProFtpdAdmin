from flask import request, current_app
from flask_login import current_user
from .models import AccessLog, db
import subprocess
import os

def log_action(action, target_type=None, target_id=None, description=None, description_key=None, **params):
    """記錄管理操作
    
    Args:
        action: 操作類型
        target_type: 目標類型 (user, group, directory, setting)
        target_id: 目標ID
        description: 傳統描述文字（向後兼容）
        description_key: 翻譯鍵值
        **params: 翻譯參數
    """
    try:
        import json
        
        # 如果提供了翻譯鍵值，優先使用
        if description_key:
            description_params = json.dumps(params, ensure_ascii=False) if params else None
        else:
            description_params = None
            
        log = AccessLog(
            admin_user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            description=description,
            description_key=description_key,
            description_params=description_params,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f'Failed to log action: {e}')

def reload_proftpd():
    """重新載入 ProFTPD 配置"""
    try:
        result = subprocess.run(['sudo', 'systemctl', 'reload', 'proftpd'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True, "ProFTPD 配置已重新載入"
        else:
            return False, f"重新載入失敗: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "重新載入超時"
    except Exception as e:
        return False, f"重新載入錯誤: {str(e)}"

def get_next_uid():
    """取得下一個可用的 UID"""
    from .models import FtpUser
    max_uid = db.session.query(db.func.max(FtpUser.uid)).scalar() or 5000
    return max_uid + 1

def get_next_gid():
    """取得下一個可用的 GID"""
    from .models import FtpGroup
    max_gid = db.session.query(db.func.max(FtpGroup.gid)).scalar() or 5000
    return max_gid + 1

def generate_ftpd_passwd():
    """生成 ProFTPD 用戶認證檔案內容"""
    from .models import FtpUser
    users = FtpUser.query.filter_by(is_enabled=True).all()
    
    lines = []
    for user in users:
        # 格式: username:password:uid:gid:gecos:homedir:shell
        lines.append(f"{user.username}:{user.password_hash}:{user.uid}:{user.gid}:{user.comment or ''}:{user.home_directory}:{user.shell}")
    
    return '\n'.join(lines)

def generate_ftpd_group():
    """生成 ProFTPD 群組檔案內容"""
    from .models import FtpGroup, GroupMembership
    groups = FtpGroup.query.all()
    
    lines = []
    for group in groups:
        members = [membership.user.username for membership in group.members if membership.user.is_enabled]
        member_list = ','.join(members)
        # 格式: groupname:password:gid:member1,member2,...
        lines.append(f"{group.groupname}::{group.gid}:{member_list}")
    
    return '\n'.join(lines)

def sync_proftpd_files():
    """同步 ProFTPD 用戶和群組檔案"""
    try:
        passwd_content = generate_ftpd_passwd()
        group_content = generate_ftpd_group()
        
        # 取得檔案路徑
        passwd_file = current_app.config['PROFTPD_PASSWD_FILE']
        group_file = current_app.config['PROFTPD_GROUP_FILE']
        
        # 確保目錄存在
        config_dir = os.path.dirname(passwd_file)
        os.makedirs(config_dir, exist_ok=True)
        
        # 寫入用戶檔案
        current_app.logger.info(f'Writing to passwd file: {passwd_file}')
        with open(passwd_file, 'w') as f:
            f.write(passwd_content)
        
        # 寫入群組檔案
        current_app.logger.info(f'Writing to group file: {group_file}')
        with open(group_file, 'w') as f:
            f.write(group_content)
        
        # 設定檔案權限
        os.chmod(passwd_file, 0o600)
        os.chmod(group_file, 0o600)
        
        current_app.logger.info(f'Synced {len(passwd_content.splitlines())} users and {len(group_content.splitlines())} groups')
        
        # 生成動態配置檔
        from .proftpd import generate_proftpd_config
        config_success, config_message = generate_proftpd_config()
        
        if not config_success:
            return False, f"用戶檔案同步成功，但配置檔生成失敗: {config_message}"
        
        return True, "ProFTPD 檔案和配置已同步"
    except PermissionError as e:
        return False, f"權限錯誤: {str(e)} - 請確保應用程式有寫入 ProFTPD 配置目錄的權限"
    except Exception as e:
        current_app.logger.error(f"同步 ProFTPD 檔案失敗: {e}")
        return False, f"同步失敗: {str(e)}"

def get_disk_usage(path):
    """取得目錄磁碟使用量"""
    try:
        result = subprocess.run(['du', '-sh', path], capture_output=True, text=True)
        if result.returncode == 0:
            size = result.stdout.split('\t')[0]
            return size.strip()
        return "N/A"
    except:
        return "N/A"

def get_ftp_connections():
    """取得目前 FTP 連線"""
    try:
        result = subprocess.run(['ftpwho'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        return "無法取得連線資訊"
    except:
        return "ftpwho 指令不可用"