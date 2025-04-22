# ------------------ Anomaly Detection with Enhanced Output ------------------
import streamlit as st
import google.generativeai as genai
import re
import json

def analyze_resume(resume_text):
    prompt = f'''
You are an expert resume reviewer for recruiters.

Evaluate the resume below against 13 predefined checks. For each check:
1. Determine if it passes (✅) or fails (❌)
2. Provide a brief explanation of the issue if it fails
3. Rate the severity of each failed check on a scale of 1-10 (1=minor, 10=critical)
4. Suggest a specific fix for each failed check
5. Explain why this issue matters to recruiters

Resume Text:
"""
{resume_text}
"""

For each of the 13 checks below, return a JSON object with these fields:
- check_name: The name of the check
- passed: true/false
- explanation: Brief explanation if failed (empty string if passed)
- severity: Number 1-10 if failed (0 if passed)
- category: One of: "Content", "Format", "Consistency", "Relevance", "Credibility"

Additionally, include a "resume_strengths" object with these fields:
- top_skills: Array of the top 5 skills the candidate is expert in based on their experience and qualifications
- wow_factor: Extraordinary achievements such as patents, published research papers, conference showcases, startup/entrepreneurship accomplishments, international/national level awards, keynote speaking engagements, or honors from top universities

Here are the 13 checks:
1. Grammar or spelling mistakes (e.g., typos, incorrect verb usage)
2. Filler or vague phrases (e.g., "hardworking," "motivated," "go-getter")
3. Repeated phrases (copy-pasted bullet points or phrases)
4. Missing contact information (check if email, mobile number is present)
5. Missing key sections (e.g., no experience, no education, no projects, no certifications)
6. Unexplained employment gaps (look for large gaps between jobs without explanation)
7. Frequent job switching (only flag jobs with tenure < 8 months)
8. Experience and skills mismatch (skills listed doesn't align with the job role)
9. Use of outdated technologies (e.g., php, adobe flash, older languages/tools not used today)
10. Lack of measurable achievements (Simply listing responsibilities without highlighting quantifiable, missing performance metrics like %s or KPIs)
11. Education and experience mismatch (e.g., studied biology/mechanical engineering, but working in software)
12. Irrelevant experience (e.g., work experience that don't relate to the field the candidate specializes in)
13. Role-skill mismatch (e.g., job is "Data Scientist" but no data tools in work experience)

**Important Notes**:
- For the "Lack of measurable achievements" check, mark it as passed if even 1 or 2 clear quantifiable metrics (such as numbers, percentages, KPIs, growth metrics) are present in a bullet point or its surrounding context. Do not fail this check just because part of a sentence doesn't include a number — what matters is whether some measurable outcome is included overall
- For the "Repeated phrases" check, only flag it as a fail if the exact same bullet point has been copy-pasted across different job roles or sections
- For the "Irrelevant experience" check, only flag any resume anomalies where the candidate lists work experience unrelated to their stated field of specialization, without demonstrating transferable skills or providing context for the career shift

Return the results as a JSON object with two properties:
1. "checks": An array of 13 objects for each check, following the format specified above
2. "resume_strengths": The object containing top_skills and wow_factor fields
'''

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        content = response.text
        
        # Extract the JSON part of the response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            results = json.loads(json_str)
            
            # Extract checks and resume strengths
            checks = results.get("checks", [])
            strengths = results.get("resume_strengths", {})
            
            # Handle case where API returned just an array of checks
            if isinstance(results, list):
                checks = results
                strengths = {}
                
            return {
                "results": checks, 
                "parsed": True,
                "strengths": strengths
            }
        else:
            # Fallback to parsing the whole response as JSON
            try:
                results = json.loads(content)
                
                # Extract checks and resume strengths
                checks = results.get("checks", [])
                strengths = results.get("resume_strengths", {})
                
                # Handle case where API returned just an array of checks
                if isinstance(results, list):
                    checks = results
                    strengths = {}
                    
                return {
                    "results": checks, 
                    "parsed": True,
                    "strengths": strengths
                }
            except:
                st.error("Failed to parse LLM response as JSON. Using text format instead.")
                # Return raw text if JSON parsing failed
                return {"raw_text": content, "parsed": False}
        
    except Exception as e:
        st.error(f"Error in LLM analysis: {e}")
        return {"raw_text": str(e), "parsed": False}
    

def calculate_overall_score(results):
    """Calculate overall resume score based on anomaly findings"""
    if not results:
        return 0
    
    # Calculate base score (100 - deductions)
    base_score = 100
    
    # Only consider issues with severity >= 4
    significant_issues = [check for check in results if not check['passed'] and check['severity'] >= 4]
    
    # Calculate severity-weighted deductions
    total_severity = sum(check['severity'] for check in significant_issues)
    
    # Adjust score based on severity
    score = base_score - (total_severity * 0.77)
    score = max(0, min(100, score))  # Ensure score stays between 0-100
    
    return round(score, 1)

def calculate_category_scores(category_results):
    """Calculate scores by category"""
    categories = {
        "Content": [],
        "Format": [],
        "Consistency": [],
        "Relevance": [],
        "Credibility": []
    }
    
    # Group checks by category, only considering significant issues (severity >= 4)
    for check in category_results:
        # Treat checks with severity < 4 as passed
        is_significant = not check['passed'] and check['severity'] >= 4
        check_result = check.copy()
        
        if not is_significant and not check['passed']:
            check_result['passed'] = True
            
        if check_result['category'] in categories:
            categories[check_result['category']].append(check_result)
    
    # Calculate score for each category
    category_scores = {}
    for category, checks in categories.items():
        if not checks:
            category_scores[category] = 100
            continue
            
        passed = sum(1 for check in checks if check['passed'])
        total = len(checks)
        
        # Calculate severity deduction
        severity_sum = sum(check['severity'] for check in checks if not check['passed'])
        severity_deduction = severity_sum * (10 / total) if total > 0 else 0
        
        # Base score based on pass rate plus severity deduction
        score = 100 * (passed / total) if total > 0 else 100
        score = max(0, score - severity_deduction)
        
        category_scores[category] = round(score, 1)
    
    return category_scores

def generate_recruiter_insights(results, strengths):
    """Generate key insights for recruiters based on analysis"""
    insights = []
    
    # Filter results to only include significant issues (severity >= 4)
    significant_results = [check for check in results if not check['passed'] and check['severity'] >= 4]
    
    # Check for deal-breakers (severity >= 8)
    deal_breakers = [check for check in significant_results if check['severity'] >= 8]
    if deal_breakers:
        insights.append({
            "type": "critical",
            "title": "Critical Issues Detected",
            "description": f"Found {len(deal_breakers)} critical issues that may significantly impact candidate viability.",
            "items": [f"{check['check_name']}: {check['explanation']}" for check in deal_breakers]
        })
    
    # Check for potential red flags (severity 4-7)
    red_flags = [check for check in significant_results if 4 <= check['severity'] < 8]
    if red_flags:
        insights.append({
            "type": "warning",
            "title": "Potential Red Flags",
            "description": f"Found {len(red_flags)} issues that warrant further discussion with the candidate.",
            "items": [f"{check['check_name']}: {check['explanation']}" for check in red_flags]
        })
    
    # Add Resume Strengths section
    top_skills = strengths.get("top_skills", [])
    wow_factor = strengths.get("wow_factor", "")
    
    if top_skills or wow_factor:
        strength_items = []
        
        if top_skills:
            if isinstance(top_skills, list):
                strength_items.append(f"Top skills: {', '.join(top_skills)}")
            else:
                strength_items.append(f"Top skills: {top_skills}")
                
        if wow_factor:
            if isinstance(wow_factor, list):
                # Join the list into a sentence
                joined_wow = ', '.join(wow_factor[:-1])
                if len(wow_factor) > 1:
                    joined_wow += f", and {wow_factor[-1]}"
                else:
                    joined_wow = wow_factor[0]
                strength_items.append(f"Standout feature: {joined_wow}")
            else:
                strength_items.append(f"Standout feature: {wow_factor}")
            
        insights.append({
            "type": "strength",
            "title": "Resume Strengths",
            "description": "Key strengths identified in this candidate's resume:",
            "items": strength_items
        })
    
    # Generate interview recommendations
    interview_questions = []
    for check in significant_results:
        if check['check_name'] == "Unexplained employment gaps":
            interview_questions.append(f"Ask about the gap between positions: \"{check['explanation']}\"")
        elif check['check_name'] == "Education and experience mismatch":
            interview_questions.append(f"Explore transition from education to current career path: \"{check['explanation']}\"")
        elif check['check_name'] == "Experience and skills mismatch":
            interview_questions.append(f"Verify skill proficiency: \"{check['explanation']}\"")
    
    if interview_questions:
        insights.append({
            "type": "interview",
            "title": "Suggested Interview Questions",
            "description": "Based on resume anomalies, consider asking:",
            "items": interview_questions
        })
    
    return insights