# -*- coding: utf-8 -*-
import requests
import json


def search_publications(query, dart_type="both"):
    """
    Send POST request to publication search API

    Args:
        query (str): Search query (e.g., "LG Electronics")
        dart_type (str): Type of search, defaults to "both"

    Returns:
        dict: API response
    """
    url = "http://211.188.53.220:2024/runs/wait"

    payload = {
        "assistant_id": "agent",
        "input": {
            "query": query,
            "dart_type": dart_type
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    print(f"[DEBUG] Publication API Request:")
    print(f"[DEBUG] URL: {url}")
    print(f"[DEBUG] Headers: {headers}")
    print(f"[DEBUG] Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        print(f"[DEBUG] Sending POST request...")
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        print(f"[DEBUG] Response status code: {response.status_code}")
        print(f"[DEBUG] Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            response_data = response.json()
            print(f"[DEBUG] Response data: {str(json.dumps(response_data, indent=2, ensure_ascii=False))[:300]}...")
            return response_data
        else:
            print(f"[DEBUG] Error response text: {response.text}")
            response.raise_for_status()

    except requests.exceptions.ConnectTimeout:
        print(f"[DEBUG] Connection timeout to {url}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[DEBUG] Connection error to {url} - service might not be running")
        return None
    except requests.exceptions.Timeout:
        print(f"[DEBUG] Request timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[DEBUG] JSON decode error: {e}")
        print(f"[DEBUG] Raw response: {response.text}")
        return None


if __name__ == "__main__":
    # Example usage
    result = search_publications("LG Electronics")
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        with open("pub_search_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)