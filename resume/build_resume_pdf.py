from pathlib import Path
import re

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "yuchen-liu-resume.pdf"

PAGE_W, PAGE_H = letter
LEFT, RIGHT = 45, PAGE_W - 45
TOP = PAGE_H - 45

INK = colors.HexColor("#171717")
MUTED = colors.HexColor("#5a5a55")
RULE = colors.HexColor("#b8b8b0")
LINK = colors.HexColor("#0645ad")

AVENIR_NEXT = "/System/Library/Fonts/Avenir Next.ttc"


def register_fonts():
    pdfmetrics.registerFont(TTFont("AvenirNext", AVENIR_NEXT, subfontIndex=7))
    pdfmetrics.registerFont(TTFont("AvenirNext-Bold", AVENIR_NEXT, subfontIndex=0))
    pdfmetrics.registerFont(TTFont("AvenirNext-Medium", AVENIR_NEXT, subfontIndex=5))


def width(text, font="AvenirNext", size=9.0):
    return stringWidth(text, font, size)


def wrap(text, max_width, font="AvenirNext", size=9.0):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        trial = word if not line else f"{line} {word}"
        if width(trial, font, size) <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def marked_tokens(text, base_font="AvenirNext", bold_font="AvenirNext-Bold"):
    tokens = []
    bold = False
    for part in text.split("**"):
        font = bold_font if bold else base_font
        for token in re.findall(r"\s+|\S+", part):
            tokens.append((token, font))
        bold = not bold
    return tokens


def wrap_marked(text, max_width, size=9.0):
    lines = []
    current = []
    current_width = 0
    for raw_token, font in marked_tokens(text):
        token = raw_token if current else raw_token.lstrip()
        if not token:
            continue
        if token.isspace():
            current.append((token, font))
            current_width += width(token, font, size)
            continue
        token_width = width(token, font, size)
        if current and current_width + token_width > max_width:
            lines.append(current)
            token = raw_token.lstrip()
            current = [(token, font)]
            current_width = width(token, font, size)
        else:
            current.append((token, font))
            current_width += token_width
    if current:
        lines.append(current)
    return lines


class ResumeCanvas:
    def __init__(self, path):
        self.c = canvas.Canvas(str(path), pagesize=letter)
        self.y = TOP

    def center(self, text, font="AvenirNext", size=9, color=INK):
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        self.c.drawCentredString(PAGE_W / 2, self.y, text)

    def center_links(self, parts, size=9.0):
        total = sum(width(text, "AvenirNext", size) for text, _, _ in parts)
        x = (PAGE_W - total) / 2
        self.c.setFont("AvenirNext", size)
        for text, is_link, url in parts:
            part_w = width(text, "AvenirNext", size)
            self.c.setFillColor(LINK if is_link else MUTED)
            self.c.drawString(x, self.y, text)
            if is_link:
                self.c.linkURL(url, (x, self.y - 2, x + part_w, self.y + size + 1), relative=0)
            x += part_w

    def section(self, title):
        self.y -= 12.7
        self.c.setFont("AvenirNext-Bold", 12.9)
        self.c.setFillColor(INK)
        self.c.drawString(LEFT, self.y, title.upper())
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.65)
        self.c.line(LEFT, self.y - 4.5, RIGHT, self.y - 4.5)
        self.y -= 15.7

    def plain(self, text, size=9.0, leading=10.2, left=LEFT, font="AvenirNext", color=INK):
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        lines = wrap(text, RIGHT - left, font=font, size=size)
        for i, line in enumerate(lines):
            self.c.drawString(left, self.y - i * leading, line)
        self.y -= len(lines) * leading + 1.8

    def marked_text(self, text, left, size=9.0, leading=10.25, max_width=None):
        lines = wrap_marked(text, max_width or RIGHT - left, size=size)
        self.c.setFillColor(INK)
        for i, line in enumerate(lines):
            x = left
            y = self.y - i * leading
            for token, font in line:
                self.c.setFont(font, size)
                self.c.drawString(x, y, token)
                x += width(token, font, size)
        self.y -= len(lines) * leading + 1.4

    def bullet(self, text, size=9.0, leading=10.25):
        indent = 15
        self.c.setFillColor(INK)
        self.c.circle(LEFT + 5, self.y + 2.2, 1.1, fill=1, stroke=0)
        self.marked_text(text, LEFT + indent, size=size, leading=leading, max_width=RIGHT - LEFT - indent)

    def role(self, title, org, dates, location):
        self.c.setFont("AvenirNext-Bold", 9.55)
        self.c.setFillColor(INK)
        self.c.drawString(LEFT, self.y, title)

        right = f"{dates} | {location}"
        self.c.setFont("AvenirNext-Medium", 9.15)
        self.c.setFillColor(MUTED)
        self.c.drawRightString(RIGHT, self.y, right)

        org_x = LEFT + width(title, "AvenirNext-Bold", 9.55) + 7
        max_org_right = RIGHT - width(right, "AvenirNext-Medium", 9.15) - 12
        org_text = f"| {org}"
        if org_x + width(org_text, "AvenirNext-Medium", 9.15) < max_org_right:
            self.c.drawString(org_x, self.y, org_text)
        self.y -= 11.1

    def project(self, name, url):
        self.c.setFont("AvenirNext-Bold", 9.3)
        self.c.setFillColor(LINK)
        self.c.drawString(LEFT, self.y, name)
        link_w = width(name, "AvenirNext-Bold", 9.3)
        self.c.linkURL(url, (LEFT, self.y - 2, LEFT + link_w, self.y + 10), relative=0)
        self.y -= 10.1

    def paper(self, title, venue, url, lines):
        self.c.setFont("AvenirNext-Bold", 9.15)
        self.c.setFillColor(LINK)
        self.c.drawString(LEFT, self.y, title)
        title_w = width(title, "AvenirNext-Bold", 9.15)
        self.c.linkURL(url, (LEFT, self.y - 2, LEFT + title_w, self.y + 10), relative=0)
        self.c.setFont("AvenirNext-Medium", 8.85)
        self.c.setFillColor(MUTED)
        self.c.drawRightString(RIGHT, self.y, venue)
        self.y -= 10.4
        for line in lines:
            self.bullet(line, size=8.65, leading=9.75)
        self.y -= 5.5

    def save(self):
        self.c.save()


def build():
    register_fonts()
    r = ResumeCanvas(OUT)

    r.c.setFont("AvenirNext-Bold", 27)
    r.c.setFillColor(INK)
    r.c.drawCentredString(PAGE_W / 2, r.y, "Yuchen Liu")
    r.y -= 18
    r.center_links(
        [
            ("Seattle, WA", False, None),
            ("  |  ", False, None),
            ("yql6113@gmail.com", True, "mailto:yql6113@gmail.com"),
            ("  |  ", False, None),
            ("814-876-2346", False, None),
            ("  |  ", False, None),
            ("github.com/Upcccccc", True, "https://github.com/Upcccccc"),
            ("  |  ", False, None),
            ("linkedin.com/in/liuyuche", True, "https://www.linkedin.com/in/liuyuche/"),
        ],
        size=8.95,
    )
    r.y -= 13.2
    r.center(
        "Search/AI infrastructure engineer building production-scale indexing, hybrid retrieval, and co-first-author LLM/mech interp research.",
        font="AvenirNext",
        size=8.45,
        color=MUTED,
    )
    r.y -= 9.0

    r.section("Education")
    for degree, school, gpa, date in [
        ("M.S. Computer Science", "University of Pennsylvania, Philadelphia", "GPA: 3.80/4.00", "May 2025"),
        ("B.S. Applied Economics", "Pennsylvania State University, State College", "GPA: 3.86/4.00", "May 2023"),
    ]:
        r.c.setFont("AvenirNext-Bold", 9.1)
        r.c.setFillColor(INK)
        r.c.drawString(LEFT, r.y, degree)
        r.c.setFont("AvenirNext", 9.0)
        r.c.drawString(LEFT + 139, r.y, school)
        r.c.drawString(RIGHT - 142, r.y, gpa)
        r.c.drawRightString(RIGHT, r.y, date)
        r.y -= 12.2

    r.section("Work Experience")
    r.role("Software Engineer, Search Infrastructure", "DoorDash", "Aug 2025 - Present", "Seattle, WA")
    for item in [
        "Owned core components of a **next-generation search ingestion platform**, re-architecting the indexing write path across **~40 production search stacks**, hundreds of sharded indexer instances, billions of indexed documents, and tens of TB of index storage.",
        "Designed a **streaming incremental-indexing framework** using **Kafka, Iceberg, Spark**, per-namespace watermarks, and exact consumer cutover offsets, sustaining millions of document updates per cycle while preventing missed or double-applied updates.",
        "Productionized a **Lucene-native hybrid retrieval layer** that fuses **BM25 keyword retrieval** with open-source dense embeddings into a single query plan, consolidating semantic search previously served through a standalone vector retrieval stack.",
        "Migrated **30+ production stacks** to modular **Jsonnet** configuration, eliminating **~56K lines** of duplicate config and reducing verification time by **~90%**; added pre-deployment validators and **Kyverno guardrails** to prevent capacity regressions.",
    ]:
        r.bullet(item)
    r.y -= 6.5

    r.role("Software Engineering Intern", "Penn Medicine TissueLab", "Oct 2024 - May 2025", "Philadelphia, PA")
    for item in [
        "Built a **Python/FastAPI ML orchestration platform** for **PyTorch-based medical-imaging workflows**, enabling natural-language-driven segmentation and classification tasks.",
        "Implemented an event-driven **DAG workflow engine** for async task execution, processing **10K+ pathology images daily** and streaming **12M+ imaging events** through WebSockets.",
    ]:
        r.bullet(item)
    r.y -= 6.5

    r.section("Selected AI Systems Projects")
    projects = [
        (
            "nanoRL",
            "https://github.com/RiddleHe/nanochat",
            "Led an open-source **RL training framework** inside nanochat for objective design, rollout experiments, reproducible ablations, and **vLLM-backed inference serving**.",
        ),
        (
            "nanochat",
            "https://github.com/RiddleHe/nanochat",
            "Built a hackable pretraining and chat stack for architecture definition, **FLOP-controlled ablations**, and reproducible LLM experiments.",
        ),
        (
            "llm-interp",
            "https://github.com/RiddleHe/llm-interp",
            "Authored reproducible interpretability scripts for model circuit research, including **attention-sink analysis** and **LLM decode indeterminism** reproductions.",
        ),
    ]
    for name, url, desc in projects:
        r.project(name, url)
        r.bullet(desc)
        r.y -= 4.3

    r.section("Research")
    r.paper(
        "Do Value Vectors in Deep Layers Need Context from the Residual Stream?",
        "EMNLP 2026, Main Conference",
        "https://arxiv.org/abs/2606.02780",
        [
            "Co-first author; co-developed the central research hypothesis that late-layer Transformer value vectors may encode **context-free token information**, challenging the assumption that deep-layer attention values require residual-stream context.",
            "Co-designed controlled architecture experiments and ablations across **135M/780M models** and **21 benchmarks**; proposed **Bank of Values**, a learned value-vector table that removes the **V-cache** while preserving downstream quality.",
        ],
    )
    r.paper(
        "Vision Language Models Cannot Plan, but Can They Formalize?",
        "ECCV 2026, under review",
        "https://arxiv.org/abs/2509.21576",
        [
            "Co-designed experiments testing whether **VLMs** can translate visual planning tasks into solver-executable **PDDL problem files**, separating perception, formalization, and planning ability.",
            "Built evaluation pipelines for visual state extraction, goal/constraint formalization, and solver-based correctness checking.",
        ],
    )
    r.paper(
        "A co-evolving agentic AI system for medical imaging analysis",
        "Under review",
        "https://arxiv.org/abs/2509.20279",
        [
            "Co-developed agentic medical-imaging workflows for **tool selection, planning, knowledge updates**, and human-in-the-loop co-evolution.",
        ],
    )

    r.section("Skills")
    for skill_line in [
        "**Languages:** Python, Kotlin, Java, C++, JavaScript",
        "**ML/AI:** PyTorch, vLLM, Transformers, RL, LLM evaluation, mechanistic interpretability",
        "**Search/Data Infra:** Lucene, Kafka, Spark, Iceberg, Delta Lake, Redis, FastAPI",
        "**Systems/Cloud:** Docker, Kubernetes, AWS, Spring Boot",
    ]:
        r.marked_text(skill_line, LEFT, size=8.35, leading=9.35)

    if r.y < 38:
        raise RuntimeError(f"Resume overflowed: final y={r.y:.1f}")
    r.save()
    reader = PdfReader(str(OUT))
    if len(reader.pages) != 1:
        raise RuntimeError(f"Expected one page, got {len(reader.pages)}")
    print(OUT)


if __name__ == "__main__":
    build()
