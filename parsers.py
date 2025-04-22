# ------------------ Document Parsing ------------------
import PyPDF2
import docx
import streamlit as st

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