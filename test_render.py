from fastapi.templating import Jinja2Templates
from app.models.models import User, UserRole
import datetime

templates = Jinja2Templates(directory="templates")

all_advisors = [
    User(id=1, name="John", last_name="Doe", role=UserRole.ASESOR, email="john@example.com", phone="123")
]

advisor_performance = {
    1: {"ganados": 5, "en_proceso": 2, "perdidos": 1}
}

try:
    print(templates.get_template("admin.html").render({
        "request": None, 
        "tab": "overview",
        "all_advisors": all_advisors,
        "advisor_performance": advisor_performance,
        "user": all_advisors[0],
        "stats": {"total_leads": 10, "closed_leads": 5, "in_progress_leads": 2, "pending_leads": 0, "conversion_rate": "50.0"},
        "leads_by_status": [],
        "leads_by_month": []
    }))
    print("RENDER SUCCESSFUL")
except Exception as e:
    print(f"RENDER ERORR: {e}")
