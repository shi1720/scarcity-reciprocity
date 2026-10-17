"""Typeset the manuscript and the workshop's required abstract/bio submission."""
from pathlib import Path
import re, json, sys
from html import escape
from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,Image,Table,
    TableStyle,KeepTogether,PageBreak,HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY,TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/'manuscript.txt').read_text()
BIO=('Shivam Gupta is an independent researcher and applied AI engineer working across India '
     'and the United Arab Emirates. He is the founder of Siloed, an AI product consultancy. '
     'His work combines production AI systems, software reliability and the governance of '
     'digital infrastructure. He previously undertook undergraduate research at IIIT Delhi '
     'and summer research at Bharat Electronics Limited. His current research examines '
     'how infrastructure contracts and operational constraints shape the practical agency '
     'of governments and service providers.')
ABSTRACT=TEXT.split('ABSTRACT\n',1)[1].split('\n\n1.',1)[0]
TITLE=TEXT.splitlines()[0];SUBTITLE=TEXT.splitlines()[1]
fontpath=Path('/System/Library/Fonts/Supplemental')
if (fontpath/'Times New Roman.ttf').exists():
    for name,file in [('Paper','Times New Roman.ttf'),('Paper-Bold','Times New Roman Bold.ttf'),
                      ('Paper-Italic','Times New Roman Italic.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(fontpath/file)))
    pdfmetrics.registerFontFamily('Paper',normal='Paper',bold='Paper-Bold',italic='Paper-Italic')
else:
    for name,real in [('Paper','Times-Roman'),('Paper-Bold','Times-Bold'),('Paper-Italic','Times-Italic')]:
        pdfmetrics.registerFont(pdfmetrics.Font(name,real,'WinAnsiEncoding'))
    pdfmetrics.registerFontFamily('Paper',normal='Paper',bold='Paper-Bold',italic='Paper-Italic')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyPaper',fontName='Paper',fontSize=11,leading=14.6,
                         alignment=TA_JUSTIFY,spaceAfter=8))
styles.add(ParagraphStyle(name='TitlePaper',fontName='Paper-Bold',fontSize=23,leading=26,spaceAfter=6))
styles.add(ParagraphStyle(name='SubtitlePaper',fontName='Paper',fontSize=15,leading=18,spaceAfter=13))
styles.add(ParagraphStyle(name='SectionPaper',fontName='Paper-Bold',fontSize=13,leading=16,
                         spaceBefore=13,spaceAfter=7,keepWithNext=True))
styles.add(ParagraphStyle(name='MetaPaper',fontName='Paper',fontSize=10,leading=13,spaceAfter=4))
styles.add(ParagraphStyle(name='AbstractPaper',fontName='Paper',fontSize=10.2,leading=13.3,
                         alignment=TA_JUSTIFY,spaceAfter=10))
styles.add(ParagraphStyle(name='CaptionPaper',fontName='Paper',fontSize=9,leading=11.3,spaceAfter=12))
styles.add(ParagraphStyle(name='RefPaper',fontName='Paper',fontSize=9,leading=11.5,spaceAfter=7,
                         splitLongWords=True))
styles.add(ParagraphStyle(name='CellPaper',fontName='Paper',fontSize=9,leading=11))
styles.add(ParagraphStyle(name='CellHead',fontName='Paper-Bold',fontSize=9,leading=11,textColor=colors.white))
BLUE=colors.HexColor('#193f54');WIDTH=487.28

def para(s,style='BodyPaper'):
    s=escape(s)
    s=re.sub(r'(https://[^\s]+)',r'<link href="\1" color="#245a75">\1</link>',s)
    return Paragraph(s,styles[style])

def footer(canvas,doc):
    canvas.saveState();w,h=doc.pagesize
    canvas.setStrokeColor(colors.HexColor('#c6cfd4'));canvas.setLineWidth(.4)
    canvas.line(54,42,w-54,42)
    canvas.setFont('Paper',8.5);canvas.setFillColor(colors.HexColor('#4e5d66'))
    canvas.drawString(54,30,'Gupta | Who Gets the Recovery Hour?')
    canvas.drawRightString(w-54,30,str(doc.page))
    if doc.page>1:
        canvas.setFont('Paper-Italic',8)
        canvas.drawRightString(w-54,h-30,'Data centre flexibility and cross-border governance')
    canvas.restoreState()

def imageflow(name,width=WIDTH):
    from PIL import Image as PILImage
    p=ROOT/'figures'/name
    with PILImage.open(p) as im:w,h=im.size
    return Image(str(p),width=width,height=width*h/w)

def eq(i):
    equations={1:r'$h_t=S^I_t-H^I_t+\eta\min\{K_t,\ S^E_t-H^E_t\}. \qquad (1)$',
               2:r'$p\left[(1-f)q+\sum_j y_{j,t}\right]\leq h_t,\quad\sum_j y_{j,t}\leq Bfq,\quad\sum_{t=r_j}^{d_j-1}y_{j,t}=6fq.\quad (2)$'}
    fig=plt.figure(figsize=(9, .48));fig.text(.5,.45,equations[i],ha='center',va='center',fontsize=12)
    p=ROOT/'figures'/f'equation_{i}.png';fig.savefig(p,dpi=240,bbox_inches='tight',pad_inches=.12);plt.close(fig)
    return imageflow(p.name)

def table(rows,widths):
    formatted=[[para(x,'CellHead' if i==0 else 'CellPaper') for x in row] for i,row in enumerate(rows)]
    t=Table(formatted,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),BLUE),('VALIGN',(0,0),(-1,-1),'TOP'),
       ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
       ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
       ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f0f4f6'),colors.white]),
       ('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#b8c5cc'))]))
    return t

def build():
    story=[para(TITLE,'TitlePaper'),para(SUBTITLE,'SubtitlePaper'),
           para('Shivam Gupta','MetaPaper'),
           para('Independent Researcher | India and United Arab Emirates','MetaPaper'),
           para('shivam1720406@gmail.com | 17 October 2026','MetaPaper'),Spacer(1,9),
           para('Abstract','SectionPaper'),para(ABSTRACT,'AbstractPaper')]
    body=TEXT.split('\n\n1. ',1)[1];body='1. '+body
    body=re.sub(r'(?m)^(\d\. [^\n]+|DATA AND CODE|REFERENCES)\n(?!\n)',r'\1\n\n',body)
    refs=False
    captions={
     1:'Figure 1. The proposed governance interface. Investment approval, power dispatch and tenant completion obligations must be assessed together. The diagram represents the analytical framework, not a description of an existing regional dispatch authority.',
     2:'Figure 2. Joint-shock scenario in the constructed system. Top: protection choices change available headroom without changing physical supply. Bottom: one completion-feasible LP schedule at q = 5.24359 MW. The shaded interval [12,24) binds admission. Lines show hourly values; all electrical inputs are illustrative.',
     3:'Figure 3. Conditional admission results. Left: main case, PUE 1.3, 80% flexible, six-hour additional slack; the daily-energy and importer-only quantities relax different commitments. Right: sensitivity at six-hour, 6 MW exporter shocks and PUE 1.4; only deadline slack and flexible share vary. These are constructed results, not national capacity estimates.'}
    for block in body.split('\n\n'):
        block=block.strip()
        if not block:continue
        if block.startswith('[FIGURE'):
            n=int(re.search(r'\d+',block).group());name={1:'01_governance.png',2:'02_recovery.png',3:'03_capacity.png'}[n]
            story.append(KeepTogether([imageflow(name),Spacer(1,6),para(captions[n],'CaptionPaper')]))
        elif block.startswith('[EQUATION'):
            n=int(re.search(r'\d+',block).group());story.extend([eq(n),Spacer(1,8)])
        elif block=='[TABLE 1]':
            rows=[['Document / status','Control point','Additional recovery question'],
              ['Singapore roadmap [8]\nPlanning factsheet','Capacity and resource performance','Which work can be dispatched?'],
              ['EMA flexibility [9]\nReform announcement','Activation and availability','When must deferred work finish?'],
              ['Malaysia guideline [10]\nDESAC eligibility','Design resource metrics','Who controls tenant workloads?'],
              ['MIDA task force [11]\nCoordination announcement','Investment applications','Which joint test is applied?'],
              ['Australia-Singapore [12]\nNon-binding framework','Trade and governance','Whose service has priority?']]
            story.append(KeepTogether([table(rows,[154,149,184.28]),Spacer(1,5),
              para('Table 1. Five documents, different institutional objects. Questions identify additional inputs; they do not demonstrate an absence of rights in other instruments. Locators and coding boundaries are in the public evidence ledger.','CaptionPaper')]))
        elif block=='[TABLE 2]':
            m=json.loads((ROOT/'results/main.json').read_text())
            rows=[['Assessment','Average IT MW','Commitment retained / relaxed'],
              ['Inflexible bilateral','2.154','Both service floors; fixed load'],
              ['Recovery bilateral','5.244','Both floors; all job windows'],
              ['Daily energy upper bound','7.045','Total work; timing relaxed'],
              ['Recovery importer only','7.436','Job windows; exporter floor omitted']]
            story.append(KeepTogether([table(rows,[170,82,235.28]),Spacer(1,5),
              para('Table 2. Main constructed-system results. The last two rows are relaxations of the bilateral recovery commitment, not equivalent service promises. IT MW excludes facility overhead; PUE = 1.3.','CaptionPaper')]))
        elif block=='REFERENCES':
            refs=True;story.append(para('References','SectionPaper'))
        elif refs:
            for line in block.splitlines():story.append(para(line,'RefPaper'))
        elif re.match(r'^\d\. ',block) or block=='DATA AND CODE':
            if block=='DATA AND CODE':story.append(PageBreak())
            story.append(para(block.title() if block=='DATA AND CODE' else block,'SectionPaper'))
        else:story.append(para(block))
    doc=SimpleDocTemplate(str(ROOT/'Who_Gets_the_Recovery_Hour_Shivam_Gupta.pdf'),
      pagesize=(595.28,841.89),rightMargin=54,leftMargin=54,topMargin=48,bottomMargin=55,
      title=TITLE+' '+SUBTITLE,author='Shivam Gupta',subject='Critical digital infrastructure governance; CAG workshop paper')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    story=[para('CAG Digital Infrastructure Workshop','MetaPaper'),Spacer(1,12),
      para(TITLE,'TitlePaper'),para(SUBTITLE,'SubtitlePaper'),
      para('Shivam Gupta','MetaPaper'),para('Independent Researcher | India and United Arab Emirates','MetaPaper'),
      para('Correspondence: shivam1720406@gmail.com','MetaPaper'),Spacer(1,8),
      para('Abstract','SectionPaper'),para(ABSTRACT,'BodyPaper'),
      para('Short biography','SectionPaper'),para(BIO,'BodyPaper')]
    doc=SimpleDocTemplate(str(ROOT/'CAG_Abstract_and_Bio_Recovery_Hour_Shivam_Gupta.pdf'),
      pagesize=(595.28,841.89),rightMargin=54,leftMargin=54,topMargin=48,bottomMargin=55,
      title='CAG Workshop: Abstract and Biography',author='Shivam Gupta')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    (ROOT/'abstract_and_bio.txt').write_text(TITLE+'\n'+SUBTITLE+'\n\nAbstract\n'+ABSTRACT+'\n\nShort biography\n'+BIO+'\n')
    print('Built manuscript and abstract/bio PDFs.')
if __name__=='__main__':build()
