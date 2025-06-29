from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from . import bp
from ..models import FtpUser, FtpGroup, Directory, AdminUser, AccessLog, db
from ..utils import get_disk_usage
from datetime import datetime, timedelta

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    """儀表板首頁"""
    # 統計資料
    stats = {
        'total_users': FtpUser.query.count(),
        'active_users': FtpUser.query.filter_by(is_enabled=True).count(),
        'total_groups': FtpGroup.query.count(),
        'total_directories': Directory.query.filter_by(is_active=True).count(),
    }
    
    # 最近的活動記錄
    recent_logs = AccessLog.query.order_by(AccessLog.created_at.desc()).limit(10).all()
    
    # 磁碟使用量（如果目錄存在）
    from flask import current_app
    base_dir = current_app.config.get('PROFTPD_BASE_DIR', '/backup/ftpdata')
    disk_usage = get_disk_usage(base_dir) if base_dir else "N/A"
    
    return render_template('main/index.html', 
                         stats=stats, 
                         recent_logs=recent_logs,
                         disk_usage=disk_usage)

@bp.route('/profile')
@login_required
def profile():
    """用戶個人資料頁面"""
    return render_template('main/profile.html')