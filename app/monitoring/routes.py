from flask import render_template, jsonify, request, current_app
from flask_login import login_required
from datetime import datetime, timedelta
from . import bp
from ..models import FtpUser, FtpGroup, Directory, AccessLog, db
from ..utils import get_disk_usage, get_ftp_connections
import subprocess
import os
import re
import psutil
from collections import defaultdict

@bp.route('/')
@login_required
def index():
    """監控首頁"""
    # 系統統計
    stats = {
        'total_users': FtpUser.query.count(),
        'active_users': FtpUser.query.filter_by(is_enabled=True).count(),
        'total_groups': FtpGroup.query.count(),
        'total_directories': Directory.query.filter_by(is_active=True).count(),
    }
    
    # 磁碟使用量
    base_dir = current_app.config.get('PROFTPD_BASE_DIR', '/backup/ftpdata')
    disk_usage = get_disk_usage_info(base_dir)
    
    # 系統資源使用量
    system_info = get_system_info()
    
    # ProFTPD 服務狀態
    service_status = get_proftpd_status()
    
    # 最近活動
    recent_activities = AccessLog.query.order_by(AccessLog.created_at.desc()).limit(10).all()
    
    return render_template('monitoring/index.html',
                         stats=stats,
                         disk_usage=disk_usage,
                         system_info=system_info,
                         service_status=service_status,
                         recent_activities=recent_activities)

@bp.route('/connections')
@login_required
def connections():
    """FTP 連線監控"""
    # 獲取目前 FTP 連線
    current_connections = get_current_connections()
    
    # 連線統計
    connection_stats = analyze_connections(current_connections)
    
    return render_template('monitoring/connections.html',
                         connections=current_connections,
                         stats=connection_stats)

@bp.route('/logs')
@login_required
def logs():
    """日誌監控"""
    log_type = request.args.get('type', 'access')
    lines = request.args.get('lines', 100, type=int)
    
    if log_type == 'access':
        log_file = current_app.config.get('PROFTPD_ACCESS_LOG', '/var/log/proftpd/access.log')
    elif log_type == 'auth':
        log_file = current_app.config.get('PROFTPD_AUTH_LOG', '/var/log/proftpd/auth.log')
    else:
        log_file = '/var/log/proftpd/proftpd.log'
    
    log_content = read_log_file(log_file, lines)
    parsed_logs = parse_log_entries(log_content, log_type)
    
    return render_template('monitoring/logs.html',
                         logs=parsed_logs,
                         log_type=log_type,
                         lines=lines)

@bp.route('/statistics')
@login_required
def statistics():
    """統計報表"""
    period = request.args.get('period', '7d')
    
    # 用戶活動統計
    user_stats = get_user_activity_stats(period)
    
    # 目錄使用統計
    directory_stats = get_directory_usage_stats()
    
    # 傳輸統計
    transfer_stats = get_transfer_stats(period)
    
    return render_template('monitoring/statistics.html',
                         user_stats=user_stats,
                         directory_stats=directory_stats,
                         transfer_stats=transfer_stats,
                         period=period)

@bp.route('/system')
@login_required
def system():
    """系統監控"""
    # 詳細系統資訊
    system_info = get_detailed_system_info()
    
    # 服務狀態
    services_status = get_all_services_status()
    
    # 網路狀態
    network_info = get_network_info()
    
    return render_template('monitoring/system.html',
                         system_info=system_info,
                         services_status=services_status,
                         network_info=network_info)

# API 路由用於即時更新
@bp.route('/api/current_stats')
@login_required
def api_current_stats():
    """即時統計 API"""
    base_dir = current_app.config.get('PROFTPD_BASE_DIR', '/backup/ftpdata')
    
    return jsonify({
        'connections': len(get_current_connections()),
        'disk_usage': get_disk_usage(base_dir),
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'timestamp': datetime.now().isoformat()
    })

@bp.route('/api/connections')
@login_required
def api_connections():
    """即時連線 API"""
    connections = get_current_connections()
    return jsonify({
        'connections': connections,
        'count': len(connections),
        'timestamp': datetime.now().isoformat()
    })

@bp.route('/api/system_health')
@login_required
def api_system_health():
    """系統健康狀況 API"""
    return jsonify({
        'proftpd_status': get_proftpd_status(),
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
        'timestamp': datetime.now().isoformat()
    })

@bp.route('/api/logs')
@login_required
def api_logs():
    """即時日誌 API"""
    log_type = request.args.get('type', 'main')
    lines = request.args.get('lines', 20, type=int)
    
    if log_type == 'access':
        log_file = current_app.config.get('PROFTPD_ACCESS_LOG', '/var/log/proftpd/access.log')
    elif log_type == 'auth':
        log_file = current_app.config.get('PROFTPD_AUTH_LOG', '/var/log/proftpd/auth.log')
    else:
        log_file = '/var/log/proftpd/proftpd.log'
    
    log_content = read_log_file(log_file, lines)
    parsed_logs = parse_log_entries(log_content, log_type)
    
    # 格式化為簡單的文字行（日誌已經在 read_log_file 中反轉過，最新在上）
    formatted_lines = []
    for log_entry in parsed_logs:
        if log_type == 'access' and 'timestamp' in log_entry and 'command' in log_entry:
            user_info = f"({log_entry['user']})" if log_entry.get('user') != 'UNKNOWN' else ""
            formatted_lines.append(f"[{log_entry['timestamp']}] {log_entry['client_ip']} {user_info} - {log_entry['command']} ({log_entry['status_code']})")
        elif log_type == 'auth' and 'timestamp' in log_entry and 'message' in log_entry:
            formatted_lines.append(f"[{log_entry['timestamp']}] {log_entry['message']}")
        else:
            # 主日誌或其他格式
            timestamp = log_entry.get('timestamp', 'unknown')
            message = log_entry.get('message', log_entry.get('raw', ''))
            formatted_lines.append(f"[{timestamp}] {message}")
    
    return jsonify({
        'log_type': log_type,
        'lines': formatted_lines,
        'count': len(formatted_lines),
        'timestamp': datetime.now().isoformat()
    })

def get_disk_usage_info(path):
    """獲取磁碟使用量資訊"""
    try:
        if os.path.exists(path):
            disk_info = psutil.disk_usage(path)
            return {
                'total': disk_info.total,
                'used': disk_info.used,
                'free': disk_info.free,
                'percent': (disk_info.used / disk_info.total) * 100,
                'path': path
            }
    except:
        pass
    
    return {
        'total': 0,
        'used': 0,
        'free': 0,
        'percent': 0,
        'path': path
    }

def get_system_info():
    """獲取系統資訊"""
    try:
        memory = psutil.virtual_memory()
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_count': psutil.cpu_count(),
            'memory_total': memory.total,
            'memory_used': memory.used,
            'memory_percent': memory.percent,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
            'uptime': datetime.now() - datetime.fromtimestamp(psutil.boot_time())
        }
    except:
        return {
            'cpu_percent': 0,
            'cpu_count': 1,
            'memory_total': 0,
            'memory_used': 0,
            'memory_percent': 0,
            'load_average': [0, 0, 0],
            'uptime': timedelta(0)
        }

def get_proftpd_status():
    """獲取 ProFTPD 服務狀態"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'proftpd'], 
                              capture_output=True, text=True, timeout=5)
        is_active = result.stdout.strip() == 'active'
        
        if is_active:
            # 獲取服務詳細資訊
            result = subprocess.run(['systemctl', 'status', 'proftpd'], 
                                  capture_output=True, text=True, timeout=5)
            status_output = result.stdout
            
            # 提取 PID
            pid_match = re.search(r'Main PID: (\d+)', status_output)
            pid = int(pid_match.group(1)) if pid_match else None
            
            # 提取啟動時間
            since_match = re.search(r'since (.+?);', status_output)
            since = since_match.group(1) if since_match else 'Unknown'
            
            return {
                'status': 'active',
                'pid': pid,
                'since': since,
                'enabled': True
            }
        else:
            return {
                'status': 'inactive',
                'pid': None,
                'since': None,
                'enabled': False
            }
    except:
        return {
            'status': 'unknown',
            'pid': None,
            'since': None,
            'enabled': False
        }

def get_current_connections():
    """獲取目前 FTP 連線"""
    connections = []
    try:
        # 使用 ftpwho 指令
        result = subprocess.run(['ftpwho'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if line.strip() and not line.startswith('Service class') and not line.startswith('standalone FTP'):
                    # ftpwho 輸出格式: PID USER [TIME] STATUS
                    match = re.match(r'\s*(\d+)\s+(\S+)\s+\[([^\]]+)\]\s+(.+)', line.strip())
                    if match:
                        pid = match.group(1)
                        user = match.group(2)
                        session_time = match.group(3)
                        status = match.group(4).strip()
                        
                        # 從 ss 或 netstat 獲取對應的 IP 位址
                        client_ip = get_client_ip_by_pid(pid)
                        
                        connections.append({
                            'pid': pid,
                            'user': user,
                            'client_ip': client_ip,
                            'status': status,
                            'session_time': session_time,
                            'connect_time': datetime.now()  # 實際應該從狀態中解析
                        })
        
        # 如果 ftpwho 沒有找到連線，使用 ss 或 netstat
        if not connections:
            connections = get_connections_from_netstat()
            
    except Exception as e:
        current_app.logger.error(f'Error getting FTP connections: {e}')
        connections = []
    
    return connections

def get_connections_from_netstat():
    """從 ss 或 netstat 獲取連線資訊"""
    connections = []
    try:
        # 優先使用 ss 指令
        result = subprocess.run(['ss', '-tnp'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if ':21' in line and 'ESTAB' in line:
                    # ss 輸出格式解析
                    parts = line.split()
                    if len(parts) >= 6:
                        local_addr = parts[3]
                        foreign_addr = parts[4]
                        process_info = parts[5] if len(parts) > 5 else ''
                        
                        # 提取 PID
                        pid_match = re.search(r'pid=(\d+)', process_info)
                        pid = pid_match.group(1) if pid_match else 'unknown'
                        
                        # 提取客戶端 IP
                        if ':' in foreign_addr:
                            if foreign_addr.startswith('[::ffff:'):
                                # IPv4-mapped IPv6 位址
                                client_ip = foreign_addr.replace('[::ffff:', '').split(']:')[0]
                            else:
                                client_ip = foreign_addr.split(':')[0]
                        else:
                            client_ip = foreign_addr
                        
                        connections.append({
                            'pid': pid,
                            'user': 'unknown',
                            'client_ip': client_ip,
                            'status': 'Connected',
                            'connect_time': datetime.now()
                        })
        else:
            # 如果 ss 不可用，嘗試 netstat
            result = subprocess.run(['netstat', '-tnp'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if ':21 ' in line and 'ESTABLISHED' in line:
                        parts = line.split()
                        if len(parts) >= 7:
                            foreign_addr = parts[4]
                            pid_info = parts[6] if len(parts) > 6 else ''
                            
                            pid_match = re.search(r'(\d+)/', pid_info)
                            pid = pid_match.group(1) if pid_match else 'unknown'
                            
                            connections.append({
                                'pid': pid,
                                'user': 'unknown',
                                'client_ip': foreign_addr.split(':')[0],
                                'status': 'Connected',
                                'connect_time': datetime.now()
                            })
    except Exception as e:
        current_app.logger.error(f'Error getting connections from netstat/ss: {e}')
    
    return connections

def get_client_ip_by_pid(pid):
    """通過 PID 獲取客戶端 IP 位址"""
    try:
        # 使用 ss 指令結合 PID 查找
        result = subprocess.run(['ss', '-tnp'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if f'pid={pid}' in line and ':21' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        foreign_addr = parts[4]
                        if ':' in foreign_addr:
                            if foreign_addr.startswith('[::ffff:'):
                                # IPv4-mapped IPv6 位址
                                return foreign_addr.replace('[::ffff:', '').split(']:')[0]
                            else:
                                return foreign_addr.split(':')[0]
                        return foreign_addr
    except:
        pass
    
    return 'unknown'

def analyze_connections(connections):
    """分析連線統計"""
    stats = {
        'total': len(connections),
        'by_user': defaultdict(int),
        'by_ip': defaultdict(int),
        'unique_users': set(),
        'unique_ips': set()
    }
    
    for conn in connections:
        stats['by_user'][conn['user']] += 1
        stats['by_ip'][conn['client_ip']] += 1
        stats['unique_users'].add(conn['user'])
        stats['unique_ips'].add(conn['client_ip'])
    
    stats['unique_users'] = len(stats['unique_users'])
    stats['unique_ips'] = len(stats['unique_ips'])
    
    return stats

def read_log_file(log_file, lines=100):
    """讀取日誌檔案"""
    try:
        # 使用 tail 指令讀取最後幾行
        result = subprocess.run(['tail', '-n', str(lines), log_file], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            log_lines = result.stdout.split('\n')
            # 反轉順序，讓最新的日誌在上方
            return list(reversed([line for line in log_lines if line.strip()]))
    except:
        pass
    
    # 如果 tail 指令失敗，嘗試直接讀取檔案
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            # 反轉順序，讓最新的日誌在上方
            return list(reversed([line.strip() for line in recent_lines if line.strip()]))
    except:
        return []

def parse_log_entries(log_lines, log_type='access'):
    """解析日誌項目"""
    parsed_logs = []
    
    for line in log_lines:
        if not line.strip():
            continue
            
        entry = parse_single_log_entry(line, log_type)
        if entry:
            parsed_logs.append(entry)
    
    return parsed_logs

def parse_single_log_entry(line, log_type):
    """解析單個日誌項目"""
    try:
        if log_type == 'access':
            # ProFTPD access log 格式: IP USER UNKNOWN [timestamp] "command" status bytes
            match = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+"([^"]+)"\s+(\d+)\s+(\S+)', line)
            if match:
                return {
                    'timestamp': match.group(4),
                    'client_ip': match.group(1),
                    'user': match.group(2),
                    'command': match.group(5),
                    'status_code': match.group(6),
                    'bytes': match.group(7),
                    'raw': line.strip()
                }
        elif log_type == 'auth':
            # ProFTPD auth log 格式: IP USER UNKNOWN [timestamp] "command" status bytes
            match = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+"([^"]+)"\s+(\d+)\s+(\S+)', line)
            if match:
                return {
                    'timestamp': match.group(4),
                    'client_ip': match.group(1),
                    'user': match.group(2),
                    'command': match.group(5),
                    'status_code': match.group(6),
                    'message': f"{match.group(1)} {match.group(2)} - {match.group(5)} ({match.group(6)})",
                    'raw': line.strip()
                }
        else:
            # 主日誌格式 - ProFTPD 格式: YYYY-MM-DD HH:MM:SS,mmm hostname proftpd[pid] hostname: message
            match = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+\S+\s+proftpd\[\d+\]\s+\S+:\s+(.+)', line)
            if match:
                return {
                    'timestamp': match.group(1),
                    'message': match.group(2),
                    'raw': line.strip()
                }
            else:
                # 如果無法解析時間戳，嘗試提取行首的時間（包含毫秒）
                time_match = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)', line)
                if time_match:
                    return {
                        'timestamp': time_match.group(1),
                        'message': line[len(time_match.group(1)):].strip(),
                        'raw': line.strip()
                    }
                else:
                    # 如果還是無法解析，嘗試不包含毫秒的格式
                    time_match_simple = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                    if time_match_simple:
                        return {
                            'timestamp': time_match_simple.group(1),
                            'message': line[len(time_match_simple.group(1)):].strip(),
                            'raw': line.strip()
                        }
                    else:
                        return {
                            'timestamp': 'unknown',
                            'message': line.strip(),
                            'raw': line.strip()
                        }
    except:
        return {
            'timestamp': 'unknown',
            'message': line.strip(),
            'raw': line.strip()
        }

def get_user_activity_stats(period='7d'):
    """獲取用戶活動統計"""
    # 這裡應該從 ProFTPD 日誌中解析用戶活動
    # 暫時返回模擬數據
    return {
        'most_active_users': [],
        'login_count': 0,
        'transfer_count': 0,
        'error_count': 0
    }

def get_directory_usage_stats():
    """獲取目錄使用統計"""
    stats = []
    base_dir = current_app.config.get('PROFTPD_BASE_DIR', '/backup/ftpdata')
    
    directories = Directory.query.filter_by(is_active=True).all()
    for directory in directories:
        try:
            if os.path.exists(directory.path):
                size = get_directory_size(directory.path)
                file_count = get_file_count(directory.path)
                stats.append({
                    'name': directory.name,
                    'path': directory.path,
                    'size': size,
                    'file_count': file_count,
                    'permissions_count': len(directory.permissions)
                })
        except:
            continue
    
    return stats

def get_directory_size(path):
    """獲取目錄大小"""
    try:
        result = subprocess.run(['du', '-sb', path], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return int(result.stdout.split()[0])
    except:
        pass
    return 0

def get_file_count(path):
    """獲取目錄中的檔案數量"""
    try:
        result = subprocess.run(['find', path, '-type', 'f'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return len(result.stdout.split('\n')) - 1
    except:
        pass
    return 0

def get_transfer_stats(period='7d'):
    """獲取傳輸統計"""
    # 這裡應該從 ProFTPD 日誌中解析傳輸統計
    # 暫時返回模擬數據
    return {
        'upload_count': 0,
        'download_count': 0,
        'total_bytes': 0,
        'avg_speed': 0
    }

def get_detailed_system_info():
    """獲取詳細系統資訊"""
    info = get_system_info()
    
    # 添加更多詳細資訊
    info.update({
        'hostname': os.uname().nodename,
        'kernel': os.uname().release,
        'architecture': os.uname().machine,
        'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
        'disk_partitions': []
    })
    
    # 磁碟分割區資訊
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            info['disk_partitions'].append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'fstype': partition.fstype,
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': (usage.used / usage.total) * 100
            })
        except:
            continue
    
    return info

def get_all_services_status():
    """獲取所有相關服務狀態"""
    services = ['proftpd', 'ssh', 'nginx', 'apache2']
    status = {}
    
    for service in services:
        try:
            result = subprocess.run(['systemctl', 'is-active', service], 
                                  capture_output=True, text=True, timeout=5)
            status[service] = result.stdout.strip() == 'active'
        except:
            status[service] = False
    
    return status

def get_network_info():
    """獲取網路資訊"""
    try:
        network_info = {
            'interfaces': [],
            'connections': len(psutil.net_connections()),
            'bytes_sent': psutil.net_io_counters().bytes_sent,
            'bytes_recv': psutil.net_io_counters().bytes_recv
        }
        
        for interface, addrs in psutil.net_if_addrs().items():
            interface_info = {'name': interface, 'addresses': []}
            for addr in addrs:
                interface_info['addresses'].append({
                    'family': str(addr.family),
                    'address': addr.address,
                    'netmask': addr.netmask,
                    'broadcast': addr.broadcast
                })
            network_info['interfaces'].append(interface_info)
        
        return network_info
    except:
        return {
            'interfaces': [],
            'connections': 0,
            'bytes_sent': 0,
            'bytes_recv': 0
        }