from django.db import migrations

SESSIONS = [
    (1, "Introduction to AI, AI in Business, Types of AI"),
    (2, "AI Landscape, Generative AI, Business Use Cases"),
    (3, "Prompt Engineering Basics, Prompt Anatomy, Best Practices"),
    (4, "Advanced Prompting, Role Prompting, Prompt Refinement"),
    (5, "AI Ethics, Hallucinations, Privacy & Bias"),
    (6, "AI Productivity for Managers, Daily AI Workflow, Case Study"),
    (7, "Business Email Writing, Professional Communication, Tone Adjustment"),
    (8, "Report Writing, Meeting Minutes, Executive Summaries"),
    (9, "Proposal Writing, SOP Creation, Policy Documentation"),
    (10, "Resume Writing, LinkedIn Optimization, Cover Letters"),
    (11, "AI Research, Citation, Fact Verification"),
    (12, "Competitor Analysis, SWOT Analysis, Industry Trends"),
    (13, "Excel with AI, Formula Generation, Data Cleaning"),
    (14, "Charts, KPI Dashboard, Business Insights"),
    (15, "PowerPoint with AI, Storytelling, Presentation Design"),
    (16, "AI Presentation Enhancement, Speaker Notes, Visual Storytelling"),
    (17, "Social Media Strategy, Content Calendar, Content Planning"),
    (18, "Customer Persona, Buyer Journey, Market Segmentation"),
    (19, "A/B Ad Copy, Headlines, Call-to-Action"),
    (20, "AI Marketing Campaign Planning, Campaign Strategy, Brand Messaging"),
    (21, "Canva AI, Brand Kit, Templates"),
    (22, "AI Image Generation, Product Posters, Promotional Designs"),
    (23, "Video Script Writing, Reel Planning, Storyboarding"),
    (24, "AI Video Creation, Editing, Caption Generation"),
    (25, "AI Voice Generation, Podcasts, Voiceovers"),
    (26, "AI for Branding, Logo Concepts, Creative Design"),
    (27, "AI for HR, Job Description, Resume Screening"),
    (28, "AI for Recruitment, Interview Questions, Candidate Evaluation"),
    (29, "AI in Finance, Budget Planning, Forecasting"),
    (30, "AI in Sales, CRM, Lead Generation"),
    (31, "AI in Operations, Supply Chain, Inventory"),
    (32, "AI Decision Making, Scenario Planning, Risk Analysis"),
    (33, "Microsoft Copilot Advanced Features, Office Automation, Productivity"),
    (34, "NotebookLM, Knowledge Management, Document Summarisation"),
    (35, "Workflow Automation, No-Code Automation, AI Integration"),
    (36, "AI Agents, Business Assistants, Task Automation"),
    (37, "AI for Entrepreneurship, Business Model Generation, Idea Validation"),
    (38, "AI for Consulting, Client Presentations, Proposal Development"),
    (39, "AI for Personal Productivity, Time Management, Learning"),
    (40, "Emerging AI Tools, Multimodal AI, AI Trends"),
    (41, "Responsible AI, Ethics, Governance"),
    (42, "Data Privacy, Cybersecurity, AI Compliance"),
    (43, "Retail & Marketing Case Study, Customer Analytics, Campaign Optimisation"),
    (44, "Finance & HR Case Study, AI Decision Support, Business Intelligence"),
    (45, "Capstone Project Planning, Problem Definition, Solution Design"),
    (46, "Capstone Project Development, Testing, Documentation"),
    (47, "Project Presentation, Business Pitch, Evaluation"),
    (48, "Viva Voce, Future of AI, Programme Wrap-up"),
]


def seed(apps, schema_editor):
    SyllabusSession = apps.get_model("syllabus", "SyllabusSession")
    for number, topics in SESSIONS:
        SyllabusSession.objects.get_or_create(session_number=number, defaults={"topics": topics})


def unseed(apps, schema_editor):
    SyllabusSession = apps.get_model("syllabus", "SyllabusSession")
    SyllabusSession.objects.filter(session_number__in=[n for n, _ in SESSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("syllabus", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
