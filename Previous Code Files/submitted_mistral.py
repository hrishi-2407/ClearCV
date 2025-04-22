import streamlit as st
import PyPDF2
import docx
import traceback
from huggingface_hub import InferenceClient

# Load Hugging Face API token securely
def get_huggingface_token():
    try:
        return st.secrets["HUGGINGFACE_API_TOKEN"]
    except Exception as e:
        st.error(f"Error loading Hugging Face API token: {e}")
        st.warning("Please set the HUGGINGFACE_API_TOKEN in your Streamlit secrets.")
        return None

# Parse PDF
def parse_pdf(file) -> str:
    try:
        reader = PyPDF2.PdfReader(file)
        return ''.join([page.extract_text() or '' for page in reader.pages]).strip()
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

# Parse DOCX
def parse_docx(file) -> str:
    try:
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return ""

# File parser
def parse_document(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    
    file_extension = uploaded_file.name.lower().split('.')[-1]
    
    if file_extension == "pdf":
        return parse_pdf(uploaded_file)
    elif file_extension == "docx":
        return parse_docx(uploaded_file)
    else:
        st.error(f"Unsupported file type: {file_extension}. Please upload a PDF or DOCX file.")
        return ""

# Prompt builder (plain text output)
def build_analysis_prompt(resume_text: str) -> str:
    truncated_text = resume_text[:6000] if len(resume_text) > 6000 else resume_text
    
    prompt = f"""
You are an expert resume reviewer.

Your task is to evaluate the resume below against 12 predefined checks (listed below). Go **one by one** and decide for each:

- Use ✅ if there is NO issue, followed by a **short OK confirmation**.
- Use ❌ if there iS an issue, and bold the text, followed by a **very short explanation of the problem**.
- Each result must be on **one line**.
- Your output MUST be **exactly 12 bullet points** — no extras, no explanations, no paragraphs.

Use this exact style:

Output only bullet points. For each rule, use:
- ✅ if it passes
- ❌ with a reason if it fails
 
Repeat this for all 12 checks.

Here are the 12 checks:
1. Grammar or spelling mistakes (e.g., typos, punctuation issues, incorrect verb usage)
2. Filler words or repeated phrases (e.g., “hardworking,” “motivated")
3. Missing contact information (check if email, mobile number is present)
4. Missing key sections (e.g., no experience, no education)
5. Unexplained employment gaps (look for large gaps between jobs without explanation)
6. Frequent job switching (many jobs with tenure < 8 months)
7. Experience and skills mismatch (skills listed not shown in job history)
8. Use of outdated technologies (e.g., php, adobe flash, older languages/tools not used today)
9. Lack of measurable achievements (missing performance metrics like %s or KPIs)
10. Education and experience mismatch (e.g., studied biology but working in software without explanation)
11. Irrelevant experience (e.g., job roles that dont relate to the field)
12. Role-skill mismatch (e.g., job is “Data Scientist” but no data related tools in skills)


Resume:
\"\"\"
{truncated_text}
\"\"\"
"""
    return prompt

# Analyze resume and return plain text
def analyze_resume(resume_text: str) -> str:
    token = get_huggingface_token()
    if not token or not resume_text:
        return "Error: Missing API token or empty resume text."
    
    try:
        # Initialize inference client with DeepSeek V3 model
        client = InferenceClient(model="mistralai/Mistral-7B-Instruct-v0.2", token=token)
        
        # Prepare prompt using your custom prompt builder
        prompt = build_analysis_prompt(resume_text)

        response = client.text_generation(
            prompt=prompt,
            max_new_tokens=600,
            temperature=0.2,
            top_p=0.9,
            repetition_penalty=1.1,
            stop=["```"]
        )
        return response.strip()

    except Exception as e:
        st.error("Exception during resume analysis:")
        st.code(traceback.format_exc())
        return "Error: Analysis failed."

# Main App
def main():
    st.set_page_config(page_title="Resume Anomaly Analyzer", layout="centered")
    st.title("📄 Resume Anomaly Analyzer")
    st.markdown("Upload your resume to get a plain English analysis using Mistral LLM (no JSON involved).")

    uploaded_file = st.file_uploader("📤 Upload Resume (PDF or DOCX)", type=["pdf", "docx"])
    
    if uploaded_file:
        resume_text = parse_document(uploaded_file)
        st.subheader("📑 Extracted Resume Text:")
        st.text_area("Resume Content", resume_text, height=300)

        if st.button("🔍 Analyze Resume"):
            with st.spinner("Analyzing with Mistral LLM..."):
                analysis = analyze_resume(resume_text)
                st.subheader("🧠 AI Analysis (Plain Text)")
                st.markdown(analysis)

if __name__ == "__main__":
    main()
