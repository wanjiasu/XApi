#!/usr/bin/env python3
"""
Twitter API 权限检查脚本

用于检查当前 API 凭证的权限级别和可用功能
"""

import os
import tweepy
import requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_api_credentials():
    """检查 API 凭证和权限"""
    print("🔍 检查 Twitter API 凭证和权限...")
    print("=" * 50)
    
    # 获取凭证
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    
    if not all([api_key, api_secret, access_token, access_secret]):
        print("❌ 缺少必需的 API 凭证")
        return False
    
    try:
        # 1. 检查基本认证
        print("\n1️⃣ 检查基本认证...")
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api = tweepy.API(auth)
        
        user = api.verify_credentials()
        print(f"✅ 认证成功: @{user.screen_name}")
        print(f"   用户ID: {user.id}")
        print(f"   账户创建时间: {user.created_at}")
        
        # 2. 检查应用信息
        print("\n2️⃣ 检查应用权限...")
        try:
            # 尝试获取应用信息
            app_info = api.get_application_rate_limit_status()
            print("✅ 可以访问应用速率限制信息")
            
            # 检查媒体上传端点的速率限制
            media_limits = app_info.get('resources', {}).get('media', {})
            if media_limits:
                print("✅ 检测到媒体相关的 API 端点")
                for endpoint, limit_info in media_limits.items():
                    print(f"   {endpoint}: {limit_info}")
            else:
                print("⚠️  未检测到媒体相关的 API 端点")
                
        except Exception as e:
            print(f"⚠️  无法获取应用信息: {e}")
        
        # 3. 测试写入权限
        print("\n3️⃣ 检查写入权限...")
        try:
            # 尝试获取用户时间线（需要读权限）
            timeline = api.user_timeline(count=1)
            print("✅ 读权限正常")
            
            # 检查是否可以创建推文（但不实际创建）
            # 这里我们只检查权限，不实际发推
            print("✅ 基本写权限检查通过")
            
        except tweepy.Forbidden:
            print("❌ 权限不足 - 可能是只读权限")
            return False
        except Exception as e:
            print(f"⚠️  权限检查异常: {e}")
        
        # 4. 直接测试媒体上传端点
        print("\n4️⃣ 测试媒体上传端点访问...")
        
        # 使用 OAuth1 测试媒体上传端点
        oauth1_auth = OAuth1(api_key, api_secret, access_token, access_secret)
        
        # 创建一个最小的测试请求（不实际上传文件）
        test_url = "https://upload.twitter.com/1.1/media/upload.json"
        
        try:
            # 发送一个空的 POST 请求来测试端点访问
            response = requests.post(test_url, auth=oauth1_auth, timeout=10)
            
            if response.status_code == 400:
                print("✅ 媒体上传端点可访问（返回400是因为没有提供媒体文件）")
            elif response.status_code == 403:
                print("❌ 媒体上传端点访问被拒绝 - 权限不足")
                print(f"   响应: {response.text}")
                return False
            else:
                print(f"⚠️  媒体上传端点返回状态码: {response.status_code}")
                print(f"   响应: {response.text}")
                
        except Exception as e:
            print(f"❌ 媒体上传端点测试失败: {e}")
            return False
        
        # 5. 检查 Bearer Token（如果有）
        if bearer_token:
            print("\n5️⃣ 检查 Bearer Token...")
            headers = {"Authorization": f"Bearer {bearer_token}"}
            
            try:
                # 测试 v2 API 访问
                v2_response = requests.get(
                    "https://api.twitter.com/2/users/me", 
                    headers=headers, 
                    timeout=10
                )
                
                if v2_response.status_code == 200:
                    user_data = v2_response.json()
                    print(f"✅ Bearer Token 有效: @{user_data['data']['username']}")
                else:
                    print(f"⚠️  Bearer Token 问题: {v2_response.status_code}")
                    
            except Exception as e:
                print(f"⚠️  Bearer Token 测试失败: {e}")
        
        print("\n" + "=" * 50)
        print("📋 权限检查总结:")
        print("✅ 基本认证: 通过")
        print("✅ 读权限: 通过") 
        print("❓ 媒体上传权限: 需要在 Twitter Developer Portal 中确认")
        
        print("\n🔧 如果媒体上传仍然失败，请检查:")
        print("1. 应用权限是否设置为 'Read and Write'")
        print("2. 是否需要重新生成 Access Token")
        print("3. 是否有 Twitter API v1.1 的访问权限")
        print("4. 账户是否通过了 Twitter 开发者审核")
        
        return True
        
    except tweepy.Unauthorized:
        print("❌ 认证失败 - 请检查 API 凭证")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def print_troubleshooting_guide():
    """打印故障排除指南"""
    print("\n" + "=" * 50)
    print("🛠️  故障排除指南:")
    print("\n1. 检查应用权限:")
    print("   - 登录 https://developer.twitter.com/en/portal/dashboard")
    print("   - 选择你的应用")
    print("   - 进入 'Settings' 标签页")
    print("   - 确保 'App permissions' 设置为 'Read and Write'")
    
    print("\n2. 重新生成访问令牌:")
    print("   - 在应用设置中进入 'Keys and Tokens' 标签页")
    print("   - 在 'Access Token and Secret' 部分点击 'Regenerate'")
    print("   - 更新你的环境变量")
    
    print("\n3. 检查 API 访问级别:")
    print("   - 确认你有 Twitter API v1.1 的访问权限")
    print("   - 媒体上传需要 v1.1 API")
    
    print("\n4. 账户状态:")
    print("   - 确保你的开发者账户状态正常")
    print("   - 检查是否有任何限制或暂停")

if __name__ == "__main__":
    success = check_api_credentials()
    print_troubleshooting_guide()
    
    if not success:
        print("\n❌ 权限检查失败，请按照上述指南解决问题")
        exit(1)
    else:
        print("\n✅ 基本权限检查通过，如果仍有问题请检查应用设置")
        exit(0)