from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy import or_
from . import bp
from .forms import FtpGroupForm, GroupMembersForm, GroupSearchForm
from ..models import FtpGroup, FtpUser, GroupMembership, db
from ..utils import log_action, get_next_gid, sync_proftpd_files, reload_proftpd

@bp.route('/')
@bp.route('/list')
@login_required
def list():
    """群組列表頁面"""
    search_form = GroupSearchForm()
    
    # 基礎查詢
    query = FtpGroup.query
    
    # 處理搜尋
    if request.args.get('search'):
        search_term = request.args.get('search')
        query = query.filter(or_(
            FtpGroup.groupname.contains(search_term),
            FtpGroup.description.contains(search_term)
        ))
    
    # 分頁
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('GROUPS_PER_PAGE', 20)
    
    groups = query.order_by(FtpGroup.groupname).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('groups/list.html', groups=groups, search_form=search_form)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """創建新群組"""
    form = FtpGroupForm()
    
    # 設定預設 GID
    if request.method == 'GET':
        form.gid.data = get_next_gid()
    
    if form.validate_on_submit():
        try:
            group = FtpGroup(
                groupname=form.groupname.data,
                gid=form.gid.data,
                description=form.description.data
            )
            
            db.session.add(group)
            db.session.commit()
            
            # 同步 ProFTPD 檔案
            success, message = sync_proftpd_files()
            if success:
                reload_proftpd()
                flash('群組創建成功', 'success')
            else:
                flash(f'群組創建成功，但同步失敗: {message}', 'warning')
            
            log_action('create_group', 'group', group.id, f'創建群組: {group.groupname}')
            return redirect(url_for('groups.list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'創建群組失敗: {str(e)}', 'error')
    
    return render_template('groups/create.html', form=form)

@bp.route('/<int:id>')
@login_required
def detail(id):
    """群組詳情頁面"""
    group = FtpGroup.query.get_or_404(id)
    return render_template('groups/detail.html', group=group)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """編輯群組"""
    group = FtpGroup.query.get_or_404(id)
    form = FtpGroupForm(original_group=group, obj=group)
    
    if form.validate_on_submit():
        try:
            group.groupname = form.groupname.data
            group.gid = form.gid.data
            group.description = form.description.data
            
            db.session.commit()
            
            # 同步 ProFTPD 檔案
            success, message = sync_proftpd_files()
            if success:
                reload_proftpd()
                flash('群組更新成功', 'success')
            else:
                flash(f'群組更新成功，但同步失敗: {message}', 'warning')
            
            log_action('edit_group', 'group', group.id, f'編輯群組: {group.groupname}')
            return redirect(url_for('groups.detail', id=group.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新群組失敗: {str(e)}', 'error')
    
    return render_template('groups/edit.html', form=form, group=group)

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """刪除群組"""
    group = FtpGroup.query.get_or_404(id)
    groupname = group.groupname
    
    # 檢查是否有用戶依賴此群組
    member_count = GroupMembership.query.filter_by(group_id=id).count()
    if member_count > 0:
        flash(f'無法刪除群組 {groupname}，因為仍有 {member_count} 個用戶屬於此群組', 'error')
        return redirect(url_for('groups.detail', id=id))
    
    try:
        db.session.delete(group)
        db.session.commit()
        
        # 同步 ProFTPD 檔案
        success, message = sync_proftpd_files()
        if success:
            reload_proftpd()
            flash(f'群組 {groupname} 已刪除', 'success')
        else:
            flash(f'群組已刪除，但同步失敗: {message}', 'warning')
        
        log_action('delete_group', 'group', id, f'刪除群組: {groupname}')
        
    except Exception as e:
        db.session.rollback()
        flash(f'刪除群組失敗: {str(e)}', 'error')
    
    return redirect(url_for('groups.list'))

@bp.route('/<int:id>/members', methods=['GET', 'POST'])
@login_required
def manage_members(id):
    """管理群組成員"""
    group = FtpGroup.query.get_or_404(id)
    form = GroupMembersForm()
    
    # 設定目前成員
    current_member_ids = [membership.user_id for membership in group.members]
    if request.method == 'GET':
        form.members.data = current_member_ids
    
    if form.validate_on_submit():
        try:
            # 獲取新的成員ID列表
            new_member_ids = set(form.members.data)
            current_member_ids = set(current_member_ids)
            
            # 找出要添加和移除的成員
            to_add = new_member_ids - current_member_ids
            to_remove = current_member_ids - new_member_ids
            
            # 移除成員
            for user_id in to_remove:
                membership = GroupMembership.query.filter_by(
                    group_id=group.id, user_id=user_id
                ).first()
                if membership:
                    db.session.delete(membership)
            
            # 添加成員
            for user_id in to_add:
                membership = GroupMembership(group_id=group.id, user_id=user_id)
                db.session.add(membership)
            
            db.session.commit()
            
            # 同步檔案
            success, message = sync_proftpd_files()
            if success:
                reload_proftpd()
                flash('群組成員已更新', 'success')
            else:
                flash(f'成員更新成功，但同步失敗: {message}', 'warning')
            
            log_action('update_group_members', 'group', group.id, 
                      f'更新群組 {group.groupname} 的成員')
            
            return redirect(url_for('groups.detail', id=group.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新成員失敗: {str(e)}', 'error')
    
    return render_template('groups/members.html', group=group, form=form)

@bp.route('/<int:group_id>/add_member/<int:user_id>', methods=['POST'])
@login_required
def add_member(group_id, user_id):
    """添加單個成員到群組"""
    group = FtpGroup.query.get_or_404(group_id)
    user = FtpUser.query.get_or_404(user_id)
    
    # 檢查是否已經是成員
    existing = GroupMembership.query.filter_by(
        group_id=group_id, user_id=user_id
    ).first()
    
    if existing:
        flash(f'用戶 {user.username} 已經是 {group.groupname} 群組的成員', 'info')
    else:
        try:
            membership = GroupMembership(group_id=group_id, user_id=user_id)
            db.session.add(membership)
            db.session.commit()
            
            flash(f'已將用戶 {user.username} 加入群組 {group.groupname}', 'success')
            log_action('add_member_to_group', 'group', group.id, 
                      f'將用戶 {user.username} 加入群組 {group.groupname}')
            
            # 同步檔案
            sync_proftpd_files()
            reload_proftpd()
            
        except Exception as e:
            db.session.rollback()
            flash(f'添加成員失敗: {str(e)}', 'error')
    
    return redirect(url_for('groups.detail', id=group_id))

@bp.route('/<int:group_id>/remove_member/<int:user_id>', methods=['POST'])
@login_required
def remove_member(group_id, user_id):
    """從群組中移除成員"""
    membership = GroupMembership.query.filter_by(
        group_id=group_id, user_id=user_id
    ).first_or_404()
    
    try:
        group_name = membership.group.groupname
        user_name = membership.user.username
        
        db.session.delete(membership)
        db.session.commit()
        
        flash(f'已將用戶 {user_name} 從群組 {group_name} 中移除', 'success')
        log_action('remove_member_from_group', 'group', group_id, 
                  f'將用戶 {user_name} 從群組 {group_name} 中移除')
        
        # 同步檔案
        sync_proftpd_files()
        reload_proftpd()
        
    except Exception as e:
        db.session.rollback()
        flash(f'移除成員失敗: {str(e)}', 'error')
    
    return redirect(url_for('groups.detail', id=group_id))

@bp.route('/api/check_groupname')
@login_required
def check_groupname():
    """檢查群組名稱是否可用 (AJAX)"""
    groupname = request.args.get('groupname', '').strip()
    group_id = request.args.get('group_id', type=int)
    
    if not groupname:
        return jsonify({'available': False, 'message': '群組名稱不能為空'})
    
    query = FtpGroup.query.filter_by(groupname=groupname)
    if group_id:  # 編輯模式，排除當前群組
        query = query.filter(FtpGroup.id != group_id)
    
    existing = query.first()
    
    return jsonify({
        'available': existing is None,
        'message': '群組名稱可用' if existing is None else '群組名稱已存在'
    })

@bp.route('/api/suggest_gid')
@login_required
def suggest_gid():
    """建議下一個可用的 GID (AJAX)"""
    gid = get_next_gid()
    return jsonify({'gid': gid})