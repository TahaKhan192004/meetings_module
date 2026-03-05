from click import prompt
from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

def _generate(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text
def generate_client_consultation_context(user_input: str) -> str:
    prompt = f"""
You are a professional business analyst preparing notes for a client consultation meeting.

Based on the following rough project information provided by the client, generate structured meeting preparation notes in Markdown format.

Client's rough input:
{user_input}

Return a well-structured Markdown document with the following sections:
- **Project Overview** — a clear summary of what the client wants
- **Key Requirements** — bullet points of the main requirements
- **Questions to Ask** — smart clarifying questions to ask in the meeting
- **Suggested Approach** — a brief recommended approach or solution direction

Keep it concise, professional, and actionable.
"""
   
    return  _generate(prompt)


def generate_technical_interview_context(user_input: str) -> str:
    prompt = f"""
You are a senior technical recruiter preparing for a technical interview.

Based on the following rough information about the position and requirements, generate a structured technical interview preparation guide in Markdown format.

Recruiter's rough input:
{user_input}

Return a well-structured Markdown document with the following sections:
- **Technical Questions** — 5 to 7 relevant technical interview questions suited for this role with one line answers
- **Evaluation Criteria** — what to look for in a strong candidate

Keep it sharp, technical, and relevant.
"""
    return  _generate(prompt)


def generate_sales_demo_context(user_input: str) -> str:
    prompt = f"""
You are an experienced sales strategist preparing for a product demo or partnership discussion.

Based on the following rough information about the service or product being presented, generate a structured sales demo preparation guide in Markdown format.

Sales rep's rough input:
{user_input}

Return a well-structured Markdown document with the following sections:
- **Service/Product Overview** — a compelling one-paragraph summary
- **Key Value Propositions** — bullet points of the strongest selling points
- **Target Pain Points** — problems this service solves for the prospect
- **Demo Talking Points** — key points to highlight during the demo
- **Anticipated Objections & Responses** — common objections and how to handle them
- **Desired Outcome** — what a successful meeting looks like

Keep it persuasive, confident, and client-focused.
"""
    return  _generate(prompt)


def generate_support_call_context(user_input: str) -> str:
    prompt = f"""
You are a technical support specialist preparing for a client support call.

Based on the following rough description of the problem, generate a structured support call preparation guide in Markdown format.

Client's rough problem description:
{user_input}

Return a well-structured Markdown document with the following sections:
- **Problem Summary** — a clear restatement of the issue
- **Likely Root Causes** — possible reasons this issue is occurring
- **Diagnostic Questions** — questions to ask the client to narrow down the cause
- **Suggested Solutions** — step-by-step fixes to try, ordered from most to least likely
- **Escalation Criteria** — conditions under which this should be escalated further

Keep it clear, methodical, and solution-oriented.
"""
    return  _generate(prompt)


# Router function — call this from main.py
def generate_meeting_context(purpose: str, user_input: str) -> str:
    purpose_map = {
        "Client Consultation": generate_client_consultation_context,
        "Technical Interview": generate_technical_interview_context,
        "Sales Demo / Partnership Discussion": generate_sales_demo_context,
        "Support Call": generate_support_call_context,
    }

    handler = purpose_map.get(purpose)
    if not handler:
        # For HR Interview and General Discussion, return user input as-is
        return user_input

    return handler(user_input)
