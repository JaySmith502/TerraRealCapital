import re
from dataclasses import dataclass

_H = re.compile(r"^##\s+(.*)$", re.M)

@dataclass
class Section:
    title: str
    body: str

def split_sections(md: str) -> tuple[str, list[Section]]:
    matches = list(_H.finditer(md))
    if not matches:
        return md, []
    preamble = md[: matches[0].start()]
    sections: list[Section] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[m.end(): end].lstrip("\n").rstrip()
        sections.append(Section(title=m.group(1).strip(), body=body))
    return preamble, sections

def section_titles(md: str) -> list[str]:
    return [s.title for s in split_sections(md)[1]]

def splice_section(md: str, title: str, new_body: str) -> str:
    preamble, sections = split_sections(md)
    if title not in {s.title for s in sections}:
        raise KeyError(title)
    rebuilt = [preamble.rstrip()]
    for s in sections:
        body = new_body.strip() if s.title == title else s.body
        rebuilt.append(f"## {s.title}\n\n{body}")
    return "\n\n".join(part for part in rebuilt if part).strip() + "\n"
