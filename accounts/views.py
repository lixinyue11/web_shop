"""账户视图"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .models import User


def login_view(request):
    """登录"""
    next_url = request.POST.get('next') if request.method == 'POST' else request.GET.get('next')
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
        next_url = ''
    if request.user.is_authenticated:
        if next_url:
            return redirect(next_url)
        if request.user.is_merchant:
            return redirect('merchant_dashboard')
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, '请输入用户名和密码')
            return render(request, 'accounts/login.html', {'next': next_url})

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'欢迎回来，{username}！')
            if next_url:
                return redirect(next_url)
            if user.is_merchant:
                return redirect('merchant_dashboard')
            return redirect('home')
        else:
            messages.error(request, '用户名或密码错误')

    return render(request, 'accounts/login.html', {'next': next_url})


def logout_view(request):
    """登出"""
    logout(request)
    messages.info(request, '已退出登录')
    return redirect('home')


def register_view(request):
    """顾客注册"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not username or not password:
            messages.error(request, '请输入用户名和密码')
        elif password != password2:
            messages.error(request, '两次密码不一致')
        elif User.objects.filter(username=username).exists():
            messages.error(request, '该用户名已存在，请换一个或直接登录')
        else:
            user = User.objects.create_user(username=username, password=password, user_type='customer')
            login(request, user)
            messages.success(request, '注册成功！')
            return redirect('home')

    return render(request, 'accounts/register.html')


def register_merchant_view(request):
    """商家注册"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not username or not password:
            messages.error(request, '请输入用户名和密码')
        elif password != password2:
            messages.error(request, '两次密码不一致')
        elif User.objects.filter(username=username).exists():
            messages.error(request, '该用户名已存在')
        else:
            user = User.objects.create_user(username=username, password=password, user_type='merchant')
            login(request, user)
            messages.success(request, '商家注册成功！')
            return redirect('merchant_dashboard')

    return render(request, 'accounts/register_merchant.html')
