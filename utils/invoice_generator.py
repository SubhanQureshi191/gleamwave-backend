# utils/invoice_generator.py

import os
import uuid
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import requests
from io import BytesIO
import os


class InvoiceGenerator:
    """Generate PDF invoices for orders"""

    INVOICE_DIR = "invoices"

    # Half A4 page size (portrait)
    PAGE_WIDTH = A4[0]  # 210mm
    PAGE_HEIGHT = A4[1] / 2  # 148.5mm (half of A4)

    @staticmethod
    def ensure_invoice_dir():
        """Create invoice directory if it doesn't exist"""
        if not os.path.exists(InvoiceGenerator.INVOICE_DIR):
            os.makedirs(InvoiceGenerator.INVOICE_DIR)

    @staticmethod
    def generate_invoice(order, order_items, user):
        """
        Generate PDF invoice for an order - Half Page (Saves printing cost)

        Args:
            order: Order object
            order_items: List of order items (dict with product_name, quantity, price)
            user: User object

        Returns:
            str: Path to generated PDF file
        """
        InvoiceGenerator.ensure_invoice_dir()

        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"invoice_{order.id}_{timestamp}.pdf"
        filepath = os.path.join(InvoiceGenerator.INVOICE_DIR, filename)

        # ─── CREATE PDF WITH HALF PAGE ───
        doc = SimpleDocTemplate(
            filepath,
            pagesize=(InvoiceGenerator.PAGE_WIDTH, InvoiceGenerator.PAGE_HEIGHT),
            topMargin=0.3 * inch,
            bottomMargin=0.3 * inch,
            leftMargin=0.4 * inch,
            rightMargin=0.4 * inch,
            title=f"Invoice #{order.id}",
            author="Gleamwave"
        )

        # ─── STYLES ────────────────────────────────────────────────
        styles = getSampleStyleSheet()

        # Custom styles - SMALLER for half page
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#4A2E22'),
            alignment=TA_CENTER,
            spaceAfter=1,
            fontName='Helvetica-Bold'
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#B8956A'),
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName='Helvetica'
        )

        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontSize=10,
            textColor=colors.HexColor('#4A2E22'),
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )

        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#6B4F3A'),
            fontName='Helvetica',
            leading=9
        )

        bold_style = ParagraphStyle(
            'Bold',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#4A2E22'),
            fontName='Helvetica-Bold',
            leading=9
        )

        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=6,
            textColor=colors.HexColor('#A08070'),
            fontName='Helvetica'
        )

        # ─── BUILD STORY ───────────────────────────────────────────
        story = []

        # ─── HEADER ────────────────────────────────────────────────
        story.append(Paragraph("gleamwave", title_style))
        story.append(Paragraph("✨ Premium Resin Artistry", subtitle_style))

        # Divider
        story.append(Spacer(1, 0.05 * inch))
        story.append(Paragraph("<hr color='#E8D9C0'/>", normal_style))
        story.append(Spacer(1, 0.05 * inch))

        # Invoice Title and Details - INLINE FORMAT
        invoice_title = Paragraph(
            f"""
            <font size="12" color="#4A2E22"><b>INVOICE</b></font>
            <font size="7" color="#6B4F3A">
            &nbsp;&nbsp;|&nbsp;&nbsp; # {order.id}
            &nbsp;&nbsp;|&nbsp;&nbsp; {order.created_at.strftime('%d %b %Y') if order.created_at else datetime.now().strftime('%d %b %Y')}
            </font>
            """,
            normal_style
        )
        story.append(invoice_title)
        story.append(Spacer(1, 0.08 * inch))

        # ─── ORDER STATUS ──────────────────────────────────────────
        status_color = {
            'confirmed': '#3B82F6',
            'shipped': '#8B5CF6',
            'delivered': '#10B981',
            'cancelled': '#EF4444',
            'pending': '#F59E0B'
        }.get(order.status, '#6B7280')

        story.append(Paragraph(
            f"""
            <font size="7" color="{status_color}">
            <b>Status: {order.status.upper()}</b>
            </font>
            """,
            normal_style
        ))
        story.append(Spacer(1, 0.08 * inch))

        # ─── CUSTOMER & PAYMENT INFO (SINGLE LINE) ──────────────────
        info_data = [
            [
                Paragraph(f"""
                    <b>Customer:</b> {order.shipping_name or user.name}<br/>
                    <font size="6" color="#6B4F3A">{order.shipping_phone or user.phone or 'N/A'}</font>
                    """, normal_style
                          ),
                Paragraph(f"""
                    <b>Payment:</b> {"COD" if order.payment_method == "cod" else "EasyPaisa"}
                    """, normal_style
                          )
            ]
        ]

        info_table = Table(info_data, colWidths=[3.2 * inch, 2.0 * inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FDF8F3')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F5EDE0')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.05 * inch))

        # ─── SHIPPING ADDRESS ──────────────────────────────────────
        if order.shipping_address:
            # Fix: Replace newlines with <br/> properly
            shipping_addr = order.shipping_address
            # Replace actual newline characters with <br/>
            shipping_addr = shipping_addr.replace('\n', '<br/>')
            # Also handle \r\n
            shipping_addr = shipping_addr.replace('\r\n', '<br/>')
            shipping_addr = shipping_addr.replace('\r', '<br/>')

            story.append(Paragraph(
                f"""
                <b>Address:</b> <font size="7" color="#6B4F3A">{shipping_addr}</font>
                """,
                normal_style
            ))
            story.append(Spacer(1, 0.05 * inch))

        # ─── ORDER NOTE ────────────────────────────────────────────
        if order.extra_note:
            story.append(Paragraph(
                f"""
                <font size="7" color="#6B4F3A">
                <b>Note:</b> "{order.extra_note}"
                </font>
                """,
                normal_style
            ))
            story.append(Spacer(1, 0.05 * inch))

        # ─── DIVIDER ───────────────────────────────────────────────
        story.append(Paragraph("<hr color='#F5EDE0'/>", normal_style))
        story.append(Spacer(1, 0.05 * inch))

        # ─── ORDER ITEMS TABLE ─────────────────────────────────────
        story.append(Paragraph("ITEMS", heading_style))
        story.append(Spacer(1, 0.03 * inch))

        # Table headers
        table_data = [
            [
                Paragraph("<b>#</b>", bold_style),
                Paragraph("<b>PRODUCT</b>", bold_style),
                Paragraph("<b>QTY</b>", bold_style),
                Paragraph("<b>PRICE</b>", bold_style),
                Paragraph("<b>TOTAL</b>", bold_style)
            ]
        ]

        # Table rows
        total_amount = 0
        for idx, item in enumerate(order_items, 1):
            item_total = item['price'] * item['quantity']
            total_amount += item_total

            # Truncate product name if too long
            product_name = item['product_name']
            if len(product_name) > 25:
                product_name = product_name[:22] + "..."

            table_data.append([
                Paragraph(str(idx), normal_style),
                Paragraph(product_name, normal_style),
                Paragraph(str(item['quantity']), normal_style),
                Paragraph(f"Rs.{item['price']:,.0f}", normal_style),
                Paragraph(f"Rs.{item_total:,.0f}", normal_style)
            ])

        # Create table with proper column widths
        items_table = Table(table_data, colWidths=[0.3 * inch, 2.5 * inch, 0.4 * inch, 0.9 * inch, 0.9 * inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6F4E37')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#E8D9C0')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#F5EDE0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FDF8F3')]),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.08 * inch))

        # ─── TOTALS ──────────────────────────────────────────────
        delivery_charges = order.delivery_charges or 300
        grand_total = total_amount + delivery_charges

        # Create totals table with proper alignment
        totals_data = [
            ["Subtotal:", f"Rs. {total_amount:,.0f}"],
            ["Delivery:", f"Rs. {delivery_charges:,.0f}"],
            ["GRAND TOTAL:", f"Rs. {grand_total:,.0f}"]
        ]

        totals_table = Table(totals_data, colWidths=[1.8 * inch, 1.8 * inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LINEABOVE', (0, 2), (-1, 2), 1.5, colors.HexColor('#4A2E22')),
            ('LINEBELOW', (0, 2), (-1, 2), 1.5, colors.HexColor('#4A2E22')),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#4A2E22')),
            ('FONTSIZE', (0, 2), (-1, 2), 10),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ]))

        # Right align the totals table
        totals_container = Table([[totals_table]], colWidths=[5.0 * inch])
        totals_container.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(totals_container)

        # ─── FOOTER ──────────────────────────────────────────────
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("<hr color='#F5EDE0'/>", normal_style))
        story.append(Spacer(1, 0.05 * inch))

        footer_text = """
        <font size="6" color="#A08070">
        Thank you! ✨ Made with Love in Pakistan
        </font>
        """
        story.append(Paragraph(footer_text, normal_style))

        # ─── BUILD PDF ───────────────────────────────────────────
        try:
            doc.build(story)
            print(f"✅ Invoice generated (Half Page): {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Error building PDF: {e}")
            # Try building with less content if it fails
            try:
                doc.build(story[:-2])
                return filepath
            except Exception as e2:
                print(f"❌ Even simpler build failed: {e2}")
                return None

    @staticmethod
    def get_invoice_path(order_id):
        """Get the latest invoice path for an order"""
        InvoiceGenerator.ensure_invoice_dir()

        import glob
        pattern = f"invoice_{order_id}_*.pdf"
        files = glob.glob(os.path.join(InvoiceGenerator.INVOICE_DIR, pattern))

        if files:
            return sorted(files)[-1]  # Return latest
        return None

    @staticmethod
    def delete_old_invoices(order_id=None, days=30):
        """Delete invoices older than specified days"""
        import glob
        import time

        InvoiceGenerator.ensure_invoice_dir()

        pattern = f"invoice_{order_id}_*.pdf" if order_id else "invoice_*.pdf"
        files = glob.glob(os.path.join(InvoiceGenerator.INVOICE_DIR, pattern))

        deleted = 0
        current_time = time.time()
        for filepath in files:
            if os.path.getctime(filepath) < current_time - (days * 24 * 60 * 60):
                try:
                    os.remove(filepath)
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting {filepath}: {e}")

        print(f"Deleted {deleted} old invoices")
        return deleted