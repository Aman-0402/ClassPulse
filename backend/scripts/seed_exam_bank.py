"""One-off: seed 100 MCQs + 50 practical questions (25 easy / 25 hard) into
the exam question bank, then schedule one open exam per section using them.

Safe to re-run: MCQs/practicals are matched by exact text (get_or_create), so
re-running won't duplicate the bank; it WILL create a new exam each time
though, since exams aren't deduplicated (each has its own window) — delete
old ones first if re-running this for a fresh batch.

cPanel Execute-python-script path: scripts/seed_exam_bank.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import setup_django

setup_django()

from django.utils import timezone

from accounts.models import StudentProfile, User
from exams.models import Exam, MCQQuestion, PracticalQuestion

# (question, option_a, option_b, option_c, option_d, correct_letter)
MCQS = [
    ("What does AI stand for?", "Automated Interface", "Artificial Intelligence", "Applied Informatics", "Auto Integration", "b"),
    ("Which of these is a type of AI that mimics human-like understanding across many tasks?", "Narrow AI", "General AI", "Weak AI", "Rule-based AI", "b"),
    ("Which company created ChatGPT?", "Google", "Microsoft", "OpenAI", "Meta", "c"),
    ("What is 'Generative AI' primarily used for?", "Deleting duplicate files", "Creating new content like text, images, or audio", "Sorting spreadsheets", "Compressing videos", "b"),
    ("In prompt engineering, what is a 'prompt'?", "A software bug", "The input instruction given to an AI model", "A type of database", "A network protocol", "b"),
    ("Which of these is an example of 'role prompting'?", "Asking the AI to act as a marketing expert before answering", "Restarting the AI model", "Uninstalling the AI app", "Clearing browser cache", "a"),
    ("What is 'prompt refinement'?", "Deleting a prompt permanently", "Iteratively improving a prompt to get better AI output", "Encrypting a prompt", "Translating a prompt to another language", "b"),
    ("What is an AI 'hallucination'?", "A rendering glitch in a video game", "When an AI confidently generates false or made-up information", "A hardware failure", "A type of malware", "b"),
    ("Why is data privacy a concern when using AI tools?", "AI tools never store any data", "Sensitive information shared with AI tools could be exposed or misused", "AI tools only work offline", "Privacy is not relevant to AI", "b"),
    ("What does 'bias' mean in the context of AI?", "An AI model running faster than expected", "Unfair or skewed outcomes caused by the data or design of an AI system", "A type of encryption", "A network firewall setting", "b"),
    ("What is one benefit of using AI for daily workflow automation?", "It always eliminates the need for human review", "It can save time on repetitive tasks", "It guarantees zero errors", "It removes the need for internet access", "b"),
    ("When writing a professional email with AI assistance, what should you always do before sending?", "Send it immediately without reading", "Review and edit the AI-generated draft for accuracy and tone", "Forward it to everyone in the company", "Translate it into a random language", "b"),
    ("What is the purpose of an Executive Summary in a report?", "To list every technical detail in full", "To give a brief, high-level overview of the report's key points", "To replace the entire report", "To show the report's formatting settings", "b"),
    ("What does 'SOP' stand for in business documentation?", "Standard Operating Procedure", "System Output Protocol", "Sales Order Processing", "Structured Output Plan", "a"),
    ("What is a key benefit of using AI to help write a resume?", "It guarantees a job offer", "It can help phrase achievements clearly and consistently", "It removes the need to proofread", "It automatically applies to jobs for you", "b"),
    ("Why should AI-generated research be fact-checked?", "AI research is always 100% accurate", "AI can generate inaccurate or outdated information", "Fact-checking is illegal", "AI cannot access any information", "b"),
    ("What is a SWOT analysis used for?", "Encrypting business data", "Evaluating Strengths, Weaknesses, Opportunities, and Threats", "Scheduling employee shifts", "Formatting spreadsheets", "b"),
    ("In Excel, which AI-assisted feature helps generate formulas from plain language?", "Formula Generation", "Cell Merging", "Print Preview", "Page Layout", "a"),
    ("What is a KPI?", "Key Performance Indicator", "Known Process Input", "Keyboard Program Interface", "Key Privacy Instruction", "a"),
    ("What is the main purpose of a dashboard in business reporting?", "To store raw unformatted data only", "To visually summarize key metrics for quick insights", "To send emails automatically", "To back up files", "b"),
    ("When using AI to help design a presentation, what does 'storytelling' refer to?", "Adding random images", "Structuring the presentation to guide the audience through a clear narrative", "Using only bullet points", "Removing all text from slides", "b"),
    ("What are 'speaker notes' used for in a presentation?", "Sharing on social media", "Providing the presenter with additional talking points not shown to the audience", "Setting the slide background color", "Recording the presentation duration only", "b"),
    ("What is a content calendar used for in social media strategy?", "Blocking spam accounts", "Planning and scheduling content posts in advance", "Encrypting messages", "Deleting old posts automatically", "b"),
    ("What is a 'buyer persona'?", "A legal contract", "A semi-fictional representation of an ideal customer", "A type of payment gateway", "A software license", "b"),
    ("In marketing, what does 'CTA' stand for?", "Call to Action", "Customer Tax Agreement", "Content Transfer API", "Campaign Tracking Analysis", "a"),
    ("What is A/B testing used for in advertising?", "Comparing two versions of an ad to see which performs better", "Backing up ad campaigns", "Translating ads into multiple languages", "Blocking competitor ads", "a"),
    ("What is a 'brand kit' typically used for?", "Storing customer payment details", "Keeping a brand's logos, colors, and fonts consistent across materials", "Managing employee payroll", "Encrypting marketing emails", "b"),
    ("What does AI-based image generation allow you to create?", "Only black and white sketches", "New images from text descriptions", "Physical printed photos automatically", "3D printed objects directly", "b"),
    ("What is the purpose of a storyboard in video creation?", "To edit audio files", "To plan the visual sequence of a video before filming/creating it", "To compress video file size", "To generate subtitles automatically", "b"),
    ("What is one common use of AI voice generation?", "Creating narration or voiceovers without a human speaker", "Deleting audio tracks", "Encrypting voice calls", "Blocking spam calls", "a"),
    ("In HR, what is AI commonly used for in recruitment?", "Screening resumes and shortlisting candidates", "Approving employee vacations automatically", "Printing offer letters only", "Managing office furniture", "a"),
    ("What is one risk of using AI for candidate evaluation?", "It might introduce or amplify bias if not carefully managed", "It always eliminates bias completely", "It cannot be used for hiring at all", "It replaces the need for interviews entirely and legally", "a"),
    ("What is the purpose of budget forecasting in finance?", "To estimate future income and expenses", "To print physical currency", "To encrypt bank statements", "To close a business permanently", "a"),
    ("What does 'CRM' stand for in sales?", "Customer Relationship Management", "Central Revenue Model", "Client Response Metric", "Company Resource Manual", "a"),
    ("What is 'lead generation' in sales?", "Deleting inactive customer accounts", "The process of attracting and identifying potential customers", "Manufacturing physical products", "Auditing tax records", "b"),
    ("What is 'supply chain management' primarily concerned with?", "Managing the flow of goods and services from raw materials to the end customer", "Managing employee attendance only", "Designing company logos", "Writing marketing emails", "a"),
    ("What is 'scenario planning' used for in decision making?", "Exploring different possible future situations to prepare responses", "Formatting Excel spreadsheets", "Deleting outdated files", "Scheduling social media posts", "a"),
    ("What is Microsoft Copilot primarily designed to do?", "Assist users with tasks across Microsoft 365 apps using AI", "Replace all IT staff", "Physically repair computers", "Manage electricity bills", "a"),
    ("What is NotebookLM generally used for?", "Knowledge management and summarizing documents/sources", "Video editing", "3D modeling", "Network security scanning", "a"),
    ("What does 'workflow automation' aim to achieve?", "Automatically completing repetitive multi-step processes", "Manually redoing every task twice", "Deleting all workflows permanently", "Increasing manual paperwork", "a"),
    ("What is an 'AI agent' commonly designed to do?", "Perform tasks autonomously on behalf of a user, often multi-step", "Only display static text", "Replace all human decision-making by law", "Encrypt hard drives", "a"),
    ("What is 'business model generation' about?", "Designing how a business creates, delivers, and captures value", "Formatting a resume", "Encrypting emails", "Managing a printer queue", "a"),
    ("Why might a consultant use AI for client presentations?", "To quickly generate polished visuals and structured content", "To avoid ever meeting the client", "To permanently replace all client communication", "To automatically sign contracts", "a"),
    ("What is one way AI can support personal productivity?", "Helping prioritize and organize daily tasks", "Automatically deleting a user's calendar", "Disabling all notifications permanently", "Removing the need for sleep", "a"),
    ("What does 'multimodal AI' mean?", "AI that can process and generate multiple types of data, like text, images, and audio together", "AI that only works on mobile phones", "AI that requires no data", "AI that only understands numbers", "a"),
    ("What is 'Responsible AI' primarily concerned with?", "Ensuring AI is developed and used ethically, fairly, and safely", "Making AI run as fast as possible only", "Making AI more expensive", "Removing all human oversight", "a"),
    ("What does 'AI governance' refer to?", "The policies and frameworks guiding responsible AI use in an organization", "The physical wiring of servers", "A programming language", "A type of firewall", "a"),
    ("Why is cybersecurity important when adopting AI tools in a business?", "AI systems can introduce new vulnerabilities and data risks if not secured properly", "AI tools are immune to all security threats", "Cybersecurity is unrelated to AI", "AI tools do not process any data", "a"),
    ("What is the goal of a capstone project in a training program?", "To apply learned skills to solve a real, practical problem", "To repeat the first lesson of the course", "To skip the final evaluation", "To only read theory with no application", "a"),
    ("What typically happens during a 'Viva Voce'?", "An oral examination or discussion to assess understanding", "A written-only exam with no discussion", "A group vacation", "A software installation process", "a"),
    ("Which of these best describes 'Narrow AI'?", "AI designed to perform a specific task well, without general reasoning", "AI that can perform every human task equally", "AI that has no practical use", "AI that only works with paper documents", "a"),
    ("What is the main purpose of 'fact verification' when using AI-generated research?", "Confirming that AI-provided information is accurate before relying on it", "Making the research longer", "Translating the research into another language", "Formatting the research document", "a"),
    ("What is a common feature of AI-powered chatbots in customer service?", "Answering common customer questions automatically", "Physically shipping products", "Setting company tax rates", "Printing invoices only on paper", "a"),
    ("What does 'tone adjustment' mean in AI-assisted writing?", "Changing the audio volume of a recording", "Modifying the style of writing to be more formal, casual, friendly, etc.", "Adjusting the screen brightness", "Changing the font size only", "b"),
    ("What is 'policy documentation' used for in a business?", "Recording official rules and procedures for employees to follow", "Tracking stock market prices", "Designing product packaging", "Managing social media likes", "a"),
    ("What is the purpose of 'cover letters' when applying for a job?", "To introduce yourself and explain your interest and fit for a role", "To list your favorite hobbies only", "To replace a resume entirely", "To request a salary advance", "a"),
    ("What is 'citation' important for in research writing?", "Giving credit to original sources and avoiding plagiarism", "Making a document longer", "Hiding the source of information", "Formatting page numbers only", "a"),
    ("What does 'industry trends' analysis help a business understand?", "Emerging patterns and shifts within a market or sector", "The personal hobbies of employees", "The weather forecast", "The company's parking policy", "a"),
    ("What is the purpose of 'data cleaning' in Excel or data analysis?", "Removing errors, duplicates, and inconsistencies from a dataset", "Deleting the entire dataset", "Changing the file format only", "Printing the data on paper", "a"),
    ("What can charts help communicate more effectively than raw numbers?", "Patterns and trends at a glance", "Nothing, charts are purely decorative", "Only the file size of a document", "The exact source code used", "a"),
    ("What is the goal of 'visual storytelling' in a presentation?", "Using images, layout, and design to support and enhance the narrative", "Removing all visuals from slides", "Making every slide the same color", "Avoiding any structure", "a"),
    ("What is 'market segmentation'?", "Dividing a broader market into groups of customers with similar needs", "Combining all customers into a single group", "Setting product prices randomly", "Deleting inactive customer records", "a"),
    ("What is one purpose of a 'campaign strategy' in marketing?", "To define goals, audience, and approach for a marketing effort", "To hire new employees only", "To manage IT infrastructure", "To file company taxes", "a"),
    ("What does 'brand messaging' refer to?", "The core message and tone a brand consistently communicates", "The technical specifications of a product", "The internal server architecture", "The company's holiday schedule", "a"),
    ("What is 'caption generation' typically used for in video content?", "Automatically creating text captions/subtitles for videos", "Compressing video resolution", "Blocking video uploads", "Changing video file names randomly", "a"),
    ("What is a common purpose of AI-assisted logo concepts?", "Quickly exploring visual branding ideas", "Legally registering a trademark automatically", "Manufacturing physical signage", "Filing business taxes", "a"),
    ("What does 'candidate evaluation' in recruitment typically assess?", "A candidate's skills, experience, and fit for a role", "A candidate's home address only", "A candidate's social media follower count", "A candidate's favorite food", "a"),
    ("What is the purpose of 'risk analysis' in decision making?", "Identifying and assessing potential risks before making a decision", "Guaranteeing there will be zero risk", "Avoiding all decisions entirely", "Only assessing risks after a decision fails", "a"),
    ("What is 'office automation' generally intended to do?", "Streamline repetitive administrative tasks in daily office work", "Replace all office furniture", "Disconnect all office computers from the internet", "Eliminate the need for any staff", "a"),
    ("What is a 'no-code automation' tool designed for?", "Building automated workflows without traditional programming", "Writing complex low-level code only", "Formatting hard drives", "Compiling C++ programs", "a"),
    ("What is 'idea validation' in entrepreneurship?", "Testing whether a business idea has real market demand before investing heavily", "Copyrighting an idea automatically", "Publishing an idea publicly with no research", "Skipping all customer research", "a"),
    ("What does 'time management' primarily help improve?", "How effectively a person organizes and uses their available time", "The speed of a computer's processor", "The internet connection speed", "The battery life of a laptop", "a"),
    ("What is a key trend often discussed under 'emerging AI tools'?", "New AI capabilities and applications becoming available over time", "The complete disappearance of all software tools", "The banning of AI in every industry", "The removal of the internet", "a"),
    ("What is one goal of 'business intelligence' tools?", "Turning raw data into actionable insights for decision-making", "Encrypting all company emails", "Deleting outdated reports automatically", "Managing physical office space only", "a"),
    ("What does 'customer analytics' typically involve?", "Analyzing customer data to understand behavior and preferences", "Manually calling every customer daily", "Deleting customer records after one purchase", "Ignoring customer feedback entirely", "a"),
    ("What is the purpose of a 'problem definition' step in project planning?", "Clearly identifying the issue a project aims to solve", "Immediately starting to code without planning", "Skipping research entirely", "Assigning a random deadline with no context", "a"),
    ("What does 'testing' typically verify in project development?", "That the solution works correctly and meets requirements", "That the project has a nice color scheme only", "That the team took enough breaks", "That the budget was spent completely", "a"),
    ("What is the goal of a 'business pitch'?", "Persuasively presenting a business idea or plan to an audience", "Filing paperwork with no explanation", "Avoiding any audience interaction", "Reading a report verbatim with no context", "a"),
    ("What is one benefit of AI-assisted meeting minutes?", "Quickly summarizing key discussion points and action items", "Automatically canceling all meetings", "Deleting the meeting recording", "Scheduling unrelated events", "a"),
    ("What is 'proposal writing' generally used for in business?", "Formally suggesting a plan, project, or solution to stakeholders", "Recording daily attendance only", "Designing office layouts", "Managing email spam filters", "a"),
    ("What is one advantage of using AI for competitor analysis?", "Quickly gathering and summarizing information about competitors", "Automatically shutting down competitor businesses", "Guaranteeing 100% market share", "Eliminating the need for any strategy", "a"),
    ("What is a common use of AI in inventory management?", "Predicting stock needs and identifying shortages or surpluses", "Manually counting every item by hand only", "Deleting inventory records after each sale", "Ignoring supply and demand data", "a"),
    ("What is the purpose of an 'AI workflow' for daily productivity?", "A repeatable process using AI tools to complete regular tasks efficiently", "A one-time task never repeated", "A workflow that requires no tools at all", "A process that avoids using any software", "a"),
    ("Why is reviewing AI-generated content important before publishing?", "AI can make mistakes or produce content that needs human judgment", "AI-generated content is always perfect", "Reviewing wastes time and should be skipped", "AI content cannot be edited once generated", "a"),
    ("What is the main idea behind 'brand kit templates'?", "Reusable design templates that follow a consistent brand identity", "One-time-use designs that are deleted after use", "Templates with no connection to branding", "Templates only for internal IT documentation", "a"),
    ("What is a common application of AI in finance beyond budgeting?", "Forecasting trends and supporting financial decision-making", "Physically printing currency", "Replacing all financial regulations", "Eliminating the need for audits entirely", "a"),
    ("What is the purpose of 'document summarisation' tools like NotebookLM?", "Condensing long documents into key points for faster understanding", "Deleting documents permanently", "Encrypting documents so no one can read them", "Converting documents into video format only", "a"),
    ("What does 'AI compliance' generally refer to?", "Following relevant laws, regulations, and standards when using AI", "Ignoring all regulations related to AI", "A type of AI hardware component", "A marketing campaign name", "a"),
    ("What is the benefit of using templates in Canva AI for design work?", "Speeding up design creation while maintaining a consistent look", "Making every design look identical with no customization", "Preventing any design from being edited", "Requiring advanced coding skills", "a"),
    ("What is a common first step in the Version 1 development plan of a software project?", "Defining core requirements and scope", "Deploying to production immediately", "Skipping testing entirely", "Deleting the project repository", "a"),
    ("What is 'non-functional requirements' typically about in a system?", "Qualities like performance, security, and usability rather than specific features", "The exact color of the user interface only", "A list of employee names", "The company's holiday calendar", "a"),
    ("What is a 'functional requirement' in a project?", "A specific capability or behavior the system must perform", "A requirement about office furniture", "A requirement about employee lunch breaks", "A requirement unrelated to the system", "a"),
    ("Why is 'database design' an important step before building an application?", "It structures how data will be stored and related for the app to function correctly", "It is purely a decorative step with no real impact", "It replaces the need for any programming", "It only matters after the app is fully built", "a"),
    ("What do 'database relationships' typically describe?", "How different tables/entities in a database are connected to each other", "The personal relationships between employees", "The physical location of a server", "The color scheme of a dashboard", "a"),
    ("What does 'system architecture' refer to in software development?", "The high-level structure and components of a system and how they interact", "The furniture layout of an office", "The marketing plan for a product", "The employee organizational chart only", "a"),
    ("Which of the following best describes an 'attendance duration' setting in a QR-based attendance system?", "The time window during which a QR code remains valid for marking attendance", "The total number of students enrolled", "The color of the QR code", "The size of the classroom", "a"),
    ("Why do dynamic QR-based attendance systems rotate the QR code periodically?", "To prevent students from sharing or reusing an old QR code", "To make the QR code load slower", "To reduce the number of enrolled students", "To disable the camera on student phones", "a"),
    ("What is the primary purpose of 'duplicate attendance prevention' in an attendance system?", "Ensuring a student cannot be marked present more than once for the same session", "Allowing unlimited attendance marks per session", "Removing all attendance records daily", "Blocking every student from attending", "a"),
    ("What is the benefit of a 'real-time teacher dashboard' in an attendance system?", "Teachers can see attendance updates immediately as students check in", "Teachers can only see attendance the next day", "It removes the need for any attendance tracking", "It only works after the class has ended", "a"),
    ("What is 'suspicious activity detection' meant to identify in an attendance system?", "Unusual patterns like duplicate attempts or expired token usage", "The most popular student in class", "The fastest typing speed among students", "The classroom's Wi-Fi signal strength", "a"),
    ("Why is calculating 'attendance percentage' useful for students and teachers?", "It shows how consistently a student has attended classes over time", "It shows the student's exam scores", "It calculates the classroom's total area", "It sets the student's password", "a"),
]

# (question, difficulty) — target roughly half easy, half hard
PRACTICALS = [
    ("Write a professional email to your team informing them about a one-day delay in the project delivery, using an AI writing tool to draft it and then editing it for tone.", "easy"),
    ("Use an AI tool to generate 3 different subject lines for a marketing email promoting a new product launch.", "easy"),
    ("Create a short LinkedIn summary for yourself using AI assistance, then refine it to sound authentic.", "easy"),
    ("Use an AI prompt to summarize a one-page article into 3 bullet points.", "easy"),
    ("Draft a simple SOP (Standard Operating Procedure) for submitting a weekly expense report, using AI to help structure it.", "easy"),
    ("Use AI to generate 5 interview questions for hiring a Marketing Executive.", "easy"),
    ("Write meeting minutes for a hypothetical 30-minute team meeting, using AI to organize the key points and action items.", "easy"),
    ("Use an AI image generation tool to create a simple promotional poster concept for a college event.", "easy"),
    ("Draft a short social media caption for a product photo, using AI, in three different tones (formal, casual, playful).", "easy"),
    ("Use AI to create a basic content calendar for one week of social media posts for a small business.", "easy"),
    ("Write a cover letter for a Marketing Intern position using AI assistance, then personalize it.", "easy"),
    ("Use AI to generate a checklist of 5 items to verify before publishing a blog post.", "easy"),
    ("Create three different call-to-action (CTA) phrases for an online course landing page using AI.", "easy"),
    ("Use AI to draft a polite follow-up email after a job interview.", "easy"),
    ("Generate a short FAQ section (3 questions and answers) for a fictional mobile app using AI.", "easy"),
    ("Use AI to write a brief product description for a wireless earbud, highlighting 3 key features.", "easy"),
    ("Draft a simple thank-you message to a client after a successful project delivery, using AI assistance.", "easy"),
    ("Use AI to create a short script (30 seconds) for a Instagram Reel introducing a local coffee shop.", "easy"),
    ("Generate three alternative taglines for a fitness brand using AI, and pick the best one with reasoning.", "easy"),
    ("Use AI to write a brief internal announcement about a new office holiday policy.", "easy"),
    ("Create a simple Excel formula (with AI's help) to calculate the average of a column of sales data, and explain what it does.", "easy"),
    ("Use AI to draft a professional out-of-office auto-reply email.", "easy"),
    ("Generate a short elevator pitch (30 seconds) for a fictional startup idea using AI.", "easy"),
    ("Use AI to write 3 possible names for a new bakery business, with a one-line reasoning for each.", "easy"),
    ("Draft a simple onboarding welcome message for a new employee using AI assistance.", "easy"),
    ("Design an end-to-end AI-powered customer segmentation and marketing campaign strategy for a retail clothing brand, including data sources, the AI approach you would use, and how you would measure success.", "hard"),
    ("Build a complete SWOT analysis for a real or fictional company entering the food delivery market, using AI tools to research and structure the analysis, and present strategic recommendations.", "hard"),
    ("Design a full recruitment pipeline using AI: from resume screening, to interview question generation, to candidate evaluation criteria, for hiring a Data Analyst.", "hard"),
    ("Create a complete social media strategy for a new fitness brand for its first 3 months, including content calendar structure, target buyer personas, and campaign goals — using AI at each step.", "hard"),
    ("Develop a business plan outline for a subscription-based meal kit startup, including business model, target market, and a go-to-market strategy, using AI-assisted research and writing.", "hard"),
    ("Design a data-driven budget forecast model outline for a small business's next fiscal year, explaining what data you would use and how AI could support the forecasting.", "hard"),
    ("Create a full risk analysis and scenario plan for a company considering entering a new international market, covering at least 3 major risks and mitigation strategies.", "hard"),
    ("Design an AI-powered workflow automation for a customer support team handling repetitive email queries, including the tools you'd use and the steps involved.", "hard"),
    ("Build a capstone-style project plan for an AI chatbot that helps students find syllabus information, including problem definition, solution design, and a testing plan.", "hard"),
    ("Develop a complete brand identity concept (brand kit outline, messaging, and sample marketing copy) for a new eco-friendly packaging company, using AI throughout.", "hard"),
    ("Design an AI-supported inventory management approach for a mid-sized retail store, including how you would forecast demand and reduce stockouts.", "hard"),
    ("Create a full presentation outline (storyline, slide structure, and speaker notes) for pitching a new AI product to investors.", "hard"),
    ("Design a customer analytics dashboard concept for an e-commerce business, specifying the key metrics, data sources, and how AI could generate insights automatically.", "hard"),
    ("Build a detailed competitor analysis report structure for a company entering the AI-powered fitness app market, including at least 3 competitors and key comparison criteria.", "hard"),
    ("Design a responsible AI governance checklist for a mid-sized company adopting AI tools across departments, covering ethics, bias, privacy, and compliance.", "hard"),
    ("Develop a complete video content plan (storyboard, script outline, and distribution plan) for a 60-second brand awareness video, using AI tools throughout the process.", "hard"),
    ("Design an AI-assisted candidate evaluation rubric for hiring a Senior Software Engineer, including at least 5 evaluation criteria and how bias would be mitigated.", "hard"),
    ("Create a full go-to-market strategy for launching a new productivity app, including target audience, pricing strategy, and a 90-day marketing plan.", "hard"),
    ("Design a data privacy and cybersecurity checklist for a company deploying a customer-facing AI chatbot, covering at least 5 key safeguards.", "hard"),
    ("Build a complete proposal document outline for pitching an AI-powered attendance system (like this one) to a college administration, including problem statement, solution, and cost-benefit analysis.", "hard"),
    ("Design a scenario-planning exercise for a manufacturing business facing a potential supply chain disruption, covering best-case, worst-case, and most-likely scenarios with responses for each.", "hard"),
    ("Develop a full business model canvas for an AI-powered tutoring platform, covering value proposition, revenue streams, and key partnerships.", "hard"),
    ("Design an AI-supported employee performance review framework for a mid-sized company, including evaluation criteria and how AI could assist without introducing bias.", "hard"),
    ("Create a comprehensive report structure analyzing the attendance and academic performance correlation for a class section, including what data you'd need and how you'd present findings.", "hard"),
    ("Design a full disaster-recovery and business-continuity outline for a small e-commerce business, covering data backup, downtime response, and customer communication.", "hard"),
]

if __name__ == "__main__":
    teacher = User.objects.filter(role=User.ROLE_TEACHER).first()

    mcq_created = 0
    for text, a, b, c, d, correct in MCQS:
        _, created = MCQQuestion.objects.get_or_create(
            text=text,
            defaults={"option_a": a, "option_b": b, "option_c": c, "option_d": d, "correct_option": correct, "created_by": teacher},
        )
        mcq_created += created

    practical_created = 0
    easy_ids, hard_ids = [], []
    for text, difficulty in PRACTICALS:
        obj, created = PracticalQuestion.objects.get_or_create(
            text=text, defaults={"difficulty": difficulty, "created_by": teacher}
        )
        practical_created += created
        (easy_ids if obj.difficulty == "easy" else hard_ids).append(obj.id)

    print(f"MCQs: {mcq_created} created (total in bank: {MCQQuestion.objects.count()})")
    print(f"Practicals: {practical_created} created (total in bank: {PracticalQuestion.objects.count()})")

    easy = PracticalQuestion.objects.filter(id__in=easy_ids).first() or PracticalQuestion.objects.filter(difficulty="easy").first()
    hard = PracticalQuestion.objects.filter(id__in=hard_ids).first() or PracticalQuestion.objects.filter(difficulty="hard").first()

    sections = sorted(set(StudentProfile.objects.exclude(section="").values_list("section", flat=True)))
    now = timezone.now()
    created_exams = 0
    for section in sections:
        Exam.objects.create(
            title="AI Training Assessment 1",
            section=section,
            easy_practical=easy,
            hard_practical=hard,
            start_time=now,
            end_time=now + timezone.timedelta(days=14),
            manual_status=Exam.STATUS_FORCED_OPEN,
            created_by=teacher,
        )
        created_exams += 1
    print(f"Exams created/opened for sections: {sections} ({created_exams} total)")
