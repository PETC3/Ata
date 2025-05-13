# seu_projeto_flask/app/utils.py

import io
import os
import locale
from datetime import datetime
from flask import current_app

from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, ListFlowable, ListItem, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, inch

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import Ata

# Configuração do locale
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese')
        except locale.Error:
            if current_app:
                current_app.logger.warning("Locale 'pt_BR' ou 'Portuguese' não configurado.")
            else:
                print("Aviso: Locale 'pt_BR' ou 'Portuguese' não configurado.")

# Função para desenhar APENAS o número da página (para páginas subsequentes)
def draw_page_number_only(canvas, doc):
    canvas.saveState()
    page_num_text = f"{canvas.getPageNumber()}"
    canvas.setFont("Times-Roman", 10)
    x_position = doc.pagesize[0] - 2*cm
    y_position = doc.pagesize[1] - 2*cm - (0.3*cm) # Posição ABNT canto sup dir
    canvas.drawRightString(x_position, y_position, page_num_text)
    canvas.restoreState()

# Função para desenhar o cabeçalho completo (logos, títulos) E o número da página (SÓ PARA A PRIMEIRA PÁGINA)
def draw_full_header_and_page_number(canvas, doc, ata_object):
    canvas.saveState()

    # --- Configurações das Logos ---
    furg_logo_filename = "FURG.png"
    c3_logo_filename = "C3.png"
    furg_width_pt = 77 * 0.75
    furg_height_pt = 77 * 0.75
    c3_width_pt = 80 * 0.75 # Você tinha 77 aqui antes, mas no HTML era 80, mantendo 80
    c3_height_pt = 87 * 0.75 # Você tinha 84 aqui antes, mas no HTML era 87, mantendo 87

    margin_lateral_logo = 1 * cm
    margin_topo_logo = 1 * cm
    page_width, page_height = doc.pagesize

    # --- Desenhar Logo FURG (Esquerda) ---
    furg_logo_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.static_folder, 'uploads')), furg_logo_filename)
    if os.path.exists(furg_logo_path):
        try:
            furg_x = margin_lateral_logo
            furg_y = page_height - margin_topo_logo - furg_height_pt
            canvas.drawImage(furg_logo_path, furg_x, furg_y, width=furg_width_pt, height=furg_height_pt, mask='auto')
        except Exception as e:
            current_app.logger.error(f"Erro ao desenhar logo FURG no PDF: {e}")

    # --- Desenhar Logo C3 (Direita) ---
    c3_logo_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.static_folder, 'uploads')), c3_logo_filename)
    if os.path.exists(c3_logo_path):
        try:
            c3_x = page_width - margin_lateral_logo - c3_width_pt
            c3_y = page_height - margin_topo_logo - c3_height_pt
            canvas.drawImage(c3_logo_path, c3_x, c3_y, width=c3_width_pt, height=c3_height_pt, mask='auto')
        except Exception as e:
            current_app.logger.error(f"Erro ao desenhar logo C3 no PDF: {e}")

    # --- Desenhar Textos Centrais (Instituição, Título da Ata) ---
    font_name_header = "Times-Roman"
    font_name_header_bold = "Times-Bold"
    font_size_header_instituicao = 12
    font_size_header_ata = 12
    line_spacing_header_pt = 4

    y_current = page_height - margin_topo_logo - font_size_header_instituicao - (0.3 * cm)
    text_area_x_start = margin_lateral_logo + furg_width_pt + 0.5*cm
    text_area_x_end = page_width - margin_lateral_logo - c3_width_pt - 0.5*cm
    text_area_width = text_area_x_end - text_area_x_start
    text_area_center_x = text_area_x_start + text_area_width / 2

    if text_area_width > 0:
        canvas.setFont(font_name_header, font_size_header_instituicao)
        text_furg = "UNIVERSIDADE FEDERAL DO RIO GRANDE - FURG"
        canvas.drawCentredString(text_area_center_x, y_current, text_furg)
        y_current -= (font_size_header_instituicao + line_spacing_header_pt)

        text_pet = "PROJETO DE EDUCAÇÃO TUTORIAL - PET"
        canvas.drawCentredString(text_area_center_x, y_current, text_pet)
        y_current -= (font_size_header_instituicao + line_spacing_header_pt)

        text_pet_cc = "PET CIÊNCIAS COMPUTACIONAIS"
        canvas.drawCentredString(text_area_center_x, y_current, text_pet_cc)
        y_current -= (font_size_header_instituicao + line_spacing_header_pt + 6)

        canvas.setFont(font_name_header_bold, font_size_header_ata)
        text_ata_titulo = f"ATA DE REUNIÃO {ata_object.project.name.upper()}"
        canvas.drawCentredString(text_area_center_x, y_current, text_ata_titulo)

    # --- Número da Página (também desenhado pela função separada, mas aqui para a primeira página) ---
    page_num_text = f"{canvas.getPageNumber()}" # ou "1" se for sempre a primeira
    canvas.setFont("Times-Roman", 10)
    num_x_position = doc.pagesize[0] - 2*cm
    num_y_position = doc.pagesize[1] - 2*cm - (0.3*cm)
    canvas.drawRightString(num_x_position, num_y_position, page_num_text)

    canvas.restoreState()

def generate_ata_pdf(ata: 'Ata') -> bytes:
    buffer = io.BytesIO()
    pdf_document_title = f"Ata Reunião PET Comp - {ata.project.name} - {ata.meeting_datetime.strftime('%Y-%m-%d')}"
    
    # A margem superior do SimpleDocTemplate precisa ser grande o suficiente para o cabeçalho fixo DA PRIMEIRA PÁGINA.
    # Para as páginas subsequentes, o conteúdo começará mais acima, pois só haverá o número da página.
    # No entanto, SimpleDocTemplate usa a mesma topMargin para todas as páginas.
    # Uma solução é manter a topMargin grande e adicionar um Spacer no início da 'story' nas páginas
    # subsequentes se o cabeçalho for menor. Ou, para este caso, aceitar que as páginas subsequentes
    # terão um espaço em branco maior no topo se o cabeçalho da primeira página for muito alto.
    # Vamos manter a margem calculada para o cabeçalho completo.
    new_top_margin = 5.5 * cm

    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=3*cm, rightMargin=2*cm,
        topMargin=new_top_margin, bottomMargin=2*cm, title=pdf_document_title
    )

    styles = getSampleStyleSheet()
    base_font_name = "Times-Roman"
    bold_font_name = "Times-Bold"

    styles.add(ParagraphStyle(name='ABNT_Corpo', parent=styles['Normal'], fontName=base_font_name, fontSize=12, leading=18, alignment=TA_JUSTIFY, firstLineIndent=1.25*cm, spaceBefore=0, spaceAfter=6 ))
    styles.add(ParagraphStyle(name='ABNT_InfoBloco', parent=styles['ABNT_Corpo'], alignment=TA_LEFT, spaceBefore=0.2*cm, spaceAfter=0.2*cm, firstLineIndent=0))
    styles.add(ParagraphStyle(name='ABNT_SecaoTitulo', parent=styles['ABNT_Corpo'], fontSize=12, fontName=bold_font_name, alignment=TA_LEFT, spaceBefore=0.8*cm, spaceAfter=0.4*cm, firstLineIndent=0))
    styles.add(ParagraphStyle(name='ABNT_ListaLabel', parent=styles['ABNT_Corpo'], fontName=bold_font_name, alignment=TA_LEFT, spaceBefore=0.3*cm, spaceAfter=0.1*cm, firstLineIndent=0))
    styles.add(ParagraphStyle(name='ABNT_ListItem', parent=styles['ABNT_Corpo'], leftIndent=0, firstLineIndent=0, alignment=TA_JUSTIFY, spaceBefore=0, spaceAfter=0)) # MUDADO PARA TA_JUSTIFY
    
    # MUDANÇA: Novo estilo para o local/data final centralizado
    styles.add(ParagraphStyle(
        name='ABNT_LocalDataFinal', 
        parent=styles['ABNT_Corpo'], 
        alignment=TA_CENTER, # Centralizado
        firstLineIndent=0,   # Sem recuo
        spaceBefore=1*cm     # Espaço antes dele
    ))

    story = []

    # --- Informações da Reunião ---
    try:
        meeting_time_str = ata.meeting_datetime.strftime('%d de %B de %Y, às %H:%M')
    except ValueError:
        meeting_time_str = ata.meeting_datetime.strftime('%d/%m/%Y às %H:%M')
        if current_app: current_app.logger.warning("Usando formato de data fallback.")
    story.append(Paragraph(f"<b>Data e Horário:</b> {meeting_time_str}", styles['ABNT_InfoBloco']))
    location_str = f"<b>Local/Modalidade:</b> {ata.location_type.value}"
    if ata.location_details:
        location_str += f" ({ata.location_details})"
    story.append(Paragraph(location_str, styles['ABNT_InfoBloco']))
    story.append(Spacer(1, 0.5*cm))

    # --- Lista de Participantes ---
    story.append(Paragraph("PARTICIPANTES", styles['ABNT_SecaoTitulo']))
    present_members = sorted([m.name for m in ata.present_members])
    absent_members = sorted([m.name for m in ata.absent_members])
    if present_members:
        story.append(Paragraph("Presentes:", styles['ABNT_ListaLabel']))
        present_list = ListFlowable( [ListItem(Paragraph(name, styles['ABNT_ListItem'])) for name in present_members], bulletType='bullet', leftIndent=1.25*cm )
        story.append(present_list)
    else:
         story.append(Paragraph("Presentes: Não houve presentes registrados.", styles['ABNT_InfoBloco']))
    if absent_members:
        story.append(Paragraph("Ausentes:", styles['ABNT_ListaLabel']))
        absent_list = ListFlowable( [ListItem(Paragraph(name, styles['ABNT_ListItem'])) for name in absent_members], bulletType='bullet', leftIndent=1.25*cm )
        story.append(absent_list)
    story.append(Spacer(1, 0.5*cm))

    # --- Assuntos Tratados / Deliberações ---
    story.append(Paragraph("ASSUNTOS TRATADOS E DELIBERAÇÕES", styles['ABNT_SecaoTitulo']))
    if ata.notes:
        note_paragraphs = ata.notes.strip().split('\n')
        for note_para_text in note_paragraphs:
            if note_para_text.strip():
                processed_text = note_para_text.replace("    ", "    ")
                story.append(Paragraph(processed_text, styles['ABNT_Corpo']))
    else:
        story.append(Paragraph("Nenhuma anotação registrada.", styles['ABNT_Corpo']))
    story.append(Spacer(1, 0.8*cm))

    # --- Texto de Encerramento ---
    texto_encerramento = "E, por nada mais haver a tratar, encerrou-se a reunião."
    story.append(Paragraph(texto_encerramento, styles['ABNT_Corpo']))
    # Removido o Spacer(1, 1*cm) daqui, o estilo ABNT_LocalDataFinal já tem spaceBefore

    # --- Local e Data no Final ---
    # MUDANÇA: Usando "Rio Grande" fixo e o novo estilo ABNT_LocalDataFinal
    cidade_final = "Rio Grande"
    try:
        data_extenso_final = ata.meeting_datetime.strftime('%d de %B de %Y')
    except ValueError:
        data_extenso_final = ata.meeting_datetime.strftime('%d/%m/%Y')
    story.append(Paragraph(f"{cidade_final}, {data_extenso_final}.", styles['ABNT_LocalDataFinal']))
    
    try:
        # MUDANÇA: Usando funções diferentes para a primeira página e páginas subsequentes
        doc.build(story, 
                  onFirstPage=lambda canvas, doc: draw_full_header_and_page_number(canvas, doc, ata),
                  onLaterPages=draw_page_number_only) # Só o número da página nas demais
        pdf_data = buffer.getvalue()
    except Exception as e:
        current_app.logger.error(f"Erro ao construir PDF (doc.build) para ata {ata.id}: {e}")
        raise Exception(f"Erro interno ao gerar PDF: {e}") from e
    finally:
        buffer.close()

    return pdf_data