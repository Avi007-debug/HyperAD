from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

class ReportGenerator:
    def __init__(self, filename: str = "HyperAD_Report.pdf"):
        self.filename = filename
        self.styles = getSampleStyleSheet()
        self.elements = []
        
        # Add custom styles for badges and highlights
        self.styles.add(ParagraphStyle(name='MITREBadge', parent=self.styles['Normal'],
                                       textColor=colors.whitesmoke, backColor=colors.darkblue,
                                       spaceBefore=10, spaceAfter=10, borderPadding=5))
        self.styles.add(ParagraphStyle(name='RiskHigh', parent=self.styles['Normal'],
                                       textColor=colors.red, fontSize=12, spaceAfter=10))

    def _add_title_page(self):
        title_style = self.styles['Title']
        title_style.fontSize = 24
        self.elements.append(Paragraph("HyperAD Security Analysis Report", title_style))
        self.elements.append(Spacer(1, 50))
        self.elements.append(Paragraph("Automated Active Directory Risk Assessment", self.styles['Heading2']))
        self.elements.append(PageBreak())

    def _add_executive_summary(self, summary_text: str):
        self.elements.append(Paragraph("Executive Summary", self.styles['Heading1']))
        self.elements.append(Spacer(1, 12))
        self.elements.append(Paragraph(summary_text, self.styles['Normal']))
        self.elements.append(PageBreak())

    def _add_risk_charts_placeholder(self):
        self.elements.append(Paragraph("Risk Overview Charts", self.styles['Heading1']))
        self.elements.append(Spacer(1, 12))
        # Placeholder for graphical charts (e.g., using reportlab graphics or embedding matplotlib images)
        data = [['Risk Level', 'Count'], ['Critical', '5'], ['High', '12'], ['Medium', '24']]
        t = Table(data, style=[
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ])
        self.elements.append(t)
        self.elements.append(PageBreak())

    def _add_findings(self, findings: list):
        self.elements.append(Paragraph("Detailed Findings", self.styles['Heading1']))
        self.elements.append(Spacer(1, 12))

        for finding in findings:
            self.elements.append(Paragraph(finding['title'], self.styles['Heading2']))
            # MITRE Badge
            mitre_text = f"MITRE ATT&CK: {finding['tactic']} | {finding['technique']}"
            self.elements.append(Paragraph(mitre_text, self.styles['MITREBadge']))
            
            self.elements.append(Paragraph(f"Risk Score: {finding['risk_score']}", self.styles['RiskHigh']))
            self.elements.append(Paragraph(f"Description: {finding['description']}", self.styles['Normal']))
            
            # Bellman-Ford Path visualization placeholder
            self.elements.append(Spacer(1, 10))
            self.elements.append(Paragraph("Attack Path Visualization (Bellman-Ford Shortest Path):", self.styles['Heading3']))
            path_str = " \u2192 ".join(finding['attack_path'])
            self.elements.append(Paragraph(path_str, self.styles['Code']))
            
            self.elements.append(Spacer(1, 20))

    def generate(self, summary_text: str, findings: list):
        """Generate the final PDF report."""
        self._add_title_page()
        self._add_executive_summary(summary_text)
        self._add_risk_charts_placeholder()
        self._add_findings(findings)

        doc = SimpleDocTemplate(self.filename, pagesize=letter)
        doc.build(self.elements)
        print(f"Report generated successfully: {self.filename}")

if __name__ == "__main__":
    # Mock data execution
    generator = ReportGenerator()
    sample_summary = "The assessment identified multiple critical paths to Domain Admin privileges. Immediate remediation is required for DCSync vulnerabilities."
    sample_findings = [
        {
            "title": "DCSync Vulnerability on DC01",
            "tactic": "Credential Access (TA0006)",
            "technique": "OS Credential Dumping: DCSync (T1003.006)",
            "risk_score": "0.95",
            "description": "An account was identified with permissions to replicate directory changes, allowing credential extraction.",
            "attack_path": ["Compromised_User", "IT_Support_Group", "Domain_Admins", "DC01"]
        }
    ]
    generator.generate(sample_summary, sample_findings)
