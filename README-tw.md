# ProFTPD 管理系統

**[English](README.md) | 繁體中文**

一個完整的 ProFTPD 虛擬用戶管理系統，提供 Web 介面管理 FTP 用戶、群組、權限和系統監控功能。
適用場景：我用在一個專用的 FTP Server 上，提供一間公司作為內部部門分享檔案使用。在日常作業中，部門內需要分享檔案或目錄，但又得限制一般組員不能看他其他非相關部門的資料夾，做為主管又要有權限可以瀏覽及管理部分資料夾，研究了一下要達成如此複雜的管理，似乎只有老牌的 ProFTPD 比較適合，為了簡化日常作業中常需要異動權限或是帳號維護，因此利用 AI 工具撰寫了本專案。

本專案使用 ProFTPD 的 AuthUserFile/AuthGroupFile 作為使用者驗證方式，測試的環境是 AlmaLinux 9.6， ProFTPD 使用 source code 編譯安裝。


## 📋 功能特色

### 🔧 核心管理功能
- ✅ **用戶管理**: 完整的 FTP 用戶 CRUD 操作，支援虛擬用戶
- ✅ **群組管理**: 群組建立、成員管理、批次操作
- ✅ **權限管理**: 目錄權限設定，即時權限矩陣介面
- ✅ **配置生成**: 自動產生 ProFTPD 配置檔，支援模組化 Include

### 📊 監控與統計
- ✅ **即時連線監控**: FTP 連線狀態、用戶活動追蹤
- ✅ **系統資源監控**: CPU、記憶體、磁碟使用量
- ✅ **日誌分析**: 存取日誌、認證日誌解析與統計
- ✅ **報表匯出**: CSV、JSON 格式統計報表匯出

### ⚙️ 系統管理
- ✅ **系統設定**: FTP 伺服器參數、安全設定、日誌配置
- ✅ **備份還原**: 系統資料備份、配置檔備份
- ✅ **管理員管理**: 密碼變更、會話管理
- ✅ **配置管理**: 配置檔預覽、驗證、重新載入

## 🏗️ 系統架構

```
MoniProFtpdAdmin/
├── app/                    # 應用程式核心
│   ├── auth/              # 認證授權模組
│   ├── users/             # 用戶管理模組
│   ├── groups/            # 群組管理模組
│   ├── permissions/       # 權限管理模組
│   ├── monitoring/        # 監控功能模組
│   ├── settings/          # 系統設定模組
│   ├── config/            # 配置管理模組
│   ├── main/              # 主頁面模組
│   ├── models.py          # 資料庫模型
│   ├── proftpd.py         # ProFTPD 整合類別
│   └── utils.py           # 工具函數
├── templates/             # Jinja2 HTML 模板
├── static/                # 靜態檔案 (CSS/JS)
├── config.py              # 應用程式配置
├── run.py                 # 應用程式啟動檔
├── requirements.txt       # Python 依賴套件
├── CLAUDE.md             # 開發文件
└── README.md             # 專案說明文件
```

## 🚀 安裝與設定

### 系統需求

- Python 3.8+
- ProFTPD 1.3.6+
- Linux/Unix 系統（建議 Ubuntu 20.04+ 或 CentOS 8+）
- 系統管理員權限（用於 ProFTPD 服務管理）

### 1. 下載專案

```bash
# 下載專案檔案
cd /opt
git clone https://github.com/bareck/MoniProFtpdAdmin.git proftpd-admin
cd proftpd-admin
```

### 2. 建立 Python 虛擬環境

建議使用 Python 虛擬環境來隔離專案依賴，避免與系統 Python 套件衝突。

#### 使用 venv（Python 3.3+ 內建）

```bash
# 建立虛擬環境
python3 -m venv venv

# 啟用虛擬環境
source venv/bin/activate

# 確認虛擬環境已啟用（命令提示符應顯示 (venv)）
which python
# 應該顯示: /opt/proftpd-admin/venv/bin/python
```

#### 使用 virtualenv（需額外安裝）

```bash
# 安裝 virtualenv（如果尚未安裝）
pip3 install virtualenv

# 建立虛擬環境
virtualenv venv

# 啟用虛擬環境
source venv/bin/activate
```

#### 虛擬環境管理指令

```bash
# 啟用虛擬環境
source venv/bin/activate

# 停用虛擬環境
deactivate

# 刪除虛擬環境（如需重建）
rm -rf venv
```

### 3. 安裝 Python 依賴套件

確保虛擬環境已啟用，然後安裝所需套件：

```bash
# 確認虛擬環境已啟用
source venv/bin/activate

# 安裝依賴套件
pip install -r requirements.txt

# 或手動安裝主要套件
pip install flask flask-login flask-wtf wtforms sqlalchemy psutil
```

### 4. 環境變數設定

建立環境變數檔案或在系統中設定：

```bash
# 建立 .env 檔案（可選）
cat > .env << EOF
FLASK_CONFIG=production
PROFTPD_BASE_DIR=/backup/ftpdata
PROFTPD_CONFIG_DIR=/etc/proftpd
DATABASE_PATH=/opt/proftpd-admin/app.db
BACKUP_DIR=/opt/proftpd-admin/backups
SECRET_KEY=your-very-secure-secret-key-here
EOF

# 或直接設定環境變數
export FLASK_CONFIG=production
export PROFTPD_BASE_DIR=/backup/ftpdata
export PROFTPD_CONFIG_DIR=/etc/proftpd
```

### 5. 資料庫初始化

```bash
# 啟用虛擬環境
source venv/bin/activate

# 初始化資料庫（首次執行會自動建立）
python run.py
```

### 6. ProFTPD 設定

#### 安裝 ProFTPD

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install proftpd-basic

# CentOS/RHEL
sudo yum install proftpd
# 或
sudo dnf install proftpd
```

#### 使用編譯方式安裝 (建議使用)

```bash
sudo dnf update
sudo dnf install tar -y
sudo dnf groupinstall "Development Tools" -y

# 1. 下載
curl -O ftp://ftp.proftpd.org/distrib/source/proftpd-1.3.9.tar.gz

# 2. 解壓縮
tar zxvf proftpd-1.3.9.tar.gz

# 3. 進入目錄
cd proftpd-1.3.9

# 4. 設定編譯選項
./configure

# 5. 編譯
make

# 6. 安裝
sudo make install

# 確認是否安裝成功
/usr/local/sbin/proftpd -v
```

#### 設定 ProFTPD 目錄

```bash
# 建立 FTP 根目錄 (可於 UI 中自訂)
sudo mkdir -p /backup/ftpdata
sudo chown nobody:nobody /backup/ftpdata
sudo chmod 755 /backup/ftpdata
```

## 🔧 使用方式

### 啟動應用程式

#### 開發模式

```bash
# 啟用虛擬環境
source venv/bin/activate

# 設定開發環境
export FLASK_CONFIG=development

# 啟動開發伺服器
python run.py
```

#### 生產模式

```bash
# 啟用虛擬環境
source venv/bin/activate

# 設定生產環境
export FLASK_CONFIG=production

# 使用 Gunicorn 啟動（建議）
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app

# 或直接啟動
python run.py
```

### 建立系統服務（可選）

建立 systemd 服務檔案以便系統啟動時自動運行：

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

# 啟用並啟動服務
sudo systemctl daemon-reload
sudo systemctl enable proftpd-admin
sudo systemctl start proftpd-admin
```

### 存取 Web 介面

開啟瀏覽器，訪問 `http://服務器IP:5000`

預設管理員帳號：
- 用戶名：`admin`
- 密碼：`admin123`

⚠️ **安全提醒**: 首次登入後請立即更改預設密碼！

## 📖 功能說明

### 1. 用戶管理
- 新增/編輯/刪除 FTP 用戶
- 設定用戶家目錄、UID/GID
- 群組成員管理
- 批次操作支援

### 2. 群組管理
- 建立/編輯/刪除 FTP 群組
- 成員批次添加/移除
- 群組權限設定

### 3. 權限管理
- 目錄權限設定（讀取、寫入、刪除）
- 即時權限矩陣顯示
- 權限繼承設定

### 4. 監控功能
- 即時 FTP 連線狀態
- 系統資源使用情況
- 日誌檔案分析
- 統計報表生成

### 5. 系統設定
- FTP 伺服器參數調整
- 安全設定配置
- 自動備份設定
- 管理員帳號管理

## ✅ 開發狀態

### 已完成功能
- [x] 專案基礎結構（目錄、配置文件）
- [x] SQLite 資料庫模型（用戶、群組、權限、設定）
- [x] Flask Web 應用程式框架
- [x] Web 管理者認證系統
- [x] 用戶管理 CRUD 功能
- [x] 群組管理 CRUD 功能
- [x] 目錄權限管理功能
- [x] ProFTPD 配置檔自動生成功能
- [x] 監控功能（連線狀態、統計、磁碟使用量）
- [x] 系統設定管理介面
- [x] HTML 模板文件

### 系統整合狀態
✅ **完整實作完成** - 所有規劃功能均已實現並可正常運作

## 🔒 安全考量

1. **密碼安全**: 使用強密碼，定期更換
2. **檔案權限**: 確保配置檔案權限正確設定
3. **網路安全**: 建議使用 HTTPS，限制存取 IP
4. **備份策略**: 定期備份資料庫和配置檔
5. **系統更新**: 保持系統和套件更新

## 🛠️ 開發說明

### 開發環境設定

```bash
# 克隆專案
git clone <repository-url>
cd proftpd-admin

# 建立開發用虛擬環境
python3 -m venv venv-dev
source venv-dev/bin/activate

# 安裝開發依賴
pip install -r requirements.txt
pip install pytest flask-testing coverage

# 設定開發環境變數
export FLASK_CONFIG=development
export FLASK_DEBUG=1

# 啟動開發伺服器
python run.py
```

### 技術架構

- **後端**: Flask + SQLAlchemy + Flask-Login
- **前端**: Bootstrap 5 + Vanilla JavaScript + AJAX
- **資料庫**: SQLite (可擴展至 PostgreSQL/MySQL)
- **認證**: Flask-Login + 密碼雜湊
- **表單**: Flask-WTF + WTForms + CSRF 保護
- **架構**: Blueprint 模組化設計

## 📝 版本歷史

- **v1.0.0** (2025-7): 初始完整版本
  - 完整用戶/群組管理功能
  - 權限管理系統
  - 即時監控介面
  - 系統設定功能
  - 備份功能
  - 多語系

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request 來改善這個專案。

## 📄 授權

本專案採用 MIT 授權條款。

## 📞 支援

如有問題或需要協助，請：

1. 查閱 `CLAUDE.md` 開發文件
2. 檢查系統日誌：`tail -f /var/log/proftpd/proftpd.log`
3. 查看應用程式日誌：`journalctl -u proftpd-admin -f`
4. 提交 Issue 到專案倉庫

---

**注意**: 本系統需要適當的系統管理權限才能正常運作，請確保在安全的環境中部署使用。