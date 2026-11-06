import os
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from config import BASE_DIR, UPLOAD_DIR

def generate_coi_docx(coi_data: dict, output_filename: str = "Court_of_Inquiry_Proceedings.docx") -> str:
    """
    Generates a formal, military statutory DOCX document strictly adhering to
    the new 'In lieu of IAFD - 931' format from coi.PDF.
    """
    doc = Document()
    
    # Page Margins (Standard military format: 1 inch margins)
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    header = coi_data.get("header", {})
    comp = header.get("composition_of_court", [])
    
    # -------------------------------------------------------------
    # PAGE 1: TITLE & PROCEEDINGS OF COURT (In lieu of IAFD - 931)
    # -------------------------------------------------------------
    p_iafd = doc.add_paragraph()
    p_iafd.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_iafd = p_iafd.add_run("In lieu of IAFD – 931")
    run_iafd.bold = True
    run_iafd.underline = True
    run_iafd.font.size = Pt(11)

    doc.add_paragraph()  # Spacing

    # Assembly Details Block
    table_assembly = doc.add_table(rows=5, cols=2)
    table_assembly.autofit = True
    col_widths = [Inches(2.2), Inches(4.3)]
    
    rows_data = [
        ("Proceed of", f": {header.get('proceed_of', 'Court of Inquiry')}"),
        ("Assembled at", f": {header.get('assembled_at', 'Station HQ, RTR Marg, New Delhi-10')}"),
        ("On time", f": {header.get('on_time', '27 Jul 2026 and subsequent days.')}"),
        ("By order of", f": {header.get('by_order_of', 'Part I Order dt August 2026')}"),
        ("For the purpose of", f": {header.get('for_the_purpose_of', 'To investigate into circumstances.')}")
    ]
    
    for row_idx, (label, val) in enumerate(rows_data):
        row = table_assembly.rows[row_idx]
        row.cells[0].width = col_widths[0]
        row.cells[1].width = col_widths[1]
        
        p0 = row.cells[0].paragraphs[0]
        r0 = p0.add_run(label)
        r0.bold = True
        r0.font.size = Pt(11)
        
        p1 = row.cells[1].paragraphs[0]
        r1 = p1.add_run(val)
        r1.font.size = Pt(11)

    doc.add_paragraph()  # Spacing

    # Composition of Court Block
    po_text = "JC-XXXXX Rank XXXXXX"
    mem1_text = "JC-XXXXX Rank XXXXXX"
    mem2_text = "No-XXXXXX Rank XXXXXXX"
    
    for m in comp:
        role = str(m.get("role", "")).lower()
        rname = m.get("rank_name") or m.get("name", "")
        if "presid" in role:
            po_text = rname
        elif "1" in role or "member 1" in role:
            mem1_text = rname
        elif "2" in role or "member 2" in role:
            mem2_text = rname

    table_comp = doc.add_table(rows=3, cols=2)
    col_widths_c = [Inches(2.2), Inches(4.3)]
    comp_rows = [
        ("Presiding Officer", f":   {po_text}"),
        ("Members", f"1.  {mem1_text}"),
        ("", f"2.  {mem2_text}")
    ]
    for row_idx, (label, val) in enumerate(comp_rows):
        row = table_comp.rows[row_idx]
        row.cells[0].width = col_widths_c[0]
        row.cells[1].width = col_widths_c[1]
        p0 = row.cells[0].paragraphs[0]
        r0 = p0.add_run(label)
        r0.bold = True
        r0.font.size = Pt(11)
        p1 = row.cells[1].paragraphs[0]
        r1 = p1.add_run(val)
        r1.font.size = Pt(11)

    doc.add_paragraph()  # Spacing

    # Opening Assembly Declaration Paragraph
    p_decl = doc.add_paragraph()
    p_decl.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_decl = p_decl.add_run(header.get("assembly_declaration", "The court of inquiry having assembled pursuant to order proceeded to investigate the circumstances as mandated."))
    r_decl.font.size = Pt(11)

    # -------------------------------------------------------------
    # PAGES 2+: WITNESS PROCEEDINGS (Q&A Format)
    # -------------------------------------------------------------
    witness_proceedings = coi_data.get("witness_proceedings", [])
    for w_idx, wit in enumerate(witness_proceedings):
        doc.add_page_break()
        
        # Witness Title (e.g. Witness No 1)
        p_wit_title = doc.add_paragraph()
        p_wit_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_wt = p_wit_title.add_run(wit.get("title", f"Witness No {w_idx+1}"))
        r_wt.bold = True
        r_wt.font.size = Pt(12)

        # Statutory Warning
        p_warn = doc.add_paragraph()
        p_warn.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_warn.add_run(wit.get("warning_declaration", "1. I, having been duly warned state the following:-")).font.size = Pt(11)

        # Posting and Duties
        p_post = doc.add_paragraph()
        p_post.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_post.add_run(wit.get("posting_and_duties", "2. I have been posted and performing authorized duties.")).font.size = Pt(11)

        # Narrative Statement
        p_narr = doc.add_paragraph()
        p_narr.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_narr.add_run(wit.get("narrative_statement", "3. On the date of occurrence, while proceeding for duty, the incident occurred.")).font.size = Pt(11)

        doc.add_paragraph()

        # Heading: Question by the Court
        p_qhead = doc.add_paragraph()
        r_qh = p_qhead.add_run("Question by the Court")
        r_qh.bold = True
        r_qh.font.size = Pt(11)

        # Q&A List
        qa_list = wit.get("questions_by_court", [])
        for item in qa_list:
            q_text = item.get("q", "")
            ans_text = item.get("ans", "")
            
            p_q = doc.add_paragraph()
            r_q = p_q.add_run(q_text)
            r_q.bold = True
            r_q.font.size = Pt(11)
            
            p_a = doc.add_paragraph()
            r_a = p_a.add_run(ans_text)
            r_a.font.size = Pt(11)

        doc.add_paragraph()

        # Closing Affirmation
        p_aff = doc.add_paragraph()
        p_aff.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_aff = p_aff.add_run(wit.get("closing_affirmation", "The above statement has been read to me in the language I understand and I sign it as correct."))
        r_aff.font.size = Pt(11)

        doc.add_paragraph()
        doc.add_paragraph()

        # Signatures Line (Presiding Officer on left, Witness on right)
        table_sig = doc.add_table(rows=1, cols=2)
        table_sig.autofit = True
        p_po_sig = table_sig.rows[0].cells[0].paragraphs[0]
        r_pos = p_po_sig.add_run(f"Presiding Officer: {po_text}")
        r_pos.font.size = Pt(10)
        
        p_wit_sig = table_sig.rows[0].cells[1].paragraphs[0]
        p_wit_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_ws = p_wit_sig.add_run(wit.get("witness_sign", "(Signature of Witness)"))
        r_ws.font.size = Pt(10)

    # -------------------------------------------------------------
    # PAGE: FINDING OF THE COURT
    # -------------------------------------------------------------
    doc.add_page_break()
    p_find_title = doc.add_paragraph()
    p_find_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ft = p_find_title.add_run("FINDING OF THE COURT")
    r_ft.bold = True
    r_ft.font.size = Pt(13)

    findings = coi_data.get("findings_of_the_court", [])
    for f in findings:
        p_f = doc.add_paragraph()
        p_f.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_f = p_f.add_run(f)
        r_f.font.size = Pt(11)

    doc.add_paragraph()
    doc.add_paragraph()

    # Signatures for Findings
    p_sig_title = doc.add_paragraph()
    table_f_sig = doc.add_table(rows=3, cols=2)
    table_f_sig.rows[0].cells[0].paragraphs[0].add_run("Presiding Officer :").bold = True
    table_f_sig.rows[0].cells[1].paragraphs[0].add_run(f"_______________________\n({po_text})")
    
    table_f_sig.rows[1].cells[0].paragraphs[0].add_run("Members 1.        :").bold = True
    table_f_sig.rows[1].cells[1].paragraphs[0].add_run(f"_______________________\n({mem1_text})")
    
    table_f_sig.rows[2].cells[0].paragraphs[0].add_run("        2.        :").bold = True
    table_f_sig.rows[2].cells[1].paragraphs[0].add_run(f"_______________________\n({mem2_text})")

    # -------------------------------------------------------------
    # PAGE: OPINION OF THE COURT
    # -------------------------------------------------------------
    doc.add_page_break()
    p_op_title = doc.add_paragraph()
    p_op_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ot = p_op_title.add_run("OPINION OF THE COURT")
    r_ot.bold = True
    r_ot.font.size = Pt(13)

    opinions = coi_data.get("opinion_of_the_court", [])
    for op in opinions:
        p_op = doc.add_paragraph()
        p_op.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_op = p_op.add_run(op)
        r_op.font.size = Pt(11)

    doc.add_paragraph()
    doc.add_paragraph()

    # Signatures for Opinion
    table_op_sig = doc.add_table(rows=3, cols=2)
    table_op_sig.rows[0].cells[0].paragraphs[0].add_run("Presiding Officer :").bold = True
    table_op_sig.rows[0].cells[1].paragraphs[0].add_run(f"_______________________\n({po_text})")
    
    table_op_sig.rows[1].cells[0].paragraphs[0].add_run("Members 1.        :").bold = True
    table_op_sig.rows[1].cells[1].paragraphs[0].add_run(f"_______________________\n({mem1_text})")
    
    table_op_sig.rows[2].cells[0].paragraphs[0].add_run("        2.        :").bold = True
    table_op_sig.rows[2].cells[1].paragraphs[0].add_run(f"_______________________\n({mem2_text})")

    # -------------------------------------------------------------
    # PAGE: REMARKS OF CONVENING AUTHORITY / OC
    # -------------------------------------------------------------
    doc.add_page_break()
    remarks = coi_data.get("remarks_of_convening_authority", {})
    rem_title = remarks.get("title", "REMARKS OF CONVENING AUTHORITY ON THE COURT OF INQUIRY")
    
    p_rem_title = doc.add_paragraph()
    p_rem_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_rt = p_rem_title.add_run(rem_title)
    r_rt.bold = True
    r_rt.font.size = Pt(12)

    rem_points = remarks.get("points", [])
    for pt in rem_points:
        p_pt = doc.add_paragraph()
        p_pt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_pt = p_pt.add_run(pt)
        r_pt.font.size = Pt(11)

    doc.add_paragraph()
    doc.add_paragraph()

    # Station & Date
    p_st = doc.add_paragraph()
    p_st.add_run(f"{remarks.get('station', 'Station: Delhi Cantt-10')}\n")
    p_st.add_run(f"{remarks.get('date', 'Date : August 2026')}")

    # Save to disk
    out_dir = UPLOAD_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_filename

    doc.save(str(out_path))
    return str(out_path)
