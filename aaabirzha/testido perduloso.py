import requests

url = 'http://localhost:8000/api/v1/public/register'
payload ={'name': 'foo'}
resp = requests.post(url=url, json=payload)
print(resp.json())