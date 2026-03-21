#!/usr/bin/env python3
"""Quick PDF analyzer for Tibia bot research paper"""

import sys
from pathlib import Path

pdf_path = Path(r'C:\Users\zycie\CTOAi\docs\Tibia_AI_Bot_Research.pdf')

try:
    import pdfplumber
    print("[+] Analyzing PDF with pdfplumber...")
    with pdfplumber.open(str(pdf_path)) as pdf:
        print(f"[PDF] {len(pdf.pages)} pages found\n")
        
        # Save full text
        all_text = ""
        for page in pdf.pages:
            all_text += page.extract_text() + "\n"
        
        out_txt = Path(pdf_path).parent / "paper_extracted.txt"
        out_txt.write_text(all_text, encoding='utf-8')
        print(f"[+] Full text saved to: {out_txt}\n")
        
        # Print key sections
        for i in range(min(6, len(pdf.pages))):
            text = pdf.pages[i].extract_text()
            print(f"\n{'='*70}\n[PAGE {i+1}]\n{'='*70}\n")
            print(text[:1500])
            print("\n[...more content...]\n")
            
        # Search for methodology/architecture sections
        print("\n\n" + "="*70)
        print("SEARCHING FOR KEY SECTIONS...")
        print("="*70)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text().lower()
            if any(keyword in text for keyword in ['architecture', 'methodology', 'implementation', 'algorithm', 'results', 'conclusion']):
                print(f"[FOUND] Page {i+1} contains architecture/methodology info")
                
except Exception as e:
    print(f"[-] Error reading PDF: {e}")
    print("\nTrying to extract metadata...")
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            print(f"Pages: {len(pdf.pages)}")
            if hasattr(pdf, 'metadata'):
                print(f"Metadata: {pdf.metadata}")
    except:
        pass
    sys.exit(1)
