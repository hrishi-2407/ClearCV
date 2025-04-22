import streamlit as st
import google.generativeai as genai
import os
from parsers import parse_document
from analysis import analyze_resume, calculate_overall_score, calculate_category_scores, generate_recruiter_insights
from visualization import create_resume_health_gauge, create_category_radar_chart, create_severity_breakdown
from pdf_generator import generate_pdf_report

# print(f"GOOGLE_API_KEY from env: {os.getenv('GEMINI_API_KEY')}")

# Configure API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# Modified part of the main() function that handles PDF generation
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
        resume_text = parse_document(uploaded_file)
        st.subheader("📑 Extracted Resume Text:")
        st.text_area("Resume Content", resume_text, height=300)   # --> SHows resume text on app
        if st.button("Analyze Resume"):
            with st.spinner("Analyzing resume... This may take a moment."):    
                
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

                        # Create PDF report for download
                        pdf_buffer = generate_pdf_report(
                            results=results, 
                            overall_score=overall_score, 
                            category_scores=category_scores, 
                            recruiter_insights=recruiter_insights,)
                        

                        # Display dashboard layout
                        st.success("Analysis complete! Here's what we found:")
                        
                        # Dashboard visualizations in containers for better layout and spacing
                        with st.container():
                            st.markdown("### 🔍 Resume Diagnostic Overview")
                            col1, col2, col3 = st.columns([0.9, 1, 0.9])  # Slightly more room for the severity bar
                        
                            with col1:
                                st.plotly_chart(create_resume_health_gauge(overall_score), use_container_width=True)
                            with col2:
                                st.plotly_chart(create_category_radar_chart(category_scores), use_container_width=True)
                            with col3:
                                st.plotly_chart(create_severity_breakdown(results), use_container_width=True)
                        
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
                        
                        # PDF Download button
                        base_name = os.path.splitext(uploaded_file.name)[0]
                        pdf_file_name = f"{base_name}_Analysis.pdf"
                        st.download_button(
                            label="Download Detailed Report (PDF)",
                            data=pdf_buffer,
                            file_name=pdf_file_name,
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