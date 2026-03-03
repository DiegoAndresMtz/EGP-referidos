import sys

with open("templates/admin.html", "r") as f:
    content = f.read()

content = content.replace("{ { advisor_performance", "{{ advisor_performance")
content = content.replace(") } },", ") }},")

with open("templates/admin.html", "w") as f:
    f.write(content)
