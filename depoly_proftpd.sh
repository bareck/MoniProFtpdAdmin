#!/bin/bash
# ProFTPD 虛擬用戶完整部署腳本

echo "=== 部署 ProFTPD with Virtual Users ==="

# 1. 移除系統用戶（如果存在）
echo "清理系統用戶..."
for user in jackie tpe alphascan iotpe; do
    if id "$user" &>/dev/null; then
        sudo userdel $user
        echo "已移除系統用戶: $user"
    fi
done

# 2. 安裝 ProFTPD
echo "安裝 ProFTPD..."
sudo yum install -y epel-release
# sudo dnf install epel-release -y
# sudo dnf makecache

sudo yum install -y proftpd proftpd-utils

# 3. 停用其他 FTP 服務
sudo systemctl stop vsftpd 2>/dev/null
sudo systemctl disable vsftpd 2>/dev/null

# 4. 創建目錄結構
echo "創建目錄結構..."
sudo mkdir -p /backup/ftpdata/ALPHASCAN
sudo mkdir -p /backup/ftpdata/IO_DATA
sudo mkdir -p /backup/ftpdata/hpcdisplay
sudo mkdir -p /backup/ftpdata/Menpad_Taipei
sudo mkdir -p /var/log/proftpd
sudo mkdir -p /etc/proftpd

# 5. 設定目錄權限（使用 nobody 用戶）
sudo chown -R nobody:nobody /backup/ftpdata
sudo chmod 777 /backup/ftpdata
sudo chmod 777 /backup/ftpdata/ALPHASCAN
sudo chmod 777 /backup/ftpdata/IO_DATA
sudo chmod 777 /backup/ftpdata/hpcdisplay
sudo chmod 777 /backup/ftpdata/Menpad_Taipei

# 6. 創建虛擬用戶群組
echo "創建群組..."
ftpasswd --group --file=/etc/proftpd/ftpd.group --name=admins --gid=5000
ftpasswd --group --file=/etc/proftpd/ftpd.group --name=users --gid=5001

# 7. 創建虛擬用戶
echo "創建虛擬用戶..."
# 管理員帳號
ftpasswd --passwd --file=/etc/proftpd/ftpd.passwd \
    --name=jackie --uid=5001 --gid=5000 \
    --home=/backup/ftpdata --shell=/sbin/nologin \
    --stdin <<< "Menpad27685366"

ftpasswd --passwd --file=/etc/proftpd/ftpd.passwd \
    --name=tpe --uid=5002 --gid=5000 \
    --home=/backup/ftpdata --shell=/sbin/nologin \
    --stdin <<< "Menpad27685386"

# 一般用戶帳號
ftpasswd --passwd --file=/etc/proftpd/ftpd.passwd \
    --name=alphascan --uid=5003 --gid=5001 \
    --home=/backup/ftpdata/ALPHASCAN --shell=/sbin/nologin \
    --stdin <<< "ALP1815"

ftpasswd --passwd --file=/etc/proftpd/ftpd.passwd \
    --name=iotpe --uid=5004 --gid=5001 \
    --home=/backup/ftpdata/IO_DATA --shell=/sbin/nologin \
    --stdin <<< "IO25231399"

ftpasswd --passwd --file=/etc/proftpd/ftpd.passwd \
    --name=hpcdisplay --uid=5005 --gid=5001 \
    --home=/backup/ftpdata/hpcdisplay --shell=/sbin/nologin \
    --stdin <<< "hpc4008598108"

ftpasswd --passwd --file=/etc/proftpd/ftpd.passwd \
    --name=tpe88 --uid=5006 --gid=5001 \
    --home=/backup/ftpdata/ --shell=/sbin/nologin \
    --stdin <<< "tpe8888"

# 8. 將用戶加入群組
echo "設定群組成員..."
ftpasswd --group --file=/etc/proftpd/ftpd.group \
    --name=admins --gid=5000 \
    --member=jackie --member=tpe

ftpasswd --group --file=/etc/proftpd/ftpd.group \
    --name=users --gid=5001 \
    --member=alphascan --member=iotpe --member=hpcdisplay --member=tpe88

# 9. 套用配置
echo "套用 ProFTPD 配置..."
sudo cp /usr/local/etc/proftpd.conf /usr/local/etc/proftpd.conf.bak
# [這裡應該寫入上面的配置內容]

# 10. 創建歡迎訊息
sudo bash -c 'cat > /etc/proftpd/welcome.msg << EOF
Welcome to FTP Server
=====================
管理員: 完整權限
一般用戶: 僅可讀寫，不可刪除或建立目錄
EOF'

# 12. SELinux 設定
if [ "$(getenforce)" = "Enforcing" ]; then
    echo "設定 SELinux..."
    sudo setsebool -P ftpd_full_access on
fi

# 13. 啟動服務
echo "啟動 ProFTPD..."
sudo systemctl enable proftpd
sudo systemctl restart proftpd

# 14. 顯示用戶資訊
echo ""
echo "=== FTP 用戶資訊 ==="
echo "管理員帳號："
echo "  jackie / Menpad27685366 - 完整權限"
echo "  tpe / Menpad27685386 - 完整權限"
echo ""
echo "一般用戶帳號："
echo "  alphascan / ALP1815 - 僅可存取 ALPHASCAN 目錄"
echo "  iotpe / IO25231399 - 僅可存取 IO_DATA 目錄"
echo ""
echo "測試指令: ftp localhost"