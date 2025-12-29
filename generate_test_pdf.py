from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def generate_test_pdf(filename="test_statement.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Header with Account Number
    elements.append(Paragraph("Bank Statement", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Account Number: 123456789", styles['Normal']))
    elements.append(Spacer(1, 24))

    # Transaction Table
    data = [
        ["Date", "Description", "Amount"],
        ["01/01/2023", "Opening Balance", "1000.00"],
        ["01/05/2023", "Grocery Store", "-50.25"],
        ["01/10/2023", "Paycheck", "2500.00"],
        ["01/15/2023", "Electric Bill", "-120.00"],
        ["01/20/2023", "Restaurant", "-85.50"]
    ]

    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(t)
    doc.build(elements)
    print(f"Generated {filename}")

if __name__ == "__main__":
    generate_test_pdf()
