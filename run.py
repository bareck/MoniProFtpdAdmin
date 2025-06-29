#!/usr/bin/env python3
from app import create_app
from app.models import db
from flask import current_app

app = create_app()

@app.cli.command()
def init_db():
    """初始化資料庫"""
    db.create_all()
    print('Database initialized.')

@app.cli.command()
def create_admin():
    """創建管理員用戶"""
    from app.models import AdminUser
    
    username = input('管理員用戶名: ')
    email = input('電子郵件: ')
    password = input('密碼: ')
    
    admin = AdminUser(username=username, email=email)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f'管理員 {username} 已創建')

if __name__ == '__main__':
    # 設定 user_loader
    from app import login_manager
    from app.models import AdminUser
    
    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))
    
    app.run(debug=True, host='0.0.0.0', port=5000)