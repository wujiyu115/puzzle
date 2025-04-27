"""
应用入口点
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    # 使用0.0.0.0作为主机以允许外部访问API接口
    # Web管理界面通过装饰器限制只能从本地访问
    app.run(debug=True, host='0.0.0.0')
