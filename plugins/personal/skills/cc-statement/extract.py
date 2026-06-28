#!/usr/bin/env python3
"""
Extract raw transactions from an Axis Bank credit card PDF statement.
Usage: python extract.py <pdf_path> <password>
Output: JSON to stdout — {transactions: [{date, description, amount, type}], pages, total_transactions}
"""
import sys
import json
import re
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: extract.py <pdf_path> <password>"}))
        sys.exit(1)

    pdf_path, password = sys.argv[1], sys.argv[2]

    try:
        from pypdf import PdfReader
    except ImportError:
        print(json.dumps({"error": "pypdf not installed. Run: pip install pypdf"}))
        sys.exit(1)

    try:
        r = PdfReader(pdf_path)
    except Exception as e:
        print(json.dumps({"error": f"Cannot open PDF: {e}"}))
        sys.exit(1)

    if r.is_encrypted:
        if r.decrypt(password) == 0:
            print(json.dumps({"error": "Wrong password"}))
            sys.exit(1)

    full_text = "\n".join(page.extract_text() or "" for page in r.pages)

    # Pattern: DD Mon 'YY  <description>  ₹ amount  Debit/Credit
    # Use a two-pass approach: find date anchors, then grab everything up to the amount+type
    date_re = re.compile(r"(\d{1,2}\s+\w{3}\s+'?\d{2,4})")
    amount_type_re = re.compile(r"[₹₹]\s*([\d,]+\.?\d*)\s+(Debit|Credit)")

    # Split text into segments starting at each date
    segments = []
    for m in date_re.finditer(full_text):
        segments.append((m.start(), m.group(1)))

    transactions = []
    for i, (start, date) in enumerate(segments):
        end = segments[i + 1][0] if i + 1 < len(segments) else len(full_text)
        chunk = full_text[start:end]

        m = amount_type_re.search(chunk)
        if not m:
            continue

        # Description = everything between the date and the ₹ sign
        desc_raw = chunk[len(date):m.start()].strip()
        desc = re.sub(r"\s+", " ", desc_raw).strip()
        amount = float(m.group(1).replace(",", ""))
        tx_type = m.group(2)

        # Skip header rows that accidentally match
        if not desc or desc.lower() in {"transaction details", "date"}:
            continue

        transactions.append({
            "date": date.strip(),
            "description": desc,
            "amount": amount,
            "type": tx_type
        })

    print(json.dumps({
        "transactions": transactions,
        "pages": len(r.pages),
        "total_transactions": len(transactions)
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
