import os
from reportlab.lib import colors, pagesizes
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_pdf(report_data, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    doc = SimpleDocTemplate(
        save_path,
        pagesize=pagesizes.A4,
        rightMargin=32,
        leftMargin=32,
        topMargin=28,
        bottomMargin=28,
    )
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0B4EA2"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#506A88"),
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0B4EA2"),
        spaceBefore=8,
        spaceAfter=8,
    )
    label_style = ParagraphStyle(
        "FieldLabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#2F4E6F"),
    )
    value_style = ParagraphStyle(
        "FieldValue",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#111111"),
    )

    elements.append(Paragraph("SMARTHEALTH AI", title_style))
    elements.append(Paragraph("AI-Based Clinical Diagnosis Report", subtitle_style))
    elements.append(Spacer(1, 0.18 * inch))

    elements.append(Paragraph("Patient Information", section_style))

    patient = report_data["patient"]
    patient_table = Table(
        [
            [Paragraph("<b>Field</b>", label_style), Paragraph("<b>Details</b>", label_style)],
            [Paragraph("Name", label_style), Paragraph(str(patient.get("name", "N/A")), value_style)],
            [Paragraph("Age", label_style), Paragraph(str(patient.get("age", "N/A")), value_style)],
            [Paragraph("Gender", label_style), Paragraph(str(patient.get("gender", "N/A")), value_style)],
            [Paragraph("Blood Group", label_style), Paragraph(str(patient.get("blood_group", "N/A")), value_style)],
            [Paragraph("BMI", label_style), Paragraph(str(patient.get("bmi", "N/A")), value_style)],
            [Paragraph("Location", label_style), Paragraph(str(patient.get("location", "N/A")), value_style)],
            [Paragraph("Date", label_style), Paragraph(str(patient.get("date", "N/A")), value_style)],
        ],
        colWidths=[2.1 * inch, 4.8 * inch],
    )
    patient_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#C8D7E8")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF3FF")),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F8FBFF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(patient_table)
    elements.append(Spacer(1, 0.22 * inch))

    elements.append(Paragraph("Vital Signs", section_style))

    vitals = report_data.get("vitals", {})
    vital_table = Table(
        [
            [Paragraph("<b>Vital</b>", label_style), Paragraph("<b>Reading</b>", label_style)],
            [Paragraph("Temperature", label_style), Paragraph(str(vitals.get("temperature", "N/A")), value_style)],
            [Paragraph("Heart Rate", label_style), Paragraph(str(vitals.get("heart_rate", "N/A")), value_style)],
            [
                Paragraph("Blood Pressure", label_style),
                Paragraph(f"{vitals.get('bp_systolic', 'N/A')}/{vitals.get('bp_diastolic', 'N/A')}", value_style),
            ],
            [Paragraph("Respiratory Rate", label_style), Paragraph(str(vitals.get("respiratory_rate", "N/A")), value_style)],
            [Paragraph("SpO2", label_style), Paragraph(str(vitals.get("spo2", "N/A")), value_style)],
        ],
        colWidths=[2.1 * inch, 4.8 * inch],
    )
    vital_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#C8D7E8")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF3FF")),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F8FBFF")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(vital_table)
    elements.append(Spacer(1, 0.22 * inch))

    elements.append(Paragraph("Clinical Findings", section_style))
    findings_table = Table(
        [[
            Paragraph(
                "<b>Chief Complaints:</b><br/>" + (", ".join(report_data.get("symptoms", [])) or "Not Provided"),
                value_style,
            )
        ], [
            Paragraph(
                "<b>Medical History:</b><br/>" + str(report_data.get("medical_history", "Not Provided")),
                value_style,
            )
        ]],
        colWidths=[6.9 * inch],
    )
    findings_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C8D7E8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7E4F2")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FCFEFF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(findings_table)
    elements.append(Spacer(1, 0.22 * inch))

    elements.append(Paragraph("Diagnosis Summary", section_style))
    prediction = report_data["prediction"]
    summary_table = Table(
        [
            [Paragraph("<b>Predicted Condition</b>", label_style), Paragraph(str(prediction.get("disease", "N/A")), value_style)],
            [Paragraph("<b>Risk Probability</b>", label_style), Paragraph(f"{prediction.get('confidence', 'N/A')}%", value_style)],
            [Paragraph("<b>Risk Level</b>", label_style), Paragraph(str(prediction.get("risk_level", "N/A")), value_style)],
        ],
        colWidths=[2.1 * inch, 4.8 * inch],
    )
    summary_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#8FB1D9")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7E4F2")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F7FF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.22 * inch))

    elements.append(Paragraph("AI Clinical Interpretation", section_style))
    if not report_data.get("explanation"):
        elements.append(Paragraph("No interpretation notes available.", value_style))
    for line in report_data.get("explanation", []):
        elements.append(Paragraph("- " + str(line), value_style))
        elements.append(Spacer(1, 0.06 * inch))

    elements.append(Spacer(1, 0.28 * inch))
    elements.append(
        Paragraph(
            "Disclaimer: This report is AI-generated and should not replace professional medical consultation.",
            ParagraphStyle(
                "Disclaimer",
                parent=styles["Italic"],
                fontSize=8.5,
                textColor=colors.HexColor("#5F738A"),
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(elements)
