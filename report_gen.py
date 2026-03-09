import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from database import save_report

BLUE   = colors.HexColor('#1a73e8')
GREEN  = colors.HexColor('#34a853')
RED    = colors.HexColor('#ea4335')
YELLOW = colors.HexColor('#fbbc04')
DARK   = colors.HexColor('#202124')
LIGHT  = colors.HexColor('#f8f9fa')
MID    = colors.HexColor('#e8eaed')

def generate_pdf(gsc_data, ga4_data, accountability=None, title=None):
    os.makedirs('data/reports', exist_ok=True)
    now = datetime.now()
    period = now.strftime('%B_%Y')
    filename = f"SEO_Report_{period}_{now.strftime('%H%M%S')}.pdf"
    filepath = f"data/reports/{filename}"

    if not title:
        title = f"SEO Report — {now.strftime('%B %Y')}"

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    story  = []

    # Styles
    h1 = ParagraphStyle('H1', parent=styles['Normal'],
        fontSize=22, textColor=DARK, fontName='Helvetica-Bold',
        spaceAfter=4)
    h2 = ParagraphStyle('H2', parent=styles['Normal'],
        fontSize=14, textColor=BLUE, fontName='Helvetica-Bold',
        spaceAfter=8, spaceBefore=16)
    body = ParagraphStyle('Body', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#5f6368'),
        spaceAfter=6, leading=14)
    small = ParagraphStyle('Small', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#9aa0a6'))
    label_c = ParagraphStyle('LabelC', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#5f6368'),
        alignment=TA_CENTER)
    value_c = ParagraphStyle('ValueC', parent=styles['Normal'],
        fontSize=20, textColor=DARK, fontName='Helvetica-Bold',
        alignment=TA_CENTER)

    # ─── HEADER ─────────────────────────────────────────────
    story.append(Paragraph(title, h1))
    site = gsc_data.get('site', os.getenv('GSC_PROPERTY_URL',''))
    days = gsc_data.get('period',{}).get('days', 28)
    p    = gsc_data.get('period',{})
    story.append(Paragraph(
        f"{site} &nbsp;|&nbsp; {p.get('start','')} to {p.get('end','')} ({days} days) &nbsp;|&nbsp; Generated {now.strftime('%d %b %Y %H:%M')}",
        small))
    story.append(HRFlowable(width='100%', thickness=2, color=BLUE, spaceAfter=16))

    # ─── KPI CARDS ─────────────────────────────────────────
    story.append(Paragraph('Key Performance Indicators', h2))
    s  = gsc_data.get('summary', {})
    ps = gsc_data.get('prev_summary', {})
    gs = ga4_data.get('summary', {})
    gp = ga4_data.get('prev_summary', {})

    def pct_change(cur, prev):
        if not prev: return ''
        chg = (cur - prev) / prev * 100
        arrow = '▲' if chg >= 0 else '▼'
        color = 'green' if chg >= 0 else 'red'
        return f'<font color="{color}">{arrow} {abs(chg):.1f}%</font>'

    kpi_data = [
        ['Metric', 'Current', 'Previous', 'Change'],
        ['Total Clicks (GSC)',
         str(s.get('total_clicks',0)),
         str(ps.get('total_clicks',0)),
         pct_change(s.get('total_clicks',0), ps.get('total_clicks',0))],
        ['Total Impressions',
         f"{s.get('total_impressions',0):,}",
         f"{ps.get('total_impressions',0):,}",
         pct_change(s.get('total_impressions',0), ps.get('total_impressions',0))],
        ['Average CTR',
         f"{s.get('avg_ctr',0):.2f}%", '—', '—'],
        ['Average Position',
         str(s.get('avg_position',0)),
         str(ps.get('avg_position',0)), '—'],
        ['Total Keywords',
         str(s.get('total_keywords',0)),
         str(ps.get('total_keywords',0)),
         pct_change(s.get('total_keywords',0), ps.get('total_keywords',0))],
        ['Keywords in Top 10',
         str(s.get('keywords_top10',0)), '—', '—'],
        ['Keywords in Top 50',
         str(s.get('keywords_top50',0)), '—', '—'],
        ['Organic Sessions (GA4)',
         str(gs.get('organic_sessions',0)),
         str(gp.get('organic_sessions',0)),
         pct_change(gs.get('organic_sessions',0), gp.get('organic_sessions',0))],
        ['Total GA4 Sessions',
         str(gs.get('total_sessions',0)),
         str(gp.get('total_sessions',0)),
         pct_change(gs.get('total_sessions',0), gp.get('total_sessions',0))],
    ]

    kpi_table = Table(kpi_data, colWidths=[7*cm, 3*cm, 3*cm, 3*cm])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLUE),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
        ('ALIGN',      (0,0), (0,-1), 'LEFT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT]),
        ('GRID', (0,0), (-1,-1), 0.5, MID),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5*cm))

    # ─── TOP KEYWORDS ──────────────────────────────────────
    story.append(Paragraph('Top Keywords by Clicks', h2))
    queries = sorted(gsc_data.get('queries',[]),
                     key=lambda x: x.get('clicks',0), reverse=True)[:20]
    if queries:
        kw_data = [['Keyword', 'Position', 'Clicks', 'Impressions', 'CTR']]
        for r in queries:
            keys = r.get('keys', [])
            kw   = keys[0] if keys else ''
            pos  = r.get('position', 0)
            kw_data.append([
                kw[:50],
                f"{pos:.1f}",
                str(r.get('clicks',0)),
                f"{r.get('impressions',0):,}",
                f"{r.get('ctr',0)*100:.2f}%"
            ])
        kw_table = Table(kw_data, colWidths=[8*cm, 2.5*cm, 2*cm, 2.5*cm, 1.5*cm])
        kw_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), DARK),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 8),
            ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT]),
            ('GRID', (0,0), (-1,-1), 0.3, MID),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(kw_table)

    story.append(Spacer(1, 0.5*cm))

    # ─── PAGE 2 OPPORTUNITIES ─────────────────────────────
    page2 = [r for r in gsc_data.get('queries',[])
              if 10 < r.get('position',0) <= 20]
    page2 = sorted(page2, key=lambda x: x.get('impressions',0), reverse=True)[:10]
    if page2:
        story.append(Paragraph('Page 2 Keywords — Quick Win Opportunities', h2))
        story.append(Paragraph(
            'These keywords rank on page 2. Small improvements can push them to page 1 for big traffic gains.',
            body))
        p2_data = [['Keyword', 'Position', 'Impressions', 'Clicks', 'CTR']]
        for r in page2:
            keys = r.get('keys', [])
            p2_data.append([
                (keys[0] if keys else '')[:50],
                f"{r.get('position',0):.1f}",
                f"{r.get('impressions',0):,}",
                str(r.get('clicks',0)),
                f"{r.get('ctr',0)*100:.2f}%"
            ])
        p2_table = Table(p2_data, colWidths=[8*cm, 2.5*cm, 2.5*cm, 2*cm, 1.5*cm])
        p2_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), YELLOW),
            ('TEXTCOLOR',  (0,0), (-1,0), DARK),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 8),
            ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT]),
            ('GRID', (0,0), (-1,-1), 0.3, MID),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(p2_table)
        story.append(Spacer(1, 0.5*cm))

    # ─── TRAFFIC CHANNELS ─────────────────────────────────
    story.append(Paragraph('Traffic by Channel (GA4)', h2))
    channels = ga4_data.get('channels', [])
    if channels:
        ch_data = [['Channel', 'Sessions', 'Users', 'Bounce Rate']]
        for ch in channels:
            ch_data.append([
                ch.get('sessionDefaultChannelGroup',''),
                ch.get('sessions','0'),
                ch.get('totalUsers','0'),
                f"{float(ch.get('bounceRate',0))*100:.1f}%"
            ])
        ch_table = Table(ch_data, colWidths=[6*cm, 3*cm, 3*cm, 4*cm])
        ch_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), GREEN),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT]),
            ('GRID', (0,0), (-1,-1), 0.3, MID),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(ch_table)

    # ─── ACCOUNTABILITY ───────────────────────────────────
    if accountability:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph('SEO Work Done This Month', h2))
        acc_data = [
            ['Backlinks Built', str(accountability.get('backlinks_built', 0))],
            ['Blog Posts Published', str(accountability.get('blog_posts', 0))],
            ['Domain Authority', str(accountability.get('da_score', '—'))],
            ['Technical Fixes', accountability.get('technical_fixes', '—')],
            ['Notes', accountability.get('notes', '—')],
        ]
        acc_table = Table(acc_data, colWidths=[6*cm, 10*cm])
        acc_table.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, LIGHT]),
            ('GRID', (0,0), (-1,-1), 0.3, MID),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(acc_table)

    # ─── FOOTER ───────────────────────────────────────────
    story.append(Spacer(1, cm))
    story.append(HRFlowable(width='100%', thickness=1, color=MID))
    story.append(Paragraph(
        f'SEO AI Dashboard — {site} — Generated {now.strftime("%d %B %Y")}',
        small))

    doc.build(story)
    print(f"PDF saved: {filepath}")

    # Save to database
    save_report(title, f"{days}d",
                filename, filepath,
                {'gsc_summary': s, 'ga4_summary': gs})

    return filepath, filename

if __name__ == '__main__':
    import json
    try:
        gsc = json.load(open('data/gsc/data.json'))
        ga4 = json.load(open('data/ga4/data.json'))
        path, fname = generate_pdf(gsc, ga4)
        print(f"Report: {path}")
    except FileNotFoundError:
        print("Run main.py first to fetch data")
