import requests
import time

headers = {
        'ngrok-skip-browser-warning': 'true',  # 跳过 ngrok 的浏览器警告
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'  # 模拟浏览器
    }

proxies = {
    'http': 'http://localhost:8080',
    # 'https': 'https://bca2a33cfef4.ngrok-free.app'
}


def test_proxy():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"尝试 #{attempt + 1}...")
            response = requests.get('http://phoenix.stu.edu.cn/bt/default.aspx',
                                    proxies=proxies,
                                    timeout=10,
                                    headers=headers)

            if response.status_code == 200:
                print("代理测试成功！")
                print("状态码:", response.status_code)
                try:
                    print("响应内容:", response.json())
                except:
                    print("响应内容:", response.text[:500])
                return True
            else:
                print(f"代理返回错误状态码: {response.status_code}")
                print("错误信息:", response.text[:500])
                return False

        except requests.exceptions.ChunkedEncodingError as e:
            print(f"分块编码错误: {str(e)}")
            if attempt < max_retries - 1:
                print("等待1秒后重试...")
                time.sleep(1)
            else:
                print("达到最大重试次数，测试失败")
                return False

        except Exception as e:
            print("代理测试失败:", str(e))
            return False


if __name__ == '__main__':
    print("开始代理服务器测试...")
    if test_proxy():
        print("测试成功完成！")
    else:
        print("测试失败")