import urllib.request
import re

url = "https://www.youtube.com/watch?v=4boN_FKyFNg"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        
        # Let's find ownerChannelName
        ch_match = re.search(r'"ownerChannelName"\s*:\s*"(.*?)"', html)
        if ch_match:
            print("CHANNEL:", ch_match.group(1).encode('ascii', 'ignore').decode('ascii'))
        
        # Let's find channelId
        cid_match = re.search(r'"channelId"\s*:\s*"(.*?)"', html)
        if cid_match:
            print("CHANNEL ID:", cid_match.group(1).encode('ascii', 'ignore').decode('ascii'))
            
        # Let's find any text corresponding to description
        # YouTube usually embeds description in ytInitialData
        desc_matches = re.findall(r'"shortDescription"\s*:\s*"(.*?)"', html)
        for i, d in enumerate(desc_matches[:3]):
            print(f"DESC_{i}:", d[:200].encode('ascii', 'ignore').decode('ascii'))
except Exception as e:
    print("ERROR:", e)
