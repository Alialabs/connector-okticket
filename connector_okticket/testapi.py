import http.client
import requests
import urllib.parse
import json

conn = http.client.HTTPConnection("dev.okticket.es")

url = "http://dev.okticket.es/api/public/oauth/token"

payload = {'client_id': '6', 'client_secret': 'kXKp79g5gPAwqbgR2091UDyvlKKIkW7WvPYYbPFU', 'grant_type': 'password','username': 'user@test.com', 'password': 'usertest', 'scope': '*'}
payload_json=json.dumps(payload)

headers = {
 # 'content-type': "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW",
 'Content-Type': "application/json",
 'cache-control': "no-cache",
 }

#response = requests.request("POST", url, data=payload, headers=headers)

conn.request("POST", url, payload_json, headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))