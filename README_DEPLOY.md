# 云服务器部署故障排除指南

## 问题描述
在云服务器上部署时出现 "All media upload attempts failed" 错误。

## 常见原因和解决方案

### 1. 环境变量配置问题

**检查步骤：**
```bash
# 运行部署检查脚本
python deploy_check.py
```

**解决方案：**
1. 复制 `.env.example` 为 `.env`
2. 填入正确的 Twitter API 凭证
3. 确保所有必需的环境变量都已设置：
   - `TWITTER_API_KEY`
   - `TWITTER_API_SECRET`
   - `TWITTER_ACCESS_TOKEN`
   - `TWITTER_ACCESS_TOKEN_SECRET`

### 2. 网络连接问题

**常见问题：**
- 云服务器防火墙阻止出站连接
- DNS 解析问题
- SSL/TLS 证书验证失败

**解决方案：**
```bash
# 测试网络连接
curl -I https://upload.twitter.com/1.1/media/upload.json
curl -I https://api.twitter.com/2/tweets

# 检查防火墙设置
sudo ufw status
sudo iptables -L

# 确保允许 HTTPS 出站连接
sudo ufw allow out 443
```

### 3. Twitter API 权限问题

**检查权限：**
1. 登录 [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. 确认应用有以下权限：
   - Read and Write
   - Media upload 权限

**重新生成令牌：**
如果权限有问题，需要重新生成 Access Token。

### 4. 文件系统问题

**检查文件权限：**
```bash
# 确保图片文件存在且可读
ls -la image.png
chmod 644 image.png

# 检查应用目录权限
ls -la /path/to/your/app/
```

### 5. 系统时间同步

**Twitter API 对时间敏感，确保系统时间正确：**
```bash
# 检查系统时间
date
timedatectl status

# 同步时间
sudo ntpdate -s time.nist.gov
# 或者
sudo chrony sources -v
```

### 6. 依赖包版本问题

**更新依赖包：**
```bash
pip install --upgrade -r requirements.txt
```

**检查关键包版本：**
```bash
pip show tweepy requests requests-oauthlib
```

## 增强的错误日志

更新后的代码包含详细的错误日志，运行时会显示：
- 具体的HTTP状态码和错误消息
- 网络连接错误详情
- 文件大小和路径信息
- 每个上传方法的尝试结果

## 调试步骤

1. **运行部署检查：**
   ```bash
   python deploy_check.py
   ```

2. **查看详细日志：**
   ```bash
   # 启动应用并查看日志
   uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
   ```

3. **测试单个上传方法：**
   ```bash
   # 运行测试脚本
   python test.py
   ```

4. **手动测试 API 端点：**
   ```bash
   curl -X POST "http://your-server:8000/tweet" \
        -H "Content-Type: application/json" \
        -d '{"text": "test tweet", "image_path": "image.png"}'
   ```

## 云服务器特定配置

### Docker 部署
如果使用 Docker，确保：
```dockerfile
# 安装 ca-certificates 用于 SSL 验证
RUN apt-get update && apt-get install -y ca-certificates

# 设置时区
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
```

### 系统服务配置
```bash
# 创建 systemd 服务文件
sudo nano /etc/systemd/system/twitter-service.service
```

```ini
[Unit]
Description=Twitter Media Upload Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/your/app
Environment=PATH=/path/to/your/venv/bin
ExecStart=/path/to/your/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 监控和日志

**设置日志轮转：**
```bash
# 创建 logrotate 配置
sudo nano /etc/logrotate.d/twitter-service
```

**监控服务状态：**
```bash
# 检查服务状态
sudo systemctl status twitter-service

# 查看日志
sudo journalctl -u twitter-service -f
```

## 联系支持

如果问题仍然存在，请提供：
1. `deploy_check.py` 的完整输出
2. 应用启动时的日志
3. 云服务器的系统信息 (`uname -a`, `cat /etc/os-release`)
4. 网络配置信息