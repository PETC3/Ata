# seu_projeto_flask/app/utils.py

import io
import os
import locale
from datetime import datetime
from flask import current_app

# Tenta importar num2words
try:
    from num2words import num2words
    NUM2WORDS_DISPONIVEL = True
except ImportError:
    NUM2WORDS_DISPONIVEL = False
    if current_app:
        current_app.logger.warning("Biblioteca 'num2words' não encontrada. Anos serão exibidos em numeral.")
    else:
        print("Aviso: Biblioteca 'num2words' não encontrada. Anos serão exibidos em numeral.")


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
            log_msg = "Locale 'pt_BR' ou 'Portuguese' não configurado."
            if current_app: current_app.logger.warning(log_msg)
            else: print(f"Aviso: {log_msg}")

# Mantido para os dias do mês, pois oferece formatação específica (ex: "quatorze")
DIAS_EXTENSO = {
    1: "primeiro", 2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete",
    8: "oito", 9: "nove", 10: "dez", 11: "onze", 12: "doze", 13: "treze", 14: "quatorze",
    15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove", 20: "vinte",
    21: "vinte e um", 22: "vinte e dois", 23: "vinte e três", 24: "vinte e quatro",
    25: "vinte e cinco", 26: "vinte e seis", 27: "vinte e sete", 28: "vinte e oito",
    29: "vinte e nove", 30: "trinta", 31: "trinta e um"
}

def get_ano_por_extenso(ano_int):
    if NUM2WORDS_DISPONIVEL:
        try:
            # 'to="year"' pode ser útil, mas o padrão geralmente funciona bem para pt_BR
            return num2words(ano_int, lang='pt_BR', to='year')
        except Exception as e:
            log_msg = f"Erro ao converter ano {ano_int} com num2words: {e}. Usando numeral."
            if current_app: current_app.logger.error(log_msg)
            else: print(log_msg)
            return str(ano_int)
    return str(ano_int)

def draw_page_number_only(canvas, doc):
    canvas.saveState()
    page_num_text = f"{canvas.getPageNumber()}"
    canvas.setFont("Times-Roman", 10)
    x_position = doc.pagesize[0] - 2*cm
    y_position = doc.pagesize[1] - 2*cm - (0.3*cm)
    canvas.drawRightString(x_position, y_position, page_num_text)
    canvas.restoreState()

def draw_first_page_header_custom(canvas, doc, ata_object):
    canvas.saveState()
    page_width, page_height = doc.pagesize

    logo_filename = "FURG.png" # !!! AJUSTE: Nome do arquivo da sua logo central !!!
    logo_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.static_folder, 'uploads')), logo_filename)
    logo_width_pt = 50
    logo_height_pt = 50
    y_logo_start = page_height - doc.topMargin + (doc.topMargin * 0.65)
    logo_x = (page_width - logo_width_pt) / 2
    logo_y = y_logo_start - logo_height_pt

    if os.path.exists(logo_path):
        try:
            canvas.drawImage(logo_path, logo_x, logo_y, width=logo_width_pt, height=logo_height_pt, mask='auto')
        except Exception as e:
            current_app.logger.error(f"Erro ao desenhar logo central no PDF: {e}")
    else:
        current_app.logger.warning(f"Arquivo de logo central não encontrado: {logo_path}")

    font_name_header = "Helvetica"
    font_name_header_bold = "Helvetica-Bold"
    font_size_instituicao = 10
    font_size_ata_titulo = 10
    line_spacing_header_pt = 12
    y_current = logo_y - 0.5*cm

    textos_cabecalho = [
        ("UNIVERSIDADE FEDERAL DO RIO GRANDE – FURG", font_name_header, font_size_instituicao),
        ("CENTRO DE CIÊNCIAS COMPUTACIONAIS", font_name_header, font_size_instituicao),
        ("PET – Ciências Computacionais – C3", font_name_header, font_size_instituicao),
    ]
    for text, font, size in textos_cabecalho:
        canvas.setFont(font, size)
        canvas.drawCentredString(page_width / 2, y_current, text)
        y_current -= line_spacing_header_pt

    y_current -= (line_spacing_header_pt * 0.2)
    canvas.setFont(font_name_header_bold, font_size_ata_titulo)
    text_ata_titulo = f"ATA {ata_object.meeting_datetime.strftime('%d/%m/%Y')}"
    canvas.drawCentredString(page_width / 2, y_current, text_ata_titulo)
    canvas.restoreState()

def generate_ata_pdf(ata: 'Ata') -> bytes:
    buffer = io.BytesIO()
    pdf_document_title = f"Ata Reunião PET Ciências Computacionais - {ata.project.name} - {ata.meeting_datetime.strftime('%Y-%m-%d')}"
    
    new_top_margin = 6.5 * cm 

    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=3*cm, rightMargin=2*cm,
        topMargin=new_top_margin, bottomMargin=2*cm, title=pdf_document_title
    )

    styles = getSampleStyleSheet()
    base_font_name = "Times-Roman"
    bold_font_name = "Times-Bold"

    styles.add(ParagraphStyle(name='ABNT_Corpo', parent=styles['Normal'], fontName=base_font_name, fontSize=12, leading=18, alignment=TA_JUSTIFY, firstLineIndent=1.25*cm, spaceBefore=0, spaceAfter=0 ))
    styles.add(ParagraphStyle(name='ABNT_ListaLabel', parent=styles['ABNT_Corpo'], fontName=bold_font_name, alignment=TA_LEFT, spaceBefore=0.3*cm, spaceAfter=0.1*cm, firstLineIndent=0))
    styles.add(ParagraphStyle(name='ABNT_ListItem', parent=styles['ABNT_Corpo'], leftIndent=1.25*cm, firstLineIndent=0, alignment=TA_JUSTIFY, spaceBefore=0, spaceAfter=0))
    styles.add(ParagraphStyle(name='LinhaAssinatura', parent=styles['Normal'], alignment=TA_CENTER, fontName='Courier', fontSize=12, spaceBefore=1*cm, spaceAfter=0.1*cm))
    styles.add(ParagraphStyle(name='NomeSignatario', parent=styles['Normal'], alignment=TA_CENTER, fontName=base_font_name, fontSize=12, spaceBefore=0.1*cm))

    story = []

    # --- Construção do parágrafo introdutório (data, presentes e ausentes) ---
    try:
        dia_int = ata.meeting_datetime.day
        dia_str_extenso = DIAS_EXTENSO.get(dia_int, str(dia_int))
        mes_str_extenso = ata.meeting_datetime.strftime('%B')
        ano_str_extenso = get_ano_por_extenso(ata.meeting_datetime.year)
        data_completa_extenso = f"{dia_str_extenso} dias do mês de {mes_str_extenso} de {ano_str_extenso}"
    except Exception as e:
        current_app.logger.error(f"Erro ao formatar data por extenso: {e}")
        data_completa_extenso = ata.meeting_datetime.strftime('%d de %B de %Y')

    # Informações dos presentes
    presentes_nomes = sorted([m.name for m in ata.present_members])
    if presentes_nomes:
        if len(presentes_nomes) == 1:
            presentes_str_formatado = f"com o seguinte presente: {presentes_nomes[0]}"
        elif len(presentes_nomes) > 1:
            presentes_str_formatado = f"com os seguintes presentes: {', '.join(presentes_nomes[:-1])} e {presentes_nomes[-1]}"
    else:
        presentes_str_formatado = "sem a presença de integrantes registrados"
    
    
    # --------------------------------------------------------------------------
    # NOVO BLOCO DE LÓGICA: Informações dos ausentes (Com e Sem Justificativa)
    # --------------------------------------------------------------------------
    
    # 1. Obter membros ausentes e justificativas salvas
    absent_members = ata.absent_members 
    justifications_dict = ata.absent_justifications_dict # Obtém {member_id: justificativa}
    
    ausentes_com_justificativa = []
    ausentes_sem_justificativa = []

    for member in absent_members:
        justificativa = justifications_dict.get(member.id)
        
        if justificativa and justificativa.strip():
            # Membro ausente com justificativa
            ausentes_com_justificativa.append(f"{member.name} (Motivo: {justificativa.strip()})")
        else:
            # Membro ausente sem justificativa registrada
            ausentes_sem_justificativa.append(member.name)


    # 2. Construir as strings formatadas
    ausentes_justificados_str = ""
    ausentes_sem_justificativa_str = ""
    
    if ausentes_com_justificativa:
        ausentes_justificados_str = (
            f"Estiveram ausentes com justificativa: {', '.join(ausentes_com_justificativa)}. "
        )
        
    if ausentes_sem_justificativa:
        # Se houver ausentes sem justificativa, separamos a frase
        sem_justificativa_nomes = (
            f"{', '.join(ausentes_sem_justificativa[:-1])} e {ausentes_sem_justificativa[-1]}"
            if len(ausentes_sem_justificativa) > 1
            else ausentes_sem_justificativa[0]
        )
        ausentes_sem_justificativa_str = (
            f"Estiveram ausentes sem justificativa: {sem_justificativa_nomes}."
        )

    # 3. Combinar as strings para o texto introdutório
    # Se ambos existirem, serão concatenados. Usamos .strip() para limpar espaços extras se uma das partes for vazia.
    ausentes_str_formatado = (ausentes_justificados_str + ausentes_sem_justificativa_str).strip()
    
    # Garantir que a string não seja vazia se houver ausentes registrados
    if not ausentes_str_formatado:
        ausentes_str_formatado = "Nenhum membro ausente."

    # --------------------------------------------------------------------------
    # FIM DO NOVO BLOCO DE LÓGICA
    # --------------------------------------------------------------------------


    # Início do texto introdutório (USA O NOVO ausentes_str_formatado)
    intro_text_parts = [
        f"Aos {data_completa_extenso}, reuniram-se os integrantes do PET Ciências Computacionais {presentes_str_formatado}. {ausentes_str_formatado}"
    ]

    # Junta todas as partes do texto introdutório
    final_intro_text = "".join(intro_text_parts)
    
    story.append(Paragraph(final_intro_text, styles['ABNT_Corpo']))
    #story.append(Spacer(1, 0.5*cm)) # Espaçador após o parágrafo introdutório combinado

    # --- Assuntos Tratados / Deliberações ---
    if ata.notes:
        note_paragraphs = ata.notes.strip().split('\n')
        for note_para_text in note_paragraphs:
            if note_para_text.strip():
                processed_text = note_para_text.replace("    ", "    ")
                story.append(Paragraph(processed_text, styles['ABNT_Corpo']))
    else:
        story.append(Paragraph("Nenhuma anotação registrada.", styles['ABNT_Corpo']))
    #story.append(Spacer(1, 0.5*cm))

    # --- Texto de Encerramento e Local/Data Final ---
    cidade_final = "Rio Grande"
    texto_encerramento_final = (
        f"Posteriormente, foi lavrada a presente ata, que será lida e aprovada em próxima reunião. "
        f"{cidade_final}, aos {data_completa_extenso} "
    )
    story.append(Paragraph(texto_encerramento_final, styles['ABNT_Corpo']))


    try:
        doc.build(story, 
                  onFirstPage=lambda canvas, doc_obj: draw_first_page_header_custom(canvas, doc_obj, ata),
                  onLaterPages=draw_page_number_only)
        pdf_data = buffer.getvalue()
    except Exception as e:
        current_app.logger.error(f"Erro ao construir PDF (doc.build) para ata {getattr(ata, 'id', 'N/A')}: {e}", exc_info=True)
        raise Exception(f"Erro interno ao gerar PDF: {e}") from e
    finally:
        buffer.close()

    return pdf_data