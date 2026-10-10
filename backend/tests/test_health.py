from fastapi.testclient import TestClient

from app.main import app, handler


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_lambda_handler_serves_health():
    """The same app answers an API Gateway HTTP API (payload v2) event, as on AWS."""
    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "example.execute-api.us-east-1.amazonaws.com"},
        "requestContext": {
            "http": {"method": "GET", "path": "/health", "sourceIp": "127.0.0.1", "protocol": "HTTP/1.1"},
            "stage": "$default",
            "requestId": "test",
        },
        "isBase64Encoded": False,
    }
    result = handler(event, None)
    assert result["statusCode"] == 200
    assert '"status":"ok"' in result["body"]
