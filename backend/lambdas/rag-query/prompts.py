"""
Strata-specific prompt templates for different query contexts
"""

STRATA_SYSTEM_PROMPT = """You are an expert assistant for Australian strata law and management. You have deep knowledge of:
- Strata Schemes Management Act 2015 (NSW)
- Body Corporate and Community Management Act 1997 (QLD)
- Owners Corporations Act 2006 (VIC)
- Strata by-laws and governance
- Meeting procedures and requirements
- Financial management and levies
- Maintenance and repairs
- Dispute resolution

Always:
1. Cite specific legislation, sections, or by-laws when applicable
2. Provide practical, actionable advice
3. Consider state-specific differences
4. Use Australian spelling and terminology
5. Be clear about what is legally required vs best practice
"""

PROMPT_TEMPLATES = {
    "by_laws": {
        "system": STRATA_SYSTEM_PROMPT,
        "user": """Question about by-laws: {question}

Based on the provided documents, explain the relevant by-laws and any legal requirements. Include:
- Specific by-law numbers and text
- How the by-law should be interpreted
- Any approval processes required
- Consequences of breaching the by-law

Relevant documents:
{context}"""
    },
    
    "meetings": {
        "system": STRATA_SYSTEM_PROMPT,
        "user": """Question about strata meetings: {question}

Based on the provided documents, explain the meeting requirements including:
- Notice periods and quorum requirements
- Voting procedures and majorities needed
- Who can attend and vote
- Required agenda items
- Legal compliance requirements

Relevant documents:
{context}"""
    },
    
    "finance": {
        "system": STRATA_SYSTEM_PROMPT,
        "user": """Financial question: {question}

Based on the provided documents, provide information about:
- Levy calculations and payment requirements
- Budget and financial reporting obligations
- Capital works fund requirements
- Insurance requirements
- Financial record keeping obligations

Relevant documents:
{context}"""
    },
    
    "maintenance": {
        "system": STRATA_SYSTEM_PROMPT,
        "user": """Maintenance and repairs question: {question}

Based on the provided documents, explain:
- Responsibility for the maintenance/repair (lot owner vs owners corporation)
- Common property vs lot property distinctions
- Approval requirements for works
- Emergency repair procedures
- Cost allocation

Relevant documents:
{context}"""
    },
    
    "disputes": {
        "system": STRATA_SYSTEM_PROMPT,
        "user": """Dispute resolution question: {question}

Based on the provided documents, provide guidance on:
- Internal dispute resolution procedures
- Mediation requirements
- Tribunal application processes
- Time limits and notice requirements
- Available remedies and orders

Relevant documents:
{context}"""
    },
    
    "governance": {
        "system": STRATA_SYSTEM_PROMPT,
        "user": """Governance question: {question}

Based on the provided documents, explain:
- Committee roles and responsibilities
- Decision-making powers and limitations
- Record keeping requirements
- Statutory obligations
- Best practices for strata governance

Relevant documents:
{context}"""
    },
    
    "general": {
        "system": STRATA_SYSTEM_PROMPT,
        "user": """Question: {question}

Based on the provided documents, provide a comprehensive answer with specific references to:
- Relevant legislation or by-laws
- Practical steps to take
- Any legal requirements or timeframes
- Best practices

Relevant documents:
{context}"""
    }
}

def get_prompt_template(category: str) -> dict:
    """Get the appropriate prompt template based on question category"""
    return PROMPT_TEMPLATES.get(category, PROMPT_TEMPLATES["general"])

def categorize_question(question: str) -> str:
    """Simple keyword-based categorization of questions"""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ["by-law", "bylaw", "rule", "pet", "parking", "noise"]):
        return "by_laws"
    elif any(word in question_lower for word in ["meeting", "agm", "egm", "vote", "quorum", "proxy"]):
        return "meetings"
    elif any(word in question_lower for word in ["levy", "levies", "budget", "financial", "insurance", "capital works"]):
        return "finance"
    elif any(word in question_lower for word in ["repair", "maintenance", "damage", "common property"]):
        return "maintenance"
    elif any(word in question_lower for word in ["dispute", "breach", "tribunal", "mediation"]):
        return "disputes"
    elif any(word in question_lower for word in ["committee", "strata manager", "secretary", "governance"]):
        return "governance"
    else:
        return "general"