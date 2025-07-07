# ProFTPD Web Management System

**English | [繁體中文](README-tw.md)**

A comprehensive ProFTPD virtual user management system providing a web interface for managing FTP users, groups, permissions, and system monitoring.

Use case: I use this on a dedicated FTP server to provide internal file sharing for a company. In daily operations, departments need to share files or directories, but general members should be restricted from accessing other non-related departmental folders. As a supervisor, I need permissions to browse and manage certain folders. After research, it seems that only the veteran ProFTPD is suitable for achieving such complex management. To simplify daily operations that often require permission changes or account maintenance, I developed this project using AI tools.

This project uses ProFTPD's AuthUserFile/AuthGroupFile for user authentication, tested on AlmaLinux 9.6 with ProFTPD compiled from source code.

## 📋 Features

### 🔧 Core Management Functions
- ✅ **User Management**: Complete FTP user CRUD operations with virtual user support
- ✅ **Group Management**: Group creation, member management, batch operations
- ✅ **Permission Management**: Directory permission settings with real-time permission matrix interface
- ✅ **Configuration Generation**: Automatic ProFTPD configuration file generation with modular Include support

### 📊 Monitoring and Statistics
- ✅ **Real-time Connection Monitoring**: FTP connection status and user activity tracking
- ✅ **System Resource Monitoring**: CPU, memory, disk usage monitoring
- ✅ **Log Analysis**: Access log and authentication log parsing and statistics
- ✅ **Report Export**: Statistical report export in CSV and JSON formats

### ⚙️ System Administration
- ✅ **System Settings**: FTP server parameters, security settings, log configuration
- ✅ **Backup and Restore**: System data backup and configuration file backup
- ✅ **Administrator Management**: Password changes and session management
- ✅ **Configuration Management**: Configuration file preview, validation, and reload

## 🏗️ System Architecture

```
MoniProFtpdAdmin/
├── app/                    # Application core
│   ├── auth/              # Authentication and authorization module
│   ├── users/             # User management module
│   ├── groups/            # Group management module
│   ├── permissions/       # Permission management module
│   ├── monitoring/        # Monitoring functionality module
│   ├── settings/          # System settings module
│   ├── config/            # Configuration management module
│   ├── main/              # Main page module
│   ├── models.py          # Database models
│   ├── proftpd.py         # ProFTPD integration class
│   └── utils.py           # Utility functions
├── templates/             # Jinja2 HTML templates
├── static/                # Static files (CSS/JS)
├── config.py              # Application configuration
├── run.py                 # Application startup file
├── requirements.txt       # Python dependencies
├── CLAUDE.md             # Development documentation
└── README.md             # Project documentation
```

## 🚀 Installation and Setup

### System Requirements

- Python 3.8+
- ProFTPD 1.3.6+
- Linux/Unix system (recommended Ubuntu 20.04+ or CentOS 8+)
- System administrator privileges (for ProFTPD service management)

### 1. Download Project

```bash
# Download project files
cd /opt
git clone https://github.com/bareck/MoniProFtpdAdmin.git proftpd-admin
cd proftpd-admin
```

### 2. Create Python Virtual Environment

It's recommended to use a Python virtual environment to isolate project dependencies and avoid conflicts with system Python packages.

#### Using venv (built-in Python 3.3+)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Confirm virtual environment is active (command prompt should show (venv))
which python
# Should display: /opt/proftpd-admin/venv/bin/python
```

#### Using virtualenv (requires separate installation)

```bash
# Install virtualenv (if not already installed)
pip3 install virtualenv

# Create virtual environment
virtualenv venv

# Activate virtual environment
source venv/bin/activate
```

#### Virtual Environment Management Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Delete virtual environment (if rebuild needed)
rm -rf venv
```

### 3. Install Python Dependencies

Ensure the virtual environment is activated, then install required packages:

```bash
# Confirm virtual environment is activated
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Or manually install main packages
pip install flask flask-login flask-wtf wtforms sqlalchemy psutil
```

### 4. Environment Variable Configuration

Create environment variable file or set in system:

```bash
# Create .env file (optional)
cat > .env << EOF
FLASK_CONFIG=production
PROFTPD_BASE_DIR=/backup/ftpdata
PROFTPD_CONFIG_DIR=/etc/proftpd
DATABASE_PATH=/opt/proftpd-admin/app.db
BACKUP_DIR=/opt/proftpd-admin/backups
SECRET_KEY=your-very-secure-secret-key-here
EOF

# Or directly set environment variables
export FLASK_CONFIG=production
export PROFTPD_BASE_DIR=/backup/ftpdata
export PROFTPD_CONFIG_DIR=/etc/proftpd
```

### 5. Database Initialization

```bash
# Activate virtual environment
source venv/bin/activate

# Initialize database (automatically created on first run)
python run.py
```

### 6. ProFTPD Configuration

#### Install ProFTPD

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install proftpd-basic

# CentOS/RHEL
sudo yum install proftpd
# or
sudo dnf install proftpd
```

#### Compile Installation (Recommended)

```bash
sudo dnf update
sudo dnf install tar -y
sudo dnf groupinstall "Development Tools" -y

# 1. Download
curl -O ftp://ftp.proftpd.org/distrib/source/proftpd-1.3.9.tar.gz

# 2. Extract
tar zxvf proftpd-1.3.9.tar.gz

# 3. Enter directory
cd proftpd-1.3.9

# 4. Configure compilation options
./configure

# 5. Compile
make

# 6. Install
sudo make install

# Confirm installation success
/usr/local/sbin/proftpd -v
```

#### Configure ProFTPD Directory

```bash
# Create FTP root directory (customizable in UI)
sudo mkdir -p /backup/ftpdata
sudo chown nobody:nobody /backup/ftpdata
sudo chmod 755 /backup/ftpdata
```

## 🔧 Usage

### Start Application

#### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Set development environment
export FLASK_CONFIG=development

# Start development server
python run.py
```

#### Production Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Set production environment
export FLASK_CONFIG=production

# Start with Gunicorn (recommended)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app

# Or start directly
python run.py
```

### Create System Service (Optional)

Create systemd service file for automatic startup:

```bash
sudo cat > /etc/systemd/system/proftpd-admin.service << EOF
[Unit]
Description=ProFTPD Admin Web Interface
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/proftpd-admin
Environment=PATH=/opt/proftpd-admin/venv/bin
Environment=FLASK_CONFIG=production
Environment=PROFTPD_BASE_DIR=/backup/ftpdata
Environment=PROFTPD_CONFIG_DIR=/etc/proftpd
ExecStart=/opt/proftpd-admin/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable proftpd-admin
sudo systemctl start proftpd-admin
```

### Access Web Interface

Open browser and visit `http://server-ip:5000`

Default administrator account:
- Username: `admin`
- Password: `admin123`

⚠️ **Security Alert**: Please change the default password immediately after first login!

## 📖 Feature Overview

### 1. User Management
- Add/edit/delete FTP users
- Set user home directories, UID/GID
- Group membership management
- Batch operation support

### 2. Group Management
- Create/edit/delete FTP groups
- Batch member addition/removal
- Group permission settings

### 3. Permission Management
- Directory permission settings (read, write, delete)
- Real-time permission matrix display
- Permission inheritance settings

### 4. Monitoring Features
- Real-time FTP connection status
- System resource usage
- Log file analysis
- Statistical report generation

### 5. System Settings
- FTP server parameter adjustment
- Security configuration
- Automatic backup settings
- Administrator account management

## ✅ Development Status

### Completed Features
- [x] Project foundation structure (directories, configuration files)
- [x] SQLite database models (users, groups, permissions, settings)
- [x] Flask web application framework
- [x] Web administrator authentication system
- [x] User management CRUD functionality
- [x] Group management CRUD functionality
- [x] Directory permission management functionality
- [x] ProFTPD configuration file auto-generation
- [x] Monitoring features (connection status, statistics, disk usage)
- [x] System settings management interface
- [x] HTML template files

### System Integration Status
✅ **Complete Implementation** - All planned features have been implemented and are functioning normally

## 🔒 Security Considerations

1. **Password Security**: Use strong passwords and change them regularly
2. **File Permissions**: Ensure configuration files have correct permissions
3. **Network Security**: Recommend using HTTPS and restricting access IPs
4. **Backup Strategy**: Regularly backup database and configuration files
5. **System Updates**: Keep system and packages updated

## 🛠️ Development Guide

### Development Environment Setup

```bash
# Clone project
git clone <repository-url>
cd proftpd-admin

# Create development virtual environment
python3 -m venv venv-dev
source venv-dev/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install pytest flask-testing coverage

# Set development environment variables
export FLASK_CONFIG=development
export FLASK_DEBUG=1

# Start development server
python run.py
```

### Technical Architecture

- **Backend**: Flask + SQLAlchemy + Flask-Login
- **Frontend**: Bootstrap 5 + Vanilla JavaScript + AJAX
- **Database**: SQLite (expandable to PostgreSQL/MySQL)
- **Authentication**: Flask-Login + password hashing
- **Forms**: Flask-WTF + WTForms + CSRF protection
- **Architecture**: Blueprint modular design

## 📝 Version History

- **v1.0.0** (2025-7): Initial complete version
  - Complete user/group management functionality
  - Permission management system
  - Real-time monitoring interface
  - System settings functionality
  - Backup functionality
  - Multi-language support

## 🤝 Contributing

Welcome to submit Issues and Pull Requests to improve this project.

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For questions or assistance, please:

1. Review the `CLAUDE.md` development documentation
2. Check system logs: `tail -f /var/log/proftpd/proftpd.log`
3. View application logs: `journalctl -u proftpd-admin -f`
4. Submit Issues to the project repository

---

**Note**: This system requires appropriate system administrator privileges to function properly. Please ensure deployment in a secure environment.