#!/usr/bin/env python3
from app import create_app
from app.models import db
from flask import current_app

app = create_app()

@app.cli.command()
def init_db():
    """Initialize database"""
    db.create_all()
    print('Database initialized.')

@app.cli.command()
def create_admin():
    """Create admin user"""
    from app.models import AdminUser
    
    username = input('Admin username: ')
    email = input('Email: ')
    password = input('Password: ')
    
    admin = AdminUser(username=username, email=email)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f'Admin {username} created')

if __name__ == '__main__':
    # Setup user_loader
    from app import login_manager
    from app.models import AdminUser
    
    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))
    
    app.run(debug=True, host='0.0.0.0', port=5000)