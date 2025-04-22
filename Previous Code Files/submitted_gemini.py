import streamlit as st
import PyPDF2
import docx
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import os
import re
import json

# Configure API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ------------------ Document Parsing ------------------
def parse_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def parse_docx(file):
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def parse_document(uploaded_file):
    file_type = uploaded_file.name.split('.')[-1].lower()
    if file_type == 'pdf':
        text = parse_pdf(uploaded_file)
        return text
    elif file_type in ['doc', 'docx']:
        text = parse_docx(uploaded_file)
        return text
    else:
        st.error("Unsupported file format. Please upload a PDF or DOCX file.")
        return None

# ------------------ Anomaly Detection with Enhanced Output ------------------
def analyze_resume(resume_text):
    prompt = f'''
You are an expert resume reviewer for recruiters.

Evaluate the resume below against 13 predefined checks. For each check:
1. Determine if it passes (✅) or fails (❌)
2. Provide a brief explanation of the issue if it fails
3. Rate the severity of each failed check on a scale of 1-10 (1=minor, 10=critical)
4. Suggest a specific fix for each failed check
5. Explain why this issue matters to recruiters

Additionally, analyze the resume to identify:
1. The top 5 skills the candidate is expert in based on their experience and qualifications
2. A "wow factor" - something impressive or unique about this candidate that makes them stand out

Resume Text:
"""
{resume_text}
"""

For each of the 13 checks below, return a JSON object with these fields:
- check_name: The name of the check
- passed: true/false
- explanation: Brief explanation if failed (empty string if passed)
- severity: Number 1-10 if failed (0 if passed)
- fix_suggestion: Specific recommendation to fix (empty string if passed)
- recruiter_impact: How this affects hiring decisions (empty string if passed)
- category: One of: "Content", "Format", "Consistency", "Relevance", "Credibility"

Additionally, include a "resume_strengths" object with these fields:
- top_skills: Array of the 5 most impressive skills exhibited in the resume
- wow_factor: A single standout feature that makes this candidate unique

Here are the 13 checks:
1. Grammar or spelling mistakes (e.g., typos, punctuation issues, incorrect verb usage)
2. Filler or vague phrases (e.g., "hardworking," "motivated," "go-getter")
3. Repeated phrases (copy-pasted bullet points or phrases)
4. Missing contact information (only check if email, mobile number is present)
5. Missing key sections (e.g., no experience, no education, no projects, no certifications)
6. Unexplained employment gaps (look for large gaps between jobs without explanation)
7. Frequent job switching (many jobs with tenure < 8 months)
8. Experience and skills mismatch (skills listed doesn't align with the job role)
9. Use of outdated technologies (e.g., php, adobe flash, older languages/tools not used today)
10. Lack of measurable achievements (only check the work experience section for at least 2-3 metrics)
11. Education and experience mismatch (e.g., studied biology but working in software without explanation)
12. Irrelevant experience (e.g., job roles that don't relate to the field)
13. Role-skill mismatch (e.g., job is "Data Scientist" but no data tools in skills)

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

# ------------------ Visualization Functions ------------------
def create_resume_health_gauge(overall_score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = overall_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Resume Health Score"},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': 'red'},
                {'range': [40, 70], 'color': 'yellow'},
                {'range': [70, 100], 'color': 'green'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': overall_score}
        }
    ))
    
    # Fixed scale to always be 0-100
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def create_category_radar_chart(category_scores):
    categories = list(category_scores.keys())
    values = list(category_scores.values())
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Resume Performance'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        height=350,
        margin=dict(l=80, r=80, t=20, b=20)
    )
    return fig

def create_severity_breakdown(results):
    # Group anomalies by severity level
    severity_levels = {
        "Critical (8-10)": 0,
        "Moderate (4-7)": 0, 
        "Minor (1-3)": 0,
        "No Issues": 0
    }
    
    for check in results:
        if not check['passed']:
            if check['severity'] >= 8:
                severity_levels["Critical (8-10)"] += 1
            elif check['severity'] >= 4:
                severity_levels["Moderate (4-7)"] += 1
            elif check['severity'] >= 1:
                severity_levels["Minor (1-3)"] += 1
        else:
            severity_levels["No Issues"] += 1
    
    # Create custom labels with counts
    custom_labels = []
    for level, count in severity_levels.items():
        if count > 0 or level == "No Issues":  # Always show "No Issues" even if zero
            custom_labels.append(f"{level} - {count}")
        else:
            custom_labels.append("")
    
    # Create horizontal bar chart
    fig = go.Figure()
    colors = ['red', 'orange', 'yellow', 'green']
    
    for i, (level, count) in enumerate(severity_levels.items()):
        fig.add_trace(go.Bar(
            y=[custom_labels[i] if count > 0 or level == "No Issues" else ""],
            x=[count],
            orientation='h',
            marker=dict(color=colors[i]),
            showlegend=False,
            name=level
        ))
    
    fig.update_layout(
        title="Anomaly Severity Breakdown",
        xaxis_title="Number of Checks",
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
        barmode='stack'
    )
    
    return fig

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
    score = base_score - (total_severity * 1.2)
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

# ------------------ Main Application ------------------
def main():
    st.set_page_config(page_title="Resume Anomaly Analyzer", layout="wide")
    
    # Custom CSS
    st.markdown("""
    <style>
    .main {
        background-color: #f5f7fa;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .insight-card {
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .critical {
        background-color: #ffecec;
        border-left: 5px solid #ff6666;
    }
    .warning {
        background-color: #fff8e6;
        border-left: 5px solid #ffc107;
    }
    .interview {
        background-color: #e6f3ff;
        border-left: 5px solid #2196F3;
    }
    .strength {
        background-color: #e6fff0;
        border-left: 5px solid #4CAF50;
    }
    .severity-high {
        color: #d32f2f;
        font-weight: bold;
    }
    .severity-medium {
        color: #f57c00;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # App Header
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://img.icons8.com/fluency/96/000000/resume.png", width=80)
    with col2:
        st.title("Resume Anomaly Analyzer")
        st.markdown("#### _Advanced insights for recruiters and HR professionals_")
    
    st.markdown("---")
    
    # File Upload Section
    uploaded_file = st.file_uploader("Upload Resume (PDF or DOC/DOCX)", type=["pdf", "docx"])
    
    if uploaded_file:
        if st.button("Analyze Resume"):
            with st.spinner("Analyzing resume... This may take a moment."):
                # Parse document
                resume_text = parse_document(uploaded_file)
                
                if resume_text:
                    # Call LLM for analysis
                    analysis = analyze_resume(resume_text)
                    
                    # Check if parsing was successful
                    if not analysis["parsed"]:
                        st.error("Failed to parse analysis results. Please try again.")
                        st.text(analysis["raw_text"])
                    else:
                        results = analysis["results"]
                        strengths = analysis.get("strengths", {})
                        
                        # Mark checks with severity < 4 as passed
                        for result in results:
                            if not result['passed'] and result['severity'] < 4:
                                result['passed'] = True
                                result['severity'] = 0
                                result['explanation'] = ""
                        
                        # Calculate overall score and category scores
                        overall_score = calculate_overall_score(results)
                        category_scores = calculate_category_scores(results)
                        
                        # Generate insights
                        recruiter_insights = generate_recruiter_insights(results, strengths)
                        
                        # Display dashboard layout
                        st.success("Analysis complete! Here's what we found:")
                        
                        # Top metrics
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.plotly_chart(create_resume_health_gauge(overall_score))
                            
                        with col2:
                            st.plotly_chart(create_category_radar_chart(category_scores))
                            
                        with col3:
                            st.plotly_chart(create_severity_breakdown(results))
                        
                        # Display insights for recruiters
                        st.markdown("### Key Insights for Recruiters")
                        
                        if not recruiter_insights:
                            st.success("No significant issues found in this resume!")
                        else:
                            for insight in recruiter_insights:
                                st.markdown(f"""
                                <div class="insight-card {insight['type']}">
                                    <h4>{insight['title']}</h4>
                                    <p>{insight['description']}</p>
                                    <ul>
                                        {"".join(f"<li>{item}</li>" for item in insight['items'])}
                                    </ul>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Detailed anomaly breakdown
                        st.markdown("### Detailed Anomaly Analysis")
                        
                        # Create tabs for different views with "Failed Checks Only" as default
                        tab2, tab1 = st.tabs(["Failed Checks Only", "All Checks"])
                        
                        with tab1:
                            for check in results:
                                if check['passed']:
                                    st.markdown(f"✅ **{check['check_name']}** - no anomaly.")
                                else:
                                    # Determine severity class
                                    severity_class = "severity-medium"
                                    if check['severity'] >= 8:
                                        severity_class = "severity-high"
                                    
                                    st.markdown(f"""
                                    ❌ **{check['check_name']}** <span class="{severity_class}">
                                    (Severity: {check['severity']}/10)</span> • **Issue:** {check['explanation']}
                                    """, unsafe_allow_html=True)
                        
                        with tab2:
                            failed_checks = [check for check in results if not check['passed'] and check['severity'] >= 4]
                            
                            if not failed_checks:
                                st.success("No significant issues found! This resume passed all checks or only has minor issues (severity < 4).")
                            else:
                                # Group by severity
                                critical = [c for c in failed_checks if c['severity'] >= 8]
                                moderate = [c for c in failed_checks if 4 <= c['severity'] < 8]
                                
                                if critical:
                                    st.markdown("#### Critical Issues")
                                    for check in critical:
                                        st.markdown(f"""
                                        ❌ **{check['check_name']}** <span class="severity-high">
                                        (Severity: {check['severity']}/10)</span> • **Issue:** {check['explanation']}
                                        """, unsafe_allow_html=True)
                                    
                                    # Add separator if both critical and moderate issues exist
                                    if moderate:
                                        st.markdown("---")
                                
                                if moderate:
                                    st.markdown("#### Moderate Issues")
                                    for check in moderate:
                                        st.markdown(f"""
                                        ❌ **{check['check_name']}** <span class="severity-medium">
                                        (Severity: {check['severity']}/10)</span> • **Issue:** {check['explanation']}
                                        """, unsafe_allow_html=True)
                        
                        # Export options
                        st.markdown("### Export Options")
                        st.download_button(
                            "Download Detailed Report (PDF)",
                            "Report functionality would be implemented here",
                            file_name="resume_analysis_report.pdf",
                            mime="application/pdf"
                        )
    
    else:
        # Show sample visualizations or instructions when no file is uploaded
        st.info("Upload a resume to begin analysis.")
        st.markdown("""
        ### How It Works
        
        1. **Upload** your candidate's resume (PDF or DOCX)
        2. **Analyze** to detect anomalies across 13 key dimensions
        3. **Review** visual insights and severity scores
        4. **Take action** based on recommended next steps
        
        This tool helps recruiters quickly identify potential issues in resumes, prioritize concerns, and make more informed decisions about candidates.
        """)

if __name__ == "__main__":
    main()