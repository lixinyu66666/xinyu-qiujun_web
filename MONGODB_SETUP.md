# MongoDB Atlas 设置指南

本指南将帮助您在 MongoDB Atlas 上设置数据库，用于存储日志条目和图像（通过 GridFS）。

## 步骤 1：创建 MongoDB Atlas 账户

1. 访问 [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. 注册一个新账户或使用 Google、GitHub 等登录

## 步骤 2：创建新集群

1. 登录后，点击"Build a Database"
2. 选择"FREE"（M0 级别）
3. 选择云提供商（AWS、GCP 或 Azure）和区域（建议选择最接近您用户的区域）
4. 点击"Create Cluster"（可能需要几分钟来创建集群）

## 步骤 3：设置数据库访问

1. 在左侧菜单的"Security"部分，点击"Database Access"
2. 点击"Add New Database User"
3. 选择"Password"认证方式
4. 设置用户名和密码（请记住这些信息）
5. 在"Database User Privileges"中，选择"Atlas admin"
6. 点击"Add User"

## 步骤 4：设置网络访问

1. 在左侧菜单的"Security"部分，点击"Network Access"
2. 点击"Add IP Address"
3. 对于 Vercel 部署，选择"Allow Access from Anywhere"（0.0.0.0/0）
4. 点击"Confirm"

## 步骤 5：获取连接字符串

1. 在"Database"部分，点击"Connect"
2. 选择"Connect your application"
3. 选择驱动类型"Python"和版本"3.6 or later"
4. 复制连接字符串，它看起来像这样：
   ```
   mongodb+srv://<username>:<password>@<cluster-name>.mongodb.net/myFirstDatabase?retryWrites=true&w=majority
   ```
5. 将字符串中的`<username>`和`<password>`替换为您之前创建的用户名和密码
6. 将"myFirstDatabase"替换为您想要的数据库名（例如 "journal_db"）

## 步骤 6：配置应用程序

1. 在应用程序的`.env`文件中，添加：
   ```
   MONGODB_URI=您的连接字符串
   MONGODB_DB=journal_db
   USE_GRIDFS_STORAGE=true
   ```

## 注意事项

1. 免费层（M0）提供的存储空间限制为 512MB
2. 图片会存储在GridFS中，占用数据库空间
3. 为了避免数据库空间不足，请定期检查使用情况
4. 可以通过 MongoDB Atlas 控制台监控数据库使用情况

## 故障排除

如果连接失败，请检查：

1. 用户名和密码是否正确
2. IP 访问限制是否设置为允许所有地址（0.0.0.0/0）
3. 集群是否已完全创建和激活

## 数据库管理

您可以使用 MongoDB Compass（一个图形界面工具）来管理数据库：

1. 从 [MongoDB 网站](https://www.mongodb.com/products/compass) 下载并安装 MongoDB Compass
2. 使用连接字符串连接到您的数据库
3. 浏览和管理集合、查看图像等
