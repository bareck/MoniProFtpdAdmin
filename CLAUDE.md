# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is MoniProFtpdAdmin - a web application for managing ProFTPD virtual users, groups, and directory permissions. The project manages FTP access to `/backup/ftpdata` with role-based permissions.

## Architecture

### Core Components
- **Virtual User Management**: Uses ProFTPD's AuthUserFile/AuthGroupFile for user authentication
- **Group Management**: Manages user groups (admins, users) with different permission levels
- **Directory Permissions**: Granular control over read/write/delete permissions per directory and user/group
- **SQLite Storage**: User and permission data stored in SQLite database

### Permission Model
- **Admins Group**: Full access to all directories including delete/create operations
- **Users Group**: Restricted access with read/write but limited delete permissions
- **Directory-Specific Permissions**: Each directory can have custom user/group access rules

### FTP Directory Structure
Base path: Configurable (default: `/backup/ftpdata/`)

**Note**: FTP base directory is configurable through web interface settings.

## Development Commands

### ProFTPD Management
```bash
# Install ProFTPD (CentOS/RHEL)
./install_proftpd.sh

# Deploy virtual users and configuration
./depoly_proftpd.sh

# Check ProFTPD status
sudo systemctl status proftpd

# Restart ProFTPD service
sudo systemctl restart proftpd

# View ProFTPD logs
sudo tail -f /var/log/proftpd/proftpd.log
sudo tail -f /var/log/proftpd/access.log
```

### Virtual User Commands
```bash
# Add new virtual user
ftpasswd --passwd --file=/etc/proftpd/ftpd.passwd \
    --name=username --uid=5XXX --gid=5XXX \
    --home=/backup/ftpdata/directory --shell=/sbin/nologin

# Add user to group
ftpasswd --group --file=/etc/proftpd/ftpd.group \
    --name=groupname --gid=5XXX --member=username

# List virtual users
ftpasswd --passwd --file=/etc/proftpd/ftpd.passwd --list

# List groups
ftpasswd --group --file=/etc/proftpd/ftpd.group --list
```

### Monitoring Commands
```bash
# Check current FTP connections
sudo ftpwho

# Monitor ProFTPD processes
sudo ps aux | grep proftpd

# Check disk usage for FTP directories (adjust path as configured)
du -sh /backup/ftpdata/*

# Parse access logs for statistics
sudo grep "$(date +%Y-%m-%d)" /var/log/proftpd/access.log | wc -l

# Reload ProFTPD configuration
sudo systemctl reload proftpd
```

## Key Configuration Files

### ProFTPD Configuration Path Detection
The system automatically detects ProFTPD configuration paths:
- **Self-compiled**: `/usr/local/etc/proftpd.conf` (checked first)
- **Package manager**: `/etc/proftpd/proftpd.conf` (fallback)
- **Override**: Set `PROFTPD_CONFIG_DIR` and `PROFTPD_MAIN_CONFIG` environment variables

### `/etc/proftpd/ftpd.passwd` or `/usr/local/etc/ftpd.passwd`
Virtual user authentication file containing user credentials and home directories.

### `/etc/proftpd/ftpd.group` or `/usr/local/etc/ftpd.group`
Group membership file defining which users belong to admins vs users groups.

### `proftpd.conf`
Main ProFTPD configuration with:
- Virtual user authentication setup
- Directory-specific permission blocks
- Security settings (passive ports, timeouts, logging)
- DefaultRoot configuration for user isolation
- Auto-detected path: `/usr/local/etc/proftpd.conf` or `/etc/proftpd/proftpd.conf`

### `/etc/proftpd/dynamic.conf`
Dynamically generated configuration file containing:
- Variable directory permission blocks
- User-specific access rules
- Should be included in main proftpd.conf with `Include /etc/proftpd/dynamic.conf`

### Configuration File Generation
The web application should generate configuration files by:
1. Reading template files for static configuration
2. Generating dynamic sections based on database content and settings
3. Substituting configurable paths (FTP base directory, log paths, etc.)
4. Writing to `/etc/proftpd/dynamic.conf`
5. Triggering `sudo systemctl reload proftpd` after changes

## Requirements Implementation

The web application must provide:

1. **User Management**: CRUD operations for FTP accounts with fields:
   - Account name (username)
   - Password
   - Home directory path
   - Comments/description
   - Enable/disable status

2. **Group Management**: CRUD operations for groups with member assignment

3. **Directory Permissions**: Interface to manage per-directory permissions:
   - Read permissions (LIST, CWD, PWD, NLST, STAT, MLSD)
   - Write permissions (STOR, STOU, APPE) 
   - Delete/Directory operations (DELE, MKD, RMD, RNFR, RNTO, SITE_CHMOD)

4. **SQLite Integration**: Store user/group data and sync with ProFTPD files

5. **Monitoring Features**: 
   - Real-time FTP connection status display
   - User access statistics and reports
   - Disk usage monitoring for FTP directories

6. **Configuration Management**:
   - Automatic ProFTPD configuration file generation
   - Modular configuration with include files for dynamic sections
   - Automatic `systemctl reload proftpd` trigger after configuration changes

7. **Web Admin Authentication**:
   - Admin user login/logout functionality
   - Session management for web interface access
   - Role-based access control for web administration features

8. **System Configuration**:
   - Configurable FTP base directory path (default: `/backup/ftpdata/`)
   - Configurable log file paths
   - System settings management interface

## Security Considerations

### FTP Security
- Virtual users run as `nobody:nobody` for isolation
- PAM authentication disabled, only file-based auth
- Anonymous access completely blocked
- Directory traversal prevented with DefaultRoot
- Passive port range limited (50000-50100)
- Connection limits enforced (30 max clients, 5 per host)
- Comprehensive logging enabled

### Web Admin Security
- Secure session management with timeout
- Password hashing for admin accounts
- CSRF protection for form submissions
- Input validation and sanitization
- Access logging for administrative actions
- Optional IP whitelist for admin access

## User Account Management

The system supports role-based FTP user management through:

### Admin Users (Group: admins)
- Full permissions to all directories including delete/create operations
- Access to entire FTP base directory structure
- Can manage other users and system settings

### Regular Users (Group: users)
- Restricted access with read/write but limited delete permissions
- Confined to their designated home directories
- Subject to directory-specific permission rules