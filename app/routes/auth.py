"""
认证路由模块
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app import db
from app.models import User, SiteConfig

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))

        flash('用户名或密码错误', 'error')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    reg_enabled = SiteConfig.get('registration_enabled', 'true')
    if reg_enabled != 'true':
        flash('注册功能已关闭', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not username or not password:
            flash('用户名和密码不能为空', 'error')
        elif len(username) < 3:
            flash('用户名至少3个字符', 'error')
        elif len(password) < 6:
            flash('密码至少6个字符', 'error')
        elif password != confirm:
            flash('两次密码输入不一致', 'error')
        elif User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
