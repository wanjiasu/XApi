import tweepy
import os
import requests
from requests_oauthlib import OAuth1

API_KEY = '93n4BrrNygzcOy4gnld1Dqo7e'
API_SECRET = 'i1qpfIO6FocqlHSegwzpcemfbNzTYPai43Uku76IIaHSEf6Xmm'
ACCESS_TOKEN = '1982475146603769856-4fJfeXWlpzqCOu3PMA6WpswaWStmhW'
ACCESS_TOKEN_SECRET = 'vun5wmOG9I831l7p4ARO5FyrRxTzG5oypDy2AvQunAXTk'

# 检查图片文件是否存在
if not os.path.exists('image.png'):
    print("Error: image.png file not found!")
    exit(1)

# 方法1：使用X API官方文档的媒体上传端点
def upload_media_x_api():
    print("尝试使用X API官方媒体上传端点...")
    
    # 创建OAuth1认证
    auth = OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    
    # 读取图片文件
    with open('image.png', 'rb') as f:
        media_data = f.read()
    
    # 根据官方文档，使用正确的参数
    files = {'media': ('image.png', media_data, 'image/png')}
    data = {
        'media_category': 'tweet_image',  # 必需参数
        'media_type': 'image/png'        # 指定媒体类型
    }
    
    # 使用正确的端点URL
    url = 'https://upload.twitter.com/1.1/media/upload.json'
    
    try:
        response = requests.post(url, auth=auth, files=files, data=data)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            return result.get('media_id_string')
        else:
            print(f"上传失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None

# 方法2：使用Bearer Token的OAuth 2.0方式（如果有的话）
def upload_media_oauth2():
    print("尝试使用OAuth 2.0方式上传媒体...")
    
    bearer_token = 'AAAAAAAAAAAAAAAAAAAAAJEr5AEAAAAAHUY8PFSSeqbq2BbMHDvkIDMrHOY%3Do15vvk5wdxS1vxmXtqOn1uOdN0CMxLc4saXPCFasJYRMWpfOCr'
    
    headers = {
        'Authorization': f'Bearer {bearer_token}',
    }
    
    # 读取图片文件
    with open('image.png', 'rb') as f:
        media_data = f.read()
    
    files = {'media': ('image.png', media_data, 'image/png')}
    data = {
        'media_category': 'tweet_image',
        'media_type': 'image/png'
    }
    
    url = 'https://upload.twitter.com/1.1/media/upload.json'
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            return result.get('media_id_string')
        else:
            print(f"上传失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None

# 方法3：使用传统的tweepy v1.1端点作为备选
def upload_media_tweepy():
    print("尝试使用tweepy库上传媒体...")
    
    # OAuth1 认证
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    
    # 测试认证
    try:
        user = api.verify_credentials()
        print(f"Authentication successful! Logged in as: @{user.screen_name}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None
    
    # 上传图片
    try:
        media = api.media_upload(filename='image.png')
        print("Media uploaded successfully! media_id:", media.media_id_string)
        return media.media_id_string
    except tweepy.errors.Forbidden as e:
        print(f"403 Forbidden Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during media upload: {e}")
        return None

# 按优先级尝试不同的上传方法
print("=== 尝试方法1：X API官方端点 ===")
media_id = upload_media_x_api()

if not media_id:
    print("\n=== 尝试方法2：OAuth 2.0方式 ===")
    media_id = upload_media_oauth2()

if not media_id:
    print("\n=== 尝试方法3：tweepy库 ===")
    media_id = upload_media_tweepy()

if not media_id:
    print("所有媒体上传方法都失败了")
    exit(1)

print(f"\n✅ 媒体上传成功！Media ID: {media_id}")

# 使用 v2 的 client 创建帖文
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    bearer_token='AAAAAAAAAAAAAAAAAAAAAJEr5AEAAAAAHUY8PFSSeqbq2BbMHDvkIDMrHOY%3Do15vvk5wdxS1vxmXtqOn1uOdN0CMxLc4saXPCFasJYRMWpfOCr'
)

text = "a test"
response = client.create_tweet(text=text, media_ids=[media.media_id_string])
print("Tweet posted. response:", response)
