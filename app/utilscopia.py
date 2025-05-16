# seu_projeto_flask/app/utils.py

import io
import os
import locale
from datetime import datetime
from flask import current_app

from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, ListFlowable, ListItem, PageBreak, Flowable)
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
# Dicionário para dias por extenso (simplificado)
DIAS_EXTENSO = {
    1: "primeiro", 2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete",
    8: "oito", 9: "nove", 10: "dez", 11: "onze", 12: "doze", 13: "treze", 14: "quatorze",
    15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove", 20: "vinte",
    21: "vinte e um", 22: "vinte e dois", 23: "vinte e três", 24: "vinte e quatro",
    25: "vinte e cinco", 26: "vinte e seis", 27: "vinte e sete", 28: "vinte e oito",
    29: "vinte e nove", 30: "trinta", 31: "trinta e um"
}
# --- Elemento para linha horizontal ---
class Line(Flowable):
    def __init__(self, width, height=0, stroke_color=colors.black, stroke_width=0.5):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width

    def draw(self):
        self.canv.setStrokeColor(self.stroke_color)
        self.canv.setLineWidth(self.stroke_width)
        self.canv.line(0, self.height/2, self.width, self.height/2)

# --- Funções de Desenho para Cabeçalho/Rodapé ---

def draw_page_number_only(canvas, doc):
    """ Desenha APENAS o número da página (para páginas subsequentes) """
    canvas.saveState()
    page_num_text = f"{canvas.getPageNumber()}"
    canvas.setFont("Times-Roman", 10)
    # Posição ABNT canto sup dir: 2cm da borda direita, 2cm da borda superior
    # Considerando margem direita de 2cm do documento, x é page_width - rightMargin
    # Considerando margem superior de 2cm do documento, y é page_height - topMargin
    # No entanto, o conteúdo do flowable começa *abaixo* da topMargin do SimpleDocTemplate.
    # Para posicionamento absoluto na página:
    x_position = doc.pagesize[0] - 2*cm
    y_position = doc.pagesize[1] - 2*cm - (0.3*cm) # Ajuste fino para alinhar com topo do texto
    canvas.drawRightString(x_position, y_position, page_num_text)
    canvas.restoreState()

def draw_first_page_header(canvas, doc, ata_object):
    """ Desenha o cabeçalho completo (logo, títulos) para a PRIMEIRA PÁGINA """
    canvas.saveState()
    page_width, page_height = doc.pagesize

    # --- Configurações da Logo ---
    # Substitua 'logo_pet_c3.png' pelo nome do seu arquivo de logo.
    # A logo na imagem de exemplo é um 'U' estilizado.
    logo_filename = "FURG.png" # Use a logo correta aqui!
    logo_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.static_folder, 'uploads')), logo_filename)
    
    logo_width_pt = 50 # Ajuste conforme necessário
    logo_height_pt = 50 # Ajuste conforme necessário
    
    # Posição da Logo (Centralizada no topo, acima do texto do cabeçalho)
    # Margem superior do documento é doc.topMargin (3.5cm no nosso caso)
    # O cabeçalho é desenhado DENTRO dessa margem.
    logo_x = (page_width - logo_width_pt) / 2
    logo_y = page_height - doc.topMargin + 2*cm # Posiciona a logo um pouco abaixo do topo da margem

    if os.path.exists(logo_path):
        try:
            canvas.drawImage(logo_path, logo_x, logo_y, width=logo_width_pt, height=logo_height_pt, mask='auto')
        except Exception as e:
            current_app.logger.error(f"Erro ao desenhar logo no PDF: {e}")
    else:
        current_app.logger.warning(f"Arquivo de logo não encontrado: {logo_path}")

    # --- Textos Centrais do Cabeçalho ---
    # Usando Helvetica (sans-serif) como na imagem
    font_name_header = "Helvetica"
    font_name_header_bold = "Helvetica-Bold" # Ou apenas Helvetica para tudo

    # Posição inicial Y para os textos (abaixo da logo)
    y_current = logo_y - 0.5*cm # Espaço entre logo e primeiro texto
    line_height_header = 14 # pt, ajuste conforme necessário

    textos_cabecalho = [
        ("UNIVERSIDADE FEDERAL DO RIO GRANDE – FURG", font_name_header, 10),
        ("CENTRO DE CIÊNCIAS COMPUTACIONAIS", font_name_header, 10),
        ("PET – Ciências Computacionais – C3", font_name_header, 10),
    ]

    for text, font, size in textos_cabecalho:
        canvas.setFont(font, size)
        canvas.drawCentredString(page_width / 2, y_current, text)
        y_current -= line_height_header

    # Título da Ata (ATA DD/MM/YYYY)
    y_current -= (line_height_header * 0.5) # Espaço extra antes do título da ata
    canvas.setFont(font_name_header_bold, 10) # Negrito para o título da ata
    ata_titulo_texto = f"ATA {ata_object.meeting_datetime.strftime('%d/%m/%Y')}"
    canvas.drawCentredString(page_width / 2, y_current, ata_titulo_texto)
    
    canvas.restoreState()


def generate_ata_pdf(ata: 'Ata') -> bytes:
    buffer = io.BytesIO()
    pdf_document_title = f"Ata {ata.project.name} - {ata.meeting_datetime.strftime('%Y-%m-%d')}"
    
    # Margem superior ajustada para o novo cabeçalho mais compacto
    # Esta margem é onde o `draw_first_page_header` irá desenhar.
    # O conteúdo do `story` começará abaixo desta margem.
    # A altura estimada do cabeçalho (logo + textos) é de aprox. 3cm.
    # Deixamos um pouco mais para garantir.
    current_top_margin = 3.5 * cm

    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=3*cm, rightMargin=2*cm,
        topMargin=current_top_margin, bottomMargin=2*cm, title=pdf_document_title
    )

    styles = getSampleStyleSheet()
    base_font_name = "Times-Roman"
    bold_font_name = "Times-Bold"

    # --- Estilos de Parágrafo ---
    # Estilo principal para o corpo do texto
    styles.add(ParagraphStyle(name='ABNT_Corpo', parent=styles['Normal'], fontName=base_font_name, fontSize=12, leading=18, alignment=TA_JUSTIFY, firstLineIndent=1.25*cm, spaceBefore=0, spaceAfter=6 ))
    # Estilo para itens de lista (se necessário para ausentes ou outros)
    styles.add(ParagraphStyle(name='ABNT_ListItem', parent=styles['ABNT_Corpo'], leftIndent=1.25*cm, firstLineIndent=0, alignment=TA_JUSTIFY, spaceBefore=0, spaceAfter=2))
    # Estilo para o nome do signatário
    styles.add(ParagraphStyle(name='ABNT_SignatarioNome', parent=styles['Normal'], fontName=base_font_name, fontSize=12, alignment=TA_CENTER, spaceBefore=2))
    # Estilo para a linha de hífens (se quiser mais controle)
    styles.add(ParagraphStyle(name='ABNT_LinhaFinal', parent=styles['ABNT_Corpo'], alignment=TA_LEFT, firstLineIndent=0, spaceBefore=6, spaceAfter=12))


    story = []

    # --- Parágrafo Introdutório (Data, Presentes) ---
    try:
        data_extenso_intro = ata.meeting_datetime.strftime('%A, %d de %B de %Y').capitalize()
        # Para "Aos quatorze dias..."
        dia_numero_extenso = {
            1: "primeiro", 2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove", 10: "dez",
            11: "onze", 12: "doze", 13: "treze", 14: "quatorze", 15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove", 20: "vinte",
            21: "vinte e um", 22: "vinte e dois", 23: "vinte e três", 24: "vinte e quatro", 25: "vinte e cinco", 26: "vinte e seis", 27: "vinte e sete", 28: "vinte e oito", 29: "vinte e nove", 30: "trinta", 31: "trinta e um"
        }
        dia_num = ata.meeting_datetime.day
        mes_extenso = ata.meeting_datetime.strftime('%B')
        ano_extenso_num = ata.meeting_datetime.year # Para "dois mil e vinte e cinco", precisaria de num2words ou similar. Simplificando para número.
        
        # Texto da imagem: "Aos quatorze dias do mês de maio de dois mil e vinte e cinco, reuniram-se..."
        # Simplificação para data:
        data_texto_intro = f"Aos {dia_numero_extenso.get(dia_num, str(dia_num))} dias do mês de {mes_extenso} de {ano_extenso_num}"

    except ValueError: # Fallback para formato de data se locale falhar
        data_texto_intro = f"Em {ata.meeting_datetime.strftime('%d/%m/%Y')}"
        if current_app: current_app.logger.warning("Usando formato de data fallback para introdução.")

    # Montar a lista de presentes
    # ATENÇÃO: A imagem distingue tipos de presentes. O modelo atual não.
    # Esta é uma simplificação. Ajuste se seu modelo `Ata` tiver mais detalhes.
    presentes_str = "Ninguém esteve presente."
    if ata.present_members:
        nomes_presentes = sorted([m.name for m in ata.present_members])
        if len(nomes_presentes) == 1:
            presentes_str = f"esteve presente: {nomes_presentes[0]}."
        elif len(nomes_presentes) > 1:
            presentes_str = f"estiveram presentes: {', '.join(nomes_presentes[:-1])} e {nomes_presentes[-1]}."
    
    # TODO: Adicionar lógica para distinguir "Professores" de "outros online" se o modelo permitir.
    # Por ora, a imagem cita:
    # "Prof.André Luis Castro de Freitas, Andrew Devos Cotta de Mello e Fábio Andre Rodrigues Ceroni Junior."
    # "De forma on-line estavam na reunião: Andrew de Jesus Garcia, Clarice Dziekaniak da Silveira, ..."
    # Para replicar isso, você precisaria de campos/listas separadas no seu objeto `ata`.
    # Por exemplo, usando os nomes da imagem (isso deveria vir do seu modelo `ata`):
    professores_presentes_exemplo = "Prof. André Luis Castro de Freitas, Andrew Devos Cotta de Mello e Fábio Andre Rodrigues Ceroni Junior"
    online_presentes_exemplo = "Andrew de Jesus Garcia, Clarice Dziekaniak da Silveira, Gustavo do Amaral Gimenes, João Gabriel Freitas Acosta, Lara Letittja Sague Lopez Guardiola Velloso, Luiz Fernando Viana Ciriaco, Sofia Botesini, Vitor dos Santos Bandeira e Yan Karlo da Silva Veiga Vasconcellos Dutra"

    # Parágrafo inicial conforme imagem (com dados de exemplo para presentes):
    # Ajuste para usar `ata.present_members` ou dados específicos do seu modelo
    paragrafo_inicial_texto = (
        f"{data_texto_intro}, reuniram-se os integrantes do PET Ciências Computacionais. "
        f"Estiveram presentes: {professores_presentes_exemplo}. " # SUBSTITUA PELA LÓGICA REAL
        f"De forma on-line estavam na reunião: {online_presentes_exemplo}." # SUBSTITUA PELA LÓGICA REAL
    )
    story.append(Paragraph(paragrafo_inicial_texto, styles['ABNT_Corpo']))
    story.append(Spacer(1, 0.3*cm))


    # --- Assuntos Tratados / Deliberações (Corpo principal da ata) ---
    # Removido o título da seção. O conteúdo de ata.notes segue diretamente.
    if ata.notes:
        note_paragraphs = ata.notes.strip().split('\n')
        for note_para_text in note_paragraphs:
            if note_para_text.strip():
                # Processar <br> ou \n para novos parágrafos dentro das notas, se necessário
                # Ou tratar cada linha como um parágrafo
                # A substituição de espaços é mantida caso seja útil para formatação manual.
                processed_text = note_para_text.replace("    ", "    ") #   para não colapsar
                story.append(Paragraph(processed_text, styles['ABNT_Corpo']))
    else:
        story.append(Paragraph("Nenhuma anotação registrada para os assuntos tratados.", styles['ABNT_Corpo']))
    story.append(Spacer(1, 0.5*cm))

    # --- Lista de Ausentes (Opcional, manter se relevante) ---
    absent_members = sorted([m.name for m in ata.absent_members])
    if absent_members:
        story.append(Paragraph("<b>Ausentes:</b>", styles['ABNT_Corpo'])) # Ou um estilo ABNT_ListaLabel
        absent_list = ListFlowable( [ListItem(Paragraph(name, styles['ABNT_ListItem'])) for name in absent_members], bulletType='bullet')
        story.append(absent_list)
        story.append(Spacer(1, 0.5*cm))

    # --- Texto de Encerramento (Conforme a imagem) ---
    # "Posteriormente, foi lavrada a presente ata, que será lida e aprovada
    # em próxima reunião. Rio Grande, aos quatorze dias do mês de maio de dois mil e vinte e
    # cinco -.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-."

    # Recriar a data por extenso para o final
    local_final = "Rio Grande"
    try:
        dia_final_num = ata.meeting_datetime.day
        mes_final_extenso = ata.meeting_datetime.strftime('%B')
        ano_final_texto = "de " + " ".join([dia_numero_extenso.get(int(d), d) for d in str(ata.meeting_datetime.year)]) # Ex: "dois mil e vinte e cinco"
        # A conversão de ano para extenso é complexa, simplificando:
        ano_final_texto = str(ata.meeting_datetime.year)

        data_final_extenso = f"{local_final}, aos {dia_numero_extenso.get(dia_final_num, str(dia_final_num))} dias do mês de {mes_final_extenso} de {ano_final_texto}"
    except:
        data_final_extenso = f"{local_final}, {ata.meeting_datetime.strftime('%d/%m/%Y')}"


    texto_encerramento_img = (
        f"Posteriormente, foi lavrada a presente ata, que será lida e aprovada em próxima reunião. "
        f"{data_final_extenso} "
        f"<font name=Courier><b>-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.</b></font>" # Usando Courier para os traços
    )
    story.append(Paragraph(texto_encerramento_img, styles['ABNT_Corpo'])) # Usando ABNT_Corpo, que tem justificado
    story.append(Spacer(1, 1*cm)) # Espaço antes da linha de assinatura

    # --- Assinatura ---
    # Placeholder para o nome do signatário - substitua pela lógica real
    # Exemplo: ata.secretary.name, ata.president.name, etc.
    # Adicione o título (Prof., Dra., etc.) se necessário
    signer_name_completo = "Prof. André Luis Castro de Freitas" # Substitua isso!
    # if hasattr(ata, 'signer_title') and ata.signer_title:
    #     signer_name_completo = f"{ata.signer_title} {ata.signer_name}"
    # else:
    #     signer_name_completo = ata.signer_name


    # Linha para assinatura
    # Pode ser uma imagem de uma linha, ou desenhada com canvas, ou um Paragraph com underscores.
    # Usando um Paragraph com underscores é mais simples dentro do flowable.
    # Ajuste o número de underscores para o comprimento desejado.
    # Ou use o elemento Line definido no início.
    # Para SimpleDocTemplate, a largura total menos margens: A4[0] - 3*cm - 2*cm
    available_width = A4[0] - doc.leftMargin - doc.rightMargin
    # story.append(Line(available_width * 0.6, stroke_width=0.5)) # Linha com 60% da largura útil
    
    # Ou, para centralizar a linha de assinatura como na imagem (que parece ter ~50% da largura):
    assinatura_linha_texto = "_" * 40 # Ajuste o comprimento
    assinatura_linha_style = ParagraphStyle(name='LinhaAssinatura', parent=styles['Normal'], alignment=TA_CENTER, spaceBefore=0.5*cm, spaceAfter=0)
    story.append(Paragraph(assinatura_linha_texto, assinatura_linha_style))

    story.append(Paragraph(signer_name_completo, styles['ABNT_SignatarioNome']))


    try:
        doc.build(story,
                  onFirstPage=lambda canvas, doc_obj: draw_first_page_header(canvas, doc_obj, ata),
                  onLaterPages=draw_page_number_only) # Numeração para páginas subsequentes
        pdf_data = buffer.getvalue()
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Erro ao construir PDF (doc.build) para ata {getattr(ata, 'id', 'N/A')}: {e}", exc_info=True)
        else:
            print(f"Erro ao construir PDF: {e}")
        raise Exception(f"Erro interno ao gerar PDF: {e}") from e
    finally:
        buffer.close()

    return pdf_data