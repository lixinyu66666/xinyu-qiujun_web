# 心语秋君 - 恋爱纪念网站

这是一个基于Flask的个人恋爱纪念网站，用于记录美好的时光。

## 部署到Vercel

1. 将代码推送到GitHub仓库
2. 在Vercel中连接GitHub仓库
3. 配置自定义域名 xinyu-qiujun.fun
4. 设置环境变量

## 环境变量设置

在Vercel项目设置中添加以下环境变量：
- `PASSWORD`: 网站访问密码
- `SECRET_KEY`: Flask会话密钥

## 本地开发

1. 安装依赖：`pip install -r requirements.txt`
2. 创建 `.env` 文件并设置环境变量
3. 运行：`python app.py`
