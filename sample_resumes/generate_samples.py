"""Generate fictional test resumes. All names/contact details are synthetic."""
from pathlib import Path
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent

profiles = [
    ("Aarav Rao", "aarav.rao@example.test", "+1 202 555 0101", "6 years", "B.Tech Computer Science", ["Java", "Spring Boot", "REST API", "SQL", "PostgreSQL", "Docker", "AWS", "Microservices", "Redis", "Git", "Agile"], "Backend Engineer", "Built payment and order services using Java and Spring Boot. Designed REST APIs, tuned PostgreSQL queries and deployed Docker containers to AWS. Worked with Redis caching, microservice patterns and CI/CD pipelines."),
    ("Nisha Verma", "nisha.verma@example.test", "+1 202 555 0102", "5 years", "Bachelor's degree in Information Technology", ["Java", "Spring Boot", "REST API", "SQL", "MySQL", "Redis", "Git", "Agile", "Docker"], "Java Developer", "Developed enterprise Java applications and Spring Boot services. Implemented REST APIs, database integrations and caching. Worked with MySQL, Redis, Git and Agile Scrum teams; basic exposure to AWS."),
    ("Kabir Sen", "kabir.sen@example.test", "+1 202 555 0103", "4 years", "B.E. Computer Engineering", ["Java", "Spring Boot", "SQL", "PostgreSQL", "Docker", "Linux", "REST API", "Git"], "Backend Developer", "Implemented Java Spring Boot applications and RESTful APIs. Designed relational schemas and SQL queries in PostgreSQL, containerized services with Docker and supported deployments on Linux."),
    ("Meera Das", "meera.das@example.test", "+1 202 555 0104", "3 years", "B.Tech Information Technology", ["Python", "Django", "FastAPI", "PostgreSQL", "Docker", "REST API", "Git", "AWS"], "Python Backend Developer", "Built API services with Python, Django and FastAPI. Designed PostgreSQL schemas, wrote REST endpoints and deployed containerized applications to AWS. Collaborated with frontend engineers and used Git."),
    ("Rohan Iyer", "rohan.iyer@example.test", "+1 202 555 0105", "8 years", "M.Tech Software Engineering", ["Java", "Spring Boot", "Microservices", "REST API", "SQL", "PostgreSQL", "Docker", "AWS", "Kubernetes", "Redis", "CI/CD", "Linux", "Git", "Agile"], "Senior Backend Engineer", "Led design of high-throughput Java Spring Boot microservices. Built REST APIs, optimized PostgreSQL and SQL, introduced Redis caching, deployed Docker workloads to AWS and Kubernetes, and owned CI/CD reliability."),
    ("Sara Khan", "sara.khan@example.test", "+1 202 555 0106", "2 years", "B.Sc Computer Science", ["Java", "SQL", "Spring", "Git", "HTML", "CSS", "Postman"], "Junior Java Developer", "Maintained Java applications, fixed defects and wrote SQL queries. Assisted with Spring MVC endpoints, API testing in Postman and version control using Git. Interested in cloud and microservices."),
    ("Dev Patel", "dev.patel@example.test", "+1 202 555 0107", "4.5 years", "Bachelor's in Computer Applications", ["JavaScript", "TypeScript", "Node.js", "Express", "React", "PostgreSQL", "MongoDB", "Docker", "AWS", "REST API", "Git", "Agile"], "Full Stack Developer", "Built Node.js and Express backend APIs with React and TypeScript frontends. Used PostgreSQL and MongoDB, Dockerized services and deployed to AWS. Designed REST APIs and worked in Agile teams."),
    ("Ishita Bose", "ishita.bose@example.test", "+1 202 555 0108", "5.5 years", "B.Tech Computer Science", ["Java", "Spring Boot", "SQL", "PostgreSQL", "REST API", "Microservices", "Docker", "AWS", "Kubernetes", "Redis", "CI/CD", "Git"], "Backend Engineer", "Designed Java Spring Boot microservices for account and billing workflows. Developed REST APIs, wrote optimized PostgreSQL queries and deployed Docker services on AWS and Kubernetes. Used Redis and CI/CD automation."),
    ("Vikram Shah", "vikram.shah@example.test", "+1 202 555 0109", "7 years", "M.Sc Data Science", ["Python", "Machine Learning", "Deep Learning", "PyTorch", "Pandas", "NumPy", "SQL", "Docker", "AWS", "NLP"], "Machine Learning Engineer", "Built machine learning pipelines in Python using PyTorch, Pandas and NumPy. Deployed inference services with Docker and AWS, queried analytical SQL databases and developed NLP prototypes."),
    ("Tara Ghosh", "tara.ghosh@example.test", "+1 202 555 0110", "3.5 years", "B.Tech Computer Science", ["Java", "Spring Boot", "REST API", "SQL", "PostgreSQL", "Docker", "Git", "Linux", "Microservices", "Postman"], "Software Engineer", "Developed Java Spring Boot services and REST APIs. Worked with PostgreSQL, SQL query optimization, Docker and Linux environments. Contributed to microservice integrations and API testing using Postman."),
]

for index, (name, email, phone, years, education, skills, role, summary) in enumerate(profiles, start=1):
    lines = [
        name, f"{email} | {phone}", role, "", "PROFESSIONAL SUMMARY",
        f"{years} of professional experience. {summary}", "", "TECHNICAL SKILLS",
        ", ".join(skills), "", "PROFESSIONAL EXPERIENCE",
        f"{role} | Example Systems | 2020 - Present",
        summary,
        "", "EDUCATION", education,
        "", "PROJECT HIGHLIGHTS",
        "Delivered maintainable software, participated in code reviews, wrote tests and collaborated with cross-functional teams.",
    ]
    if index in {2, 5, 8, 10}:
        path = OUT / f"sample_{index:02d}_{name.split()[0].lower()}.pdf"
        pdf = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        y = height - 55
        for line in lines:
            if y < 55:
                pdf.showPage(); y = height - 55
            pdf.setFont("Helvetica-Bold" if line in {name, "PROFESSIONAL SUMMARY", "TECHNICAL SKILLS", "PROFESSIONAL EXPERIENCE", "EDUCATION", "PROJECT HIGHLIGHTS"} else "Helvetica", 11 if line == name else 9)
            pdf.drawString(48, y, line[:110])
            y -= 17 if line else 9
        pdf.save()
    else:
        path = OUT / f"sample_{index:02d}_{name.split()[0].lower()}.docx"
        doc = Document()
        for line in lines:
            if line in {"PROFESSIONAL SUMMARY", "TECHNICAL SKILLS", "PROFESSIONAL EXPERIENCE", "EDUCATION", "PROJECT HIGHLIGHTS"}:
                doc.add_heading(line.title(), level=2)
            elif line == name:
                doc.add_heading(line, level=0)
            else:
                doc.add_paragraph(line)
        doc.save(path)

print(f"Generated {len(profiles)} fictional resumes in {OUT}")
