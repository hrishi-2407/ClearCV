import streamlit as st
import PyPDF2
import docx
import google.generativeai as genai
from io import BytesIO
import os

print(f"GOOGLE_API_KEY from env: {os.getenv('GEMINI_API_KEY')}")

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

# ------------------ Anomaly Detection ------------------
def analyze_resume(resume_text):
    prompt = f'''
You are an expert resume reviewer.

Your task is to evaluate the resume below against 15 predefined checks (listed below). Go **one by one** through each check and decide:

- Use "✅ [check name]" if there is NO issue
- Use "❌ [check name]" if there IS an issue, followed by a brief explanation of the problem

Your output format should be exactly 15 bullet points, with each on a new line.

Resume Text:
"""
{resume_text}
"""

Here are the 15 checks to evaluate:
1. Grammar or spelling mistakes (e.g., typos, punctuation issues, incorrect verb usage)
2. Filler or vague phrases (e.g., "hardworking," "motivated," "go-getter")
3. Repeated phrases (copy-pasted bullet points or phrases)
4. Missing contact information (check if email, mobile number is present)
5. Missing key sections (e.g., no experience, no education, no projects, no certifications)
6. Unexplained employment gaps (look for large gaps between jobs without explanation)
7. Frequent job switching (many jobs with tenure < 8 months)
8. Experience and skills mismatch (skills listed doesn't align with the job role)
9. Use of outdated technologies (e.g., php, adobe flash, older languages/tools not used today)
10. Lack of measurable achievements (Simply listing responsibilities without highlighting quantifiable, missing performance metrics like %s or KPIs)
11. Education and experience mismatch (e.g., studied biology but working in software without explanation)
12. Irrelevant experience (e.g., job roles that don't relate to the field)
13. Role-skill mismatch (e.g., job is "Data Scientist" but no data tools in skills)
14. Inconsistent formatting (inconsistent bullet points, dates, etc.)
15. Formatting or layout issues (inconsistent fonts, margins, bullet usage)

DO NOT return your analysis in JSON format. Return ONLY the 15 bullet points with ✅ or ❌, followed by the check name and brief explanation if needed.
'''

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        content = response.text
        return content
    except Exception as e:
        st.error(f"Error in LLM analysis: {e}")
        return ""

# ------------------ Main Application ------------------
def main():
    st.set_page_config(page_title="Resume Anomaly Analyzer", layout="centered")
    st.title("📄 Resume Anomaly Analyzer")
    
    st.markdown("""
    This tool helps you identify potential issues in your resume by analyzing it against 15 common resume checks.
    Upload your resume to get started!
    """)

    uploaded_file = st.file_uploader("Upload Resume (PDF or DOC/DOCX):", type=["pdf", "docx"])

    if uploaded_file and st.button("Analyze Resume"):
        with st.spinner("Parsing document..."):
            resume_text = parse_document(uploaded_file)

        if resume_text:
            with st.spinner("Analyzing resume using Gemini API..."):
                analysis_results = analyze_resume(resume_text)

            if analysis_results:
                st.success("Analysis complete!")
                
                # Display summary of issues
                pass_count = analysis_results.count("✅")
                fail_count = analysis_results.count("❌")
                
                st.markdown(f"""
                ### Summary
                - **Passed checks**: {pass_count}/15
                - **Issues found**: {fail_count}/15
                """)
                
                # Display detailed results
                st.markdown("### Detailed Analysis")
                
                # Process each line to add proper formatting
                lines = analysis_results.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line:  # Skip empty lines
                        if line.startswith("✅"):
                            st.markdown(f"<div style='color:green'>{line}</div>", unsafe_allow_html=True)
                        elif line.startswith("❌"):
                            st.markdown(f"<div style='color:red'>{line}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(line)
                
                # Offer recommendations
                if fail_count > 0:
                    st.markdown("### Recommendations")
                    st.markdown("""
                    - Consider addressing the issues marked with ❌ to improve your resume
                    - Focus first on fixing critical issues like missing contact information or key sections
                    - Use specific, measurable achievements rather than vague statements
                    """)

if __name__ == "__main__":
    main()