// 全局认证对象
window.Auth = {
    // 检查是否已登录
    isAuthenticated: function() {
        return !!localStorage.getItem('auth_token');
    },

    // 获取认证令牌
    getToken: function() {
        return localStorage.getItem('auth_token');
    },

    // 跳转到登录页面
    redirectToLogin: function() {
        // 清除本地存储的令牌
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
    },

    // 设置请求头
    withAuthHeader: function(headers = {}) {
        const token = this.getToken();
        if (token) {
            return {
                ...headers,
                'Authorization': `Bearer ${token}`
            };
        }
        return headers;
    },

    // 处理API响应
    handleResponse: function(response) {
        if (response.status === 401) {
            this.redirectToLogin();
            return null;
        }
        return response.json();
    },

    // 初始化登录页面
    initLoginPage: function() {
        document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            try {
                const response = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                if (response.ok) {
                    const data = await response.json();
                    // 保存令牌
                    localStorage.setItem('auth_token', data.token);

                    // 重定向到主应用页面
                    window.location.href = '/app';
                } else {
                    const error = await response.json();
                    alert(`登录失败: ${error.error}`);
                }
            } catch (err) {
                console.error('登录请求失败:', err);
                alert('网络请求失败');
            }
        });
    }
};

// 如果是登录页面，初始化登录表单
if (window.location.pathname === '/login') {
    document.addEventListener('DOMContentLoaded', function() {
        Auth.initLoginPage();
    });
}