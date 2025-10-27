#!/usr/bin/env python3
"""
部署检查脚本 - 验证云服务器环境配置

运行此脚本来检查：
1. 环境变量是否正确设置
2. 网络连接是否正常
3. Twitter API 凭证是否有效
4. 依赖包是否正确安装

使用方法：
    python deploy_check.py
"""

import os
import sys
import logging
import requests
import tweepy
from pathlib import Path
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def check_environment_variables():
    """检查必需的环境变量"""
    logger.info("🔍 检查环境变量...")
    
    # 加载 .env 文件
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv()
        logger.info("✅ 找到 .env 文件")
    else:
        logger.warning("⚠️  未找到 .env 文件，将检查系统环境变量")
    
    required_vars = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET", 
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            logger.error(f"❌ 缺少环境变量: {var}")
        else:
            logger.info(f"✅ {var}: {'*' * (len(value) - 4)}{value[-4:]}")
    
    # 检查可选变量
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if bearer_token:
        logger.info(f"✅ TWITTER_BEARER_TOKEN: {'*' * (len(bearer_token) - 4)}{bearer_token[-4:]}")
    else:
        logger.warning("⚠️  TWITTER_BEARER_TOKEN 未设置（可选）")
    
    if missing_vars:
        logger.error(f"❌ 缺少 {len(missing_vars)} 个必需的环境变量")
        return False
    
    logger.info("✅ 所有必需的环境变量都已设置")
    return True

def check_network_connectivity():
    """检查网络连接"""
    logger.info("🌐 检查网络连接...")
    
    test_urls = [
        "https://api.twitter.com",
        "https://upload.twitter.com", 
        "https://www.google.com"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            logger.info(f"✅ {url}: {response.status_code}")
        except requests.exceptions.Timeout:
            logger.error(f"❌ {url}: 连接超时")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ {url}: 连接错误")
            return False
        except Exception as e:
            logger.error(f"❌ {url}: {str(e)}")
            return False
    
    logger.info("✅ 网络连接正常")
    return True

def check_twitter_credentials():
    """检查 Twitter API 凭证"""
    logger.info("🐦 检查 Twitter API 凭证...")
    
    try:
        # 检查环境变量
        api_key = os.getenv("TWITTER_API_KEY")
        api_secret = os.getenv("TWITTER_API_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        
        if not all([api_key, api_secret, access_token, access_secret]):
            logger.error("❌ Twitter API 凭证不完整")
            return False
        
        # 测试 OAuth1 认证
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_secret
        )
        api = tweepy.API(auth)
        
        # 验证凭证
        user = api.verify_credentials()
        logger.info(f"✅ Twitter API 认证成功: @{user.screen_name}")
        
        # 检查权限
        logger.info(f"✅ 用户ID: {user.id}")
        logger.info(f"✅ 关注者数: {user.followers_count}")
        
        return True
        
    except tweepy.Unauthorized:
        logger.error("❌ Twitter API 认证失败：凭证无效")
        return False
    except tweepy.Forbidden:
        logger.error("❌ Twitter API 权限不足")
        return False
    except Exception as e:
        logger.error(f"❌ Twitter API 检查失败: {str(e)}")
        return False

def check_dependencies():
    """检查依赖包"""
    logger.info("📦 检查依赖包...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "tweepy",
        "requests",
        "requests-oauthlib",
        "python-dotenv",
        "pydantic"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            logger.info(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"❌ 缺少包: {package}")
    
    if missing_packages:
        logger.error(f"❌ 缺少 {len(missing_packages)} 个依赖包")
        logger.info("请运行: pip install -r requirements.txt")
        return False
    
    logger.info("✅ 所有依赖包都已安装")
    return True

def check_test_image():
    """检查测试图片文件"""
    logger.info("🖼️  检查测试图片...")
    
    test_images = ["image.png", "test.png", "sample.png"]
    
    for img in test_images:
        img_path = Path(img)
        if img_path.exists():
            size = img_path.stat().st_size
            logger.info(f"✅ 找到测试图片: {img} ({size} bytes)")
            
            # 检查文件大小
            if size > 5 * 1024 * 1024:  # 5MB
                logger.warning(f"⚠️  图片文件过大: {size} bytes (Twitter限制5MB)")
            
            return True
    
    logger.warning("⚠️  未找到测试图片文件")
    logger.info("建议创建一个测试图片文件 (image.png)")
    return False

def main():
    """主检查函数"""
    logger.info("🚀 开始部署环境检查...")
    logger.info("=" * 50)
    
    checks = [
        ("环境变量", check_environment_variables),
        ("网络连接", check_network_connectivity), 
        ("依赖包", check_dependencies),
        ("Twitter API凭证", check_twitter_credentials),
        ("测试图片", check_test_image)
    ]
    
    results = {}
    for name, check_func in checks:
        logger.info(f"\n📋 检查 {name}...")
        try:
            results[name] = check_func()
        except Exception as e:
            logger.error(f"❌ {name} 检查失败: {str(e)}")
            results[name] = False
    
    # 总结
    logger.info("\n" + "=" * 50)
    logger.info("📊 检查结果总结:")
    
    passed = 0
    total = len(results)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"  {name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 总体结果: {passed}/{total} 项检查通过")
    
    if passed == total:
        logger.info("🎉 所有检查都通过！环境配置正确。")
        return 0
    else:
        logger.error("💥 部分检查失败，请修复上述问题后重新运行。")
        return 1

if __name__ == "__main__":
    sys.exit(main())