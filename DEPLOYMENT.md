# 部署指南

本应用使用 Flask 框架开发，可以部署到 Vercel 平台。

## 准备工作

### MongoDB Atlas 设置

1. 创建 [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) 免费账户
2. 创建一个新集群（选择免费层 M0）
3. 在"Security"中创建一个数据库用户
4. 在"Network Access"中设置 IP 访问权限（允许所有 IP：0.0.0.0/0）
5. 在"Databases"中点击"Connect"按钮，选择"Connect your application"，并复制连接字符串

### 环境变量配置

在 Vercel 部署前，需要设置以下环境变量：

1. `MONGODB_URI` - MongoDB Atlas 连接字符串（替换用户名和密码）
2. `MONGODB_DB` - 数据库名称（例如：journal_db）
3. `SECRET_KEY` - 应用密钥（生成随机字符串）
4. `PASSWORD` - 网站登录密码
5. `USE_GRIDFS_STORAGE` - 设置为 "true"
6. `VERCEL` - 设置为 "1"

## 部署步骤

### 使用 Vercel CLI

1. 安装 Vercel CLI：
   ```
   npm install -g vercel
   ```

2. 登录 Vercel：
   ```
   vercel login
   ```

3. 部署项目：
   ```
   cd /path/to/project
   vercel
   ```

4. 按照提示操作，配置环境变量。

### 使用 Vercel 网站

1. 在 [Vercel](https://vercel.com/) 注册并登录
2. 导入 Git 仓库或上传项目
3. 设置环境变量
4. 点击部署

## 验证部署

1. 访问部署成功后的 URL
2. 登录应用（使用环境变量中设置的 PASSWORD）
3. 测试图像上传和显示功能

## 故障排除

如果部署后遇到问题：

1. 检查 Vercel 日志
2. 确认环境变量是否正确设置
3. 验证 MongoDB Atlas 连接是否正常

## 注意事项

1. Vercel 免费版有限制，包括函数执行时间（10秒）和部署大小
2. MongoDB Atlas 免费版有 512MB 存储限制
3. GridFS 适合存储小型图片（建议不超过 4MB）
