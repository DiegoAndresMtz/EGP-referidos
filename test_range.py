from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/static/videos/prado-norte.mp4", headers={"Range": "bytes=0-100"})
print(response.status_code)
print(response.headers)
