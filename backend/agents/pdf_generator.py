from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
from io import BytesIO
import re

def generate_itinerary_pdf(destination, arrival_date, departure_date, itinerary_text):
    """
    Generate a professionally formatted PDF from itinerary text
    
    Args:
        destination: City name
        arrival_date: Check-in date (YYYY-MM-DD)
        departure_date: Check-out date (YYYY-MM-DD)
        itinerary_text: The full itinerary text content
    
    Returns:
        bytes: PDF file data
    """
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=36,
    )
    
    # Container for PDF elements
    story = []
    
    # Define custom styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#2C3E50'),
        spaceAfter=30,
        spaceBefore=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=HexColor('#7F8C8D'),
        spaceAfter=24,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor('#34495E'),
        spaceAfter=12,
        spaceBefore=16,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=HexColor('#555555'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        spaceAfter=8,
        leading=14
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['BodyText'],
        fontSize=10,
        leftIndent=20,
        spaceAfter=6,
        leading=13
    )
    
    # Add title
    title = Paragraph(f"✈️ Trip to {destination}", title_style)
    story.append(title)
    
    # Add dates
    dates = Paragraph(f"{arrival_date} — {departure_date}", subtitle_style)
    story.append(dates)
    
    story.append(Spacer(1, 0.3*inch))
    
    # Parse and add itinerary content
    lines = itinerary_text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        if not line:
            story.append(Spacer(1, 0.1*inch))
            continue
        
        # Level 1 headers (## Header or # Header)
        if line.startswith('##'):
            clean_line = line.replace('##', '').strip()
            # Remove emojis for PDF (optional)
            clean_line = re.sub(r'[^\w\s\-:,.()?!]', '', clean_line)
            para = Paragraph(clean_line, heading_style)
            story.append(para)
            
        elif line.startswith('###'):
            clean_line = line.replace('###', '').strip()
            clean_line = re.sub(r'[^\w\s\-:,.()?!]', '', clean_line)
            para = Paragraph(clean_line, subheading_style)
            story.append(para)
            
        # Day headers (special formatting)
        elif line.lower().startswith('day '):
            para = Paragraph(line, heading_style)
            story.append(para)
            
        # Bold text (**text**)
        elif '**' in line:
            # Handle markdown bold
            clean_line = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', line)
            # Remove markdown links but keep text
            clean_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_line)
            para = Paragraph(clean_line, body_style)
            story.append(para)
            
        # Bullet points
        elif line.startswith('- ') or line.startswith('* ') or line.startswith('• '):
            clean_line = line[2:].strip()
            # Handle bold within bullets
            clean_line = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', clean_line)
            # Remove markdown links
            clean_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_line)
            para = Paragraph(f"• {clean_line}", bullet_style)
            story.append(para)
            
        # Regular paragraph
        else:
            # Handle markdown formatting
            clean_line = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', line)
            clean_line = re.sub(r'\*([^\*]+)\*', r'<i>\1</i>', clean_line)
            # Remove markdown links but keep text
            clean_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_line)
            
            para = Paragraph(clean_line, body_style)
            story.append(para)
    
    # Build PDF
    try:
        doc.build(story)
    except Exception as e:
        print(f"Error building PDF: {e}")
        raise
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data


def test_pdf_generation():
    """Test function to generate a sample PDF"""
    sample_itinerary = """
## Day 1 - Arrival & Gothic Quarter

**Morning:** Arrive at Barcelona airport, check into hotel
**Afternoon:** Explore the Gothic Quarter (Barri Gòtic)
- Visit Barcelona Cathedral
- Wander through narrow medieval streets
- Stop at Plaça Sant Jaume

**Evening:** Dinner at a tapas restaurant in El Born

**Tips:** The Gothic Quarter is best explored on foot. Wear comfortable shoes!

## Day 2 - Gaudí's Masterpieces

**Morning:** Visit Sagrada Família (book tickets in advance!)
**Afternoon:** Explore Park Güell
- Admire the colorful mosaics
- Enjoy panoramic city views

**Evening:** Stroll down Passeig de Gràcia, see Casa Batlló

## Restaurant Recommendations

- **Can Culleretes** - Traditional Catalan cuisine, oldest restaurant in Barcelona
- **El Xampanyet** - Authentic tapas bar in El Born
- **Cervecería Catalana** - Popular spot for tapas on Passeig de Gràcia

## Practical Tips

- Buy a T-10 metro card for unlimited rides
- Many museums are free on Sunday afternoons
- Book popular attractions online to skip queues
"""
    
    pdf_data = generate_itinerary_pdf(
        destination="Barcelona",
        arrival_date="2026-01-08",
        departure_date="2026-01-15",
        itinerary_text=sample_itinerary
    )
    
    # Save to file for testing
    with open('test_itinerary.pdf', 'wb') as f:
        f.write(pdf_data)
    
    print("✅ Test PDF generated: test_itinerary.pdf")

if __name__ == "__main__":
    test_pdf_generation()