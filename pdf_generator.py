# ------------------ PDF Generation Functions ------------------
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
import io
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import base64

def sanitize_text(text):
    """Replace characters that can't be encoded in latin-1 with spaces"""
    if text is None:
        return ""
    
    result = ""
    for char in str(text):
        try:
            # Test if the character can be encoded with latin-1
            char.encode('latin-1')
            result += char
        except UnicodeEncodeError:
            # Replace problematic characters with a space
            result += ' '
    return result


def generate_pdf_report(results, overall_score, category_scores, recruiter_insights):
    """Generate a PDF report of the resume analysis"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Create custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=12,
    )
    
    heading_style = ParagraphStyle(
        'Heading1',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=6,
        spaceBefore=12,
    )
    
    subheading_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        spaceBefore=6,
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
    )
    
    # Title
    elements.append(Paragraph(sanitize_text("Resume Analysis Report"), title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Resume health score section
    elements.append(Paragraph(sanitize_text("Resume Health Score: " + str(overall_score) + "/100"), heading_style))
    
    # Generate a simple score visualization using matplotlib
    try:
        plt.figure(figsize=(5, 1))
        plt.axis('off')
        plt.xlim(0, 100)
        plt.ylim(0, 1)
        
        # Create color ranges
        plt.axvspan(0, 40, ymin=0.25, ymax=0.75, color='red', alpha=0.3)
        plt.axvspan(40, 70, ymin=0.25, ymax=0.75, color='yellow', alpha=0.3)
        plt.axvspan(70, 100, ymin=0.25, ymax=0.75, color='green', alpha=0.3)
        
        # Plot the score marker
        plt.axvline(x=overall_score, ymin=0, ymax=1, color='blue', linewidth=3)
        
        # Add labels
        plt.text(1, 0.5, '0', verticalalignment='center')
        plt.text(99, 0.5, '100', verticalalignment='center')
        plt.text(overall_score, 0.1, str(overall_score), verticalalignment='bottom', horizontalalignment='center')
        
        # Save to buffer
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        
        # Add the image to the PDF
        img = Image(img_buffer, width=4*inch, height=0.8*inch)
        elements.append(img)
        plt.close()
    except Exception as e:
        # Fallback if matplotlib fails
        elements.append(Paragraph(sanitize_text(f"Score: {overall_score}/100"), normal_style))
    
    elements.append(Spacer(1, 0.1*inch))
    
    # Category scores
    elements.append(Paragraph(sanitize_text("Category Performance"), heading_style))
    
    # Create a table for category scores
    category_data = [["Category", "Score"]]
    for category, score in category_scores.items():
        category_data.append([sanitize_text(category), sanitize_text(str(score) + "/100")])
    
    table = Table(category_data, colWidths=[2.5*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Key Insights for Recruiters
    elements.append(Paragraph(sanitize_text("Key Insights for Recruiters"), heading_style))
    
    if not recruiter_insights:
        elements.append(Paragraph(sanitize_text("No significant issues found in this resume!"), normal_style))
    else:
        for insight in recruiter_insights:
            insight_title = sanitize_text(insight['title'])
            elements.append(Paragraph(insight_title, subheading_style))
            
            description = sanitize_text(insight['description'])
            elements.append(Paragraph(description, normal_style))
            
            # Add items as bullet points
            for item in insight['items']:
                bullet_text = sanitize_text("• " + item)
                elements.append(Paragraph(bullet_text, normal_style))
            
            elements.append(Spacer(1, 0.1*inch))
    
    # Detailed Anomaly Analysis
    elements.append(Paragraph(sanitize_text("Detailed Anomaly Analysis"), heading_style))
    
    # Filter for significant failures (severity >= 4)
    failed_checks = [check for check in results if not check['passed'] and check['severity'] >= 4]
    
    if not failed_checks:
        elements.append(Paragraph(sanitize_text("No significant issues found! This resume passed all checks or only has minor issues."), normal_style))
    else:
        # Group by severity
        critical = [c for c in failed_checks if c['severity'] >= 8]
        moderate = [c for c in failed_checks if 4 <= c['severity'] < 8]
        
        if critical:
            elements.append(Paragraph(sanitize_text("Critical Issues:"), subheading_style))
            
            for check in critical:
                check_text = sanitize_text(f"❌ {check['check_name']} (Severity: {check['severity']}/10)")
                elements.append(Paragraph(check_text, normal_style))
                
                issue_text = sanitize_text(f"Issue: {check['explanation']}")
                elements.append(Paragraph(issue_text, normal_style))
            
            elements.append(Spacer(1, 0.1*inch))
        
        if moderate:
            elements.append(Paragraph(sanitize_text("Moderate Issues:"), subheading_style))
            
            for check in moderate:
                check_text = sanitize_text(f"❌ {check['check_name']} (Severity: {check['severity']}/10)")
                elements.append(Paragraph(check_text, normal_style))
                
                issue_text = sanitize_text(f"Issue: {check['explanation']}")
                elements.append(Paragraph(issue_text, normal_style))
    
    # Build the PDF document
    doc.build(elements)
    buffer.seek(0)
    return buffer

def get_pdf_download_link(pdf_bytes, filename="resume_analysis_report.pdf"):
    """Generate a download link for the PDF"""
    b64 = base64.b64encode(pdf_bytes.read()).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Download PDF</a>'
