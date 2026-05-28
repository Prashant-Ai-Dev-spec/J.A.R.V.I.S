import sys
sys.path.insert(0, '/app')

try:
    from backend.browsing_adapter import BrowsingAdapter
    print("[OK] BrowsingAdapter imported")
    
    # Test requests provider (should work)
    adapter_req = BrowsingAdapter(provider='requests')
    print("[OK] Requests adapter instantiated")
    
    try:
        result = adapter_req.fetch("https://example.com", timeout=10)
        print(f"[OK] Requests fetch succeeded: {len(result['html'])} bytes")
    except Exception as e:
        print(f"[WARN] Requests fetch failed: {str(e)[:100]}")
    
    # Test playwright provider
    adapter_pw = BrowsingAdapter(provider='playwright')
    print("[OK] Playwright adapter instantiated")
    
    if adapter_pw._playwright_adapter:
        print("[OK] PlaywrightAdapter available")
        try:
            result = adapter_pw.fetch("https://example.com", timeout=10)
            print(f"[OK] Playwright fetch succeeded: {type(result)}")
        except Exception as e:
            print(f"[WARN] Playwright fetch failed: {str(e)[:150]}")
    else:
        print("[WARN] PlaywrightAdapter not loaded (may need installation)")
        
except Exception as e:
    print(f"[FAIL] Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
