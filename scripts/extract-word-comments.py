#!/usr/bin/env python3
"""Extract review comments from EDA-Microsegmentation.docx."""
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def text_of(el):
    parts = []
    for t in el.iter(f"{W}t"):
        if t.text:
            parts.append(t.text)
        if t.tail:
            parts.append(t.tail)
    return "".join(parts).strip()


def main():
    docx = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/EDA-Microsegmentation.docx")
    with zipfile.ZipFile(docx) as zf:
        comments_root = ET.fromstring(zf.read("word/comments.xml"))
        doc_root = ET.fromstring(zf.read("word/document.xml"))

    comments = {}
    for c in comments_root.findall(f"{W}comment"):
        cid = c.get(f"{W}id")
        comments[cid] = {
            "author": c.get(f"{W}author", ""),
            "date": c.get(f"{W}date", ""),
            "body": text_of(c),
        }

    body = doc_root.find(f"{W}body")
    results = []
    current_para = []
    active_comments = {}

    for elem in body.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "commentRangeStart":
            cid = elem.get(f"{W}id")
            anchor = " ".join(current_para).strip()
            if len(anchor) > 150:
                anchor = "..." + anchor[-150:]
            active_comments[cid] = anchor
        elif tag == "commentReference":
            cid = elem.get(f"{W}id")
            if cid in comments:
                results.append(
                    {
                        "id": cid,
                        "anchor": active_comments.get(cid, ""),
                        "author": comments[cid]["author"],
                        "date": comments[cid]["date"],
                        "comment": comments[cid]["body"],
                    }
                )
        elif tag == "p":
            current_para = []
        elif tag == "t" and elem.text:
            current_para.append(elem.text)

    print(f"Total comments: {len(results)}\n")
    for i, r in enumerate(results, 1):
        print(f"--- Comment {i} (id={r['id']}) ---")
        print(f"Author: {r['author']}  Date: {r['date']}")
        if r["anchor"]:
            print(f"Anchor: {r['anchor']}")
        print(f"Comment: {r['comment']}")
        print()


if __name__ == "__main__":
    main()
