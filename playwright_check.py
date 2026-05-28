import sys
sys.path.insert(0, '/app')

try:
    from backend.browsing_adapter import BrowsingAdapter
    
    # Test requests provider
    adapter_req = BrowsingAdapter(provider='requests')
    result = adapter_req.fetch("https://example.com", timeout=10)
    print(f"[OK] Requests provider: {len(result['html'])} bytes")
    
    # Test playwright provider
    adapter_pw = BrowsingAdapter(provider='playwright')
    if adapter_pw._playwright_adapter:
        print("[OK] Playwright provider: Available")
    else:
        print("[WARN] Playwright provider: Not loaded yet")
        
except Exception as e:
    print(f"[FAIL] Error: {e}")
