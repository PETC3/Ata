# seu_projeto_flask/app/utils.py

import io
import os
from datetime import datetime
from flask import current_app # Para acessar config (UPLOAD_FOLDER)

# Importações do ReportLab
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, ListFlowable, ListItem)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm

# Importa o modelo Ata para type hinting (opcional, mas boa prática)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import Ata


def generate_ata_pdf(ata: 'Ata') -> bytes:
    """
    Gera o conteúdo de um arquivo PDF para a Ata fornecida.

    Args:
        ata: A instância do modelo Ata contendo os dados.

    Returns:
        Bytes representando o arquivo PDF gerado.

    Raises:
        FileNotFoundError: Se o arquivo de logo do projeto não for encontrado.
        Exception: Para outros erros durante a geração do PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title=f"Ata Reunião - {ata.project.name} - {ata.meeting_datetime.strftime('%Y-%m-%d')}"
    )

    styles = getSampleStyleSheet()

    # Estilos customizados (opcional)
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, parent=styles['Normal']))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, parent=styles['h1']))
    styles.add(ParagraphStyle(name='Subtitle', alignment=TA_CENTER, fontSize=12, parent=styles['h2']))
    styles.add(ParagraphStyle(name='SectionTitle', fontSize=11, spaceBefore=10, spaceAfter=5, parent=styles['h3']))


    story = [] # Lista de elementos Platypus que formarão o PDF

    # --- Cabeçalho ---
    # Logo (se existir)
    logo_path = None
    if ata.project.logo:
        logo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], ata.project.logo)
        if not os.path.exists(logo_path):
            current_app.logger.warning(f"Arquivo de logo não encontrado: {logo_path}")
            logo_path = None # Ignora se não encontrar

    if logo_path:
        try:
            # Tenta carregar a imagem, definindo largura máxima
            img = Image(logo_path, width=3*cm, height=3*cm) # Ajuste tamanho conforme necessário
            img.hAlign = 'LEFT' # Alinha a imagem
            story.append(img)
            story.append(Spacer(1, 0.5*cm)) # Espaço após logo
        except Exception as e:
            current_app.logger.error(f"Erro ao carregar logo {logo_path} para PDF: {e}")
            # Continua sem o logo se der erro

    story.append(Paragraph("ATA DE REUNIÃO", styles['Center']))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Projeto: {ata.project.name}", styles['Subtitle']))
    story.append(Spacer(1, 0.8*cm))

    # --- Informações da Reunião ---
    meeting_time_str = ata.meeting_datetime.strftime('%d/%m/%Y às %H:%M')
    story.append(Paragraph(f"<b>Data e Hora:</b> {meeting_time_str}", styles['Normal']))

    location_str = f"<b>Local/Modalidade:</b> {ata.location_type.value}" # Usa o valor do Enum
    if ata.location_details:
        location_str += f" ({ata.location_details})"
    story.append(Paragraph(location_str, styles['Normal']))
    story.append(Spacer(1, 0.8*cm))

    # --- Lista de Participantes ---
    story.append(Paragraph("PARTICIPANTES", styles['SectionTitle']))

    present_members = sorted([m.name for m in ata.present_members])
    absent_members = sorted([m.name for m in ata.absent_members]) # Usa a property do modelo

    # Usando ListFlowable para listas com marcadores
    if present_members:
        story.append(Paragraph("<b>Presentes:</b>", styles['Normal']))
        present_list = ListFlowable(
            [ListItem(Paragraph(name, styles['Normal'])) for name in present_members],
            bulletType='bullet',
            start='circle', # ou 'square', 'diamond', etc.
        )
        story.append(present_list)
        story.append(Spacer(1, 0.3*cm))
    else:
         story.append(Paragraph("<b>Presentes:</b> Nenhum membro presente registrado.", styles['Normal']))
         story.append(Spacer(1, 0.3*cm))


    if absent_members:
        story.append(Paragraph("<b>Ausentes:</b>", styles['Normal']))
        absent_list = ListFlowable(
            [ListItem(Paragraph(name, styles['Normal'])) for name in absent_members],
            bulletType='bullet',
            start='circle',
        )
        story.append(absent_list)
        story.append(Spacer(1, 0.3*cm))
    # Se não houver ausentes, não adicionamos nada (ou podemos adicionar "Nenhum")
    # else:
    #    story.append(Paragraph("<b>Ausentes:</b> Nenhum.", styles['Normal']))


    story.append(Spacer(1, 0.8*cm))

    # --- Assuntos Tratados / Deliberações ---
    story.append(Paragraph("ASSUNTOS TRATADOS E DELIBERAÇÕES", styles['SectionTitle']))

    # Para preservar quebras de linha do TextArea, substituímos \n por <br/>
    notes_formatted = ata.notes.replace('\n', '<br/>') if ata.notes else "Nenhuma anotação registrada."
    story.append(Paragraph(notes_formatted, styles['Justify']))
    story.append(Spacer(1, 1*cm))

    # --- Rodapé (Exemplo) ---
    # story.append(Paragraph(f"Ata gerada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['small'])) # Estilo 'small' não existe por padrão

    # --- Construir o PDF ---
    try:
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data
    except Exception as e:
        current_app.logger.error(f"Erro ao construir PDF (doc.build) para ata {ata.id}: {e}")
        buffer.close()
        # Relança a exceção para ser tratada na view
        raise Exception(f"Erro interno ao gerar PDF: {e}") from e