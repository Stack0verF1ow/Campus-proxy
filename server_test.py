import requests

proxies = {
    'http': 'http://admin:securepassword@localhost:8081',
    'https': 'http://admin:securepassword@localhost:8081'
}

try:
    print("发送请求...")
    response = requests.get('http://httpbin.org/get', proxies=proxies)

    print(f"状态码: {response.status_code}")
    print(f"响应头: {response.headers}")

    if response.status_code == 200:
        print("代理测试成功！")
        try:
            print("响应内容:", response.json())
        except:
            print("响应内容:", response.text[:500])
    else:
        print(f"代理返回错误状态码: {response.status_code}")
        print("错误信息:", response.text[:500])

except Exception as e:
    print("代理测试失败:", str(e))
    if hasattr(e, 'response'):
        print(f"响应状态码: {e.response.status_code}")
        print(f"响应头: {e.response.headers}")
        print(f"响应内容: {e.response.text[:500]}")