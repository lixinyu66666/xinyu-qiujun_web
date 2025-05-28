# Xinyu & Qiujun - Love Anniversary Website

A Flask-based personal love anniversary website to record beautiful moments together. Updated on 2025-05-28.

## Features

- Track days since the beginning (December 10, 2022)
- 100-day milestone celebrations
- Beautiful photo gallery with fullscreen view
- Journal system to record memories
- Password protection

## 重要提示: Vercel 部署问题解决方案

在 Vercel 上添加日志报错的解决方案:

### 问题原因

Vercel 是一个**无状态服务平台**，它不允许服务端持久化写入文件系统。当您尝试添加日志时，服务器试图将内容写入到 journal.json 文件，但在 Vercel 环境中这种操作是不允许的，因此导致了 500 内部服务器错误。

### 解决方案: 使用 MongoDB 数据库

应用已更新为支持 MongoDB，可以按以下步骤设置：

1. 注册并登录 [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. 创建一个免费层级的数据库集群
3. 在安全设置中，添加用户名和密码
4. 在网络访问设置中，允许从任何地址访问 (添加 0.0.0.0/0)
5. 获取连接字符串，格式类似: `mongodb+srv://username:password@cluster.mongodb.net/mydb?retryWrites=true&w=majority`

## Deploying to Vercel

1. Push code to GitHub repository
2. Connect GitHub repository in Vercel
3. Configure custom domain xinyu-qiujun.fun
4. Set up environment variables (see below)

## Environment Variables

在 Vercel 项目设置中添加以下环境变量:

- `PASSWORD`: 网站访问密码
- `SECRET_KEY`: Flask 会话密钥
- `MONGODB_URI`: MongoDB Atlas 连接字符串
- `MONGODB_DB`: 数据库名称 (例如: `journal_db`)
- `VERCEL`: 设置为 `1`

## Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` file and set environment variables:
   ```
   SECRET_KEY=your_random_secret_key
   PASSWORD=your_password
   # 如果本地使用 MongoDB (可选)
   # MONGODB_URI=your_mongodb_connection_string
   # MONGODB_DB=journal_db
   ```
3. Run: `python app.py`
4. 访问 http://localhost:8080

## 故障排除

如果在 Vercel 上仍然遇到错误:

1. 检查 Vercel 部署日志
2. 确认 MongoDB 连接字符串正确
3. 确认所有环境变量都已正确设置
4. 重新从 GitHub 部署项目
