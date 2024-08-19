import requests

def monitor_endpoints(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return {"status": "success", "message": f"{url} is up"}
        else:
            return {"status": "failure", "message": f"{url} is down"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}
