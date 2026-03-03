import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.models import User, Lead, LeadStatus
from fastapi.templating import Jinja2Templates

try:
    templates = Jinja2Templates(directory="templates")

    async def main():
        async with async_session() as db:
            result = await db.execute(select(User).where(User.role == 'ADMIN'))
            admin = result.scalars().first()
            if not admin:
                print("No admin found")
                return

            result_adv = await db.execute(select(User).where(User.role == 'ASESOR'))
            advisors = result_adv.scalars().all()
            
            advisor_performance = {}
            for adv in advisors:
                advisor_performance[adv.id] = {
                    "total": 5, "ganados": 1, "perdidos": 2, "en_proceso": 2
                }
                
            ctx = {
                "request": {"url": {"path": "/admin"}, "query_params": {}},
                "user": admin,
                "tab": "overview",
                "stats": {"recent_leads": 12, "pending_leads": 0},
                "top_projects": [],
                "all_advisors": advisors,
                "advisor_performance": advisor_performance,
            }
            
            tmpl = templates.get_template("admin.html")
            rendered = tmpl.render(ctx)
            
            start_idx = rendered.find('const advisors =')
            if start_idx != -1:
                print(rendered[start_idx:start_idx+600])
            else:
                print("Not found")

    asyncio.run(main())
except Exception as e:
    import traceback
    traceback.print_exc()
