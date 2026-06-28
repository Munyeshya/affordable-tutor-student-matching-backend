from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "diagram_exports"
OUT_DIR.mkdir(exist_ok=True)

A4_W = 2480
A4_H = 3508
MARGIN = 130
TITLE_H = 150
PAGE_BG = "white"
BOX_FILL = "white"
BOX_OUTLINE = "black"
TEXT_COLOR = "black"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        (r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        (r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


TITLE_FONT = load_font(44, bold=True)
SECTION_FONT = load_font(28, bold=True)
BOX_FONT = load_font(24, bold=False)
SMALL_FONT = load_font(20, bold=False)
TINY_FONT = load_font(18, bold=False)


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            lines.append("")
            continue
        words = raw_line.split()
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if text_size(draw, candidate, font)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


@dataclass
class Box:
    x: int
    y: int
    w: int
    h: int
    text: str
    font: ImageFont.ImageFont = BOX_FONT
    fill: str = BOX_FILL
    outline: str = BOX_OUTLINE
    radius: int = 18
    align: str = "center"


@dataclass
class Edge:
    start: tuple[int, int]
    end: tuple[int, int]
    via: list[tuple[int, int]] | None = None
    width: int = 3


def draw_title(draw: ImageDraw.ImageDraw, title: str, subtitle: str | None = None):
    tw, th = text_size(draw, title, TITLE_FONT)
    draw.text(((A4_W - tw) // 2, 40), title, fill=TEXT_COLOR, font=TITLE_FONT)
    if subtitle:
        sw, sh = text_size(draw, subtitle, SMALL_FONT)
        draw.text(((A4_W - sw) // 2, 40 + th + 10), subtitle, fill=TEXT_COLOR, font=SMALL_FONT)


def draw_box(draw: ImageDraw.ImageDraw, box: Box):
    draw.rounded_rectangle((box.x, box.y, box.x + box.w, box.y + box.h), radius=box.radius, fill=box.fill, outline=box.outline, width=3)
    max_width = box.w - 24
    lines = wrap_text(draw, box.text, box.font, max_width)
    line_gap = 6
    line_heights = [text_size(draw, line or " ", box.font)[1] for line in lines]
    total_height = sum(line_heights) + line_gap * max(0, len(lines) - 1)
    y = box.y + max(12, (box.h - total_height) // 2)
    for line, lh in zip(lines, line_heights):
        lw = text_size(draw, line, box.font)[0]
        if box.align == "left":
            x = box.x + 12
        else:
            x = box.x + (box.w - lw) // 2
        draw.text((x, y), line, fill=TEXT_COLOR, font=box.font)
        y += lh + line_gap


def draw_arrow(draw: ImageDraw.ImageDraw, edge: Edge):
    points = [edge.start]
    if edge.via:
        points.extend(edge.via)
    points.append(edge.end)
    draw.line(points, fill=TEXT_COLOR, width=edge.width)
    p1 = points[-2]
    p2 = points[-1]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux = dx / length
    uy = dy / length
    arrow_len = 18
    arrow_w = 10
    left = (p2[0] - ux * arrow_len - uy * arrow_w, p2[1] - uy * arrow_len + ux * arrow_w)
    right = (p2[0] - ux * arrow_len + uy * arrow_w, p2[1] - uy * arrow_len - ux * arrow_w)
    draw.polygon([p2, left, right], fill=TEXT_COLOR)


def new_page() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (A4_W, A4_H), PAGE_BG)
    return img, ImageDraw.Draw(img)


def export_page(filename: str, draw_fn) -> tuple[Path, Image.Image]:
    img, draw = new_page()
    draw_fn(draw)
    png_path = OUT_DIR / f"{filename}.png"
    pdf_path = OUT_DIR / f"{filename}.pdf"
    img.save(png_path)
    img.save(pdf_path, "PDF", resolution=300.0)
    return pdf_path, img


def save_combined_pdf(images: Sequence[Image.Image]):
    first, rest = images[0], images[1:]
    first.save(OUT_DIR / "all-diagrams.pdf", "PDF", resolution=300.0, save_all=True, append_images=rest)


def functional_diagram(draw: ImageDraw.ImageDraw):
    draw_title(draw, "Affordable Tutor-Student Matching Platform", "Functional Diagram")
    boxes = [
        Box(1020, 150, 440, 90, "Loading Page", font=SECTION_FONT),
        Box(110, 370, 520, 130, "Public Portal", font=SECTION_FONT),
        Box(1850, 370, 480, 130, "Login and Authentication", font=SECTION_FONT),
        Box(520, 620, 620, 170, "Role-Based Dashboard Access", font=SECTION_FONT),
        Box(1460, 620, 700, 170, "System Authentication and Validation", font=SECTION_FONT),
        Box(120, 900, 500, 200, "Student Functions\nSearch tutors by price and subject\nBook sessions\nPay\nReview", font=SMALL_FONT),
        Box(700, 900, 500, 200, "Tutor Functions\nProfile\nDocuments\nAvailability\nCourses and Lessons", font=SMALL_FONT),
        Box(1280, 900, 500, 200, "Parent Functions\nLink student\nBook on behalf\nMonitor learning", font=SMALL_FONT),
        Box(1860, 900, 500, 200, "Admin Functions\nVerify tutors\nModerate courses\nResolve disputes\nView analytics", font=SMALL_FONT),
        Box(140, 1270, 500, 120, "Login Successful", font=SECTION_FONT),
        Box(720, 1270, 500, 120, "Login Failed", font=SECTION_FONT),
        Box(1280, 1270, 500, 120, "Error Message and Retry", font=SECTION_FONT),
        Box(1880, 1270, 470, 120, "Logout", font=SECTION_FONT),
        Box(820, 1550, 860, 140, "Marketplace Matching, Booking, Payments, Messaging, Reviews, and Analytics", font=SECTION_FONT),
    ]
    for box in boxes:
        draw_box(draw, box)

    edges = [
        Edge((1240, 240), (370, 370)),
        Edge((1240, 240), (2090, 370)),
        Edge((370, 500), (830, 620)),
        Edge((2090, 500), (1810, 620)),
        Edge((830, 790), (370, 900)),
        Edge((1000, 790), (950, 900)),
        Edge((1600, 790), (1530, 900)),
        Edge((2160, 790), (2110, 900)),
        Edge((370, 1100), (390, 1270)),
        Edge((950, 1100), (970, 1270)),
        Edge((1530, 1100), (1540, 1270)),
        Edge((2110, 1100), (2110, 1270)),
        Edge((1670, 1340), (1250, 1550)),
        Edge((390, 1390), (670, 1550)),
        Edge((970, 1390), (970, 1550)),
        Edge((1540, 1390), (1540, 1550)),
        Edge((2110, 1390), (1680, 1550)),
    ]
    for edge in edges:
        draw_arrow(draw, edge)


def level0_dfd(draw: ImageDraw.ImageDraw):
    draw_title(draw, "Level 0 DFD", "Context Diagram")
    center = Box(860, 1380, 760, 380, "Affordable Tutor-Student Matching Platform", font=SECTION_FONT)
    boxes = [
        Box(120, 420, 420, 140, "Student", font=SECTION_FONT),
        Box(120, 960, 420, 140, "Parent", font=SECTION_FONT),
        Box(120, 1500, 420, 140, "Tutor", font=SECTION_FONT),
        Box(1940, 420, 420, 140, "Admin", font=SECTION_FONT),
        Box(1940, 960, 420, 140, "Payment Gateway", font=SECTION_FONT),
        Box(1940, 1500, 420, 140, "Media Storage", font=SECTION_FONT),
        center,
    ]
    for box in boxes:
        draw_box(draw, box)
    edges = [
        Edge((540, 490), (860, 1540)),
        Edge((540, 1030), (860, 1630)),
        Edge((540, 1570), (860, 1710)),
        Edge((1940, 490), (1620, 1500)),
        Edge((1940, 1030), (1620, 1600)),
        Edge((1940, 1570), (1620, 1700)),
        Edge((1240, 1380), (330, 560)),
        Edge((1240, 1380), (330, 1100)),
        Edge((1240, 1380), (330, 1640)),
        Edge((1240, 1380), (2150, 560)),
        Edge((1240, 1380), (2150, 1100)),
        Edge((1240, 1380), (2150, 1640)),
    ]
    for edge in edges:
        draw_arrow(draw, edge)


def level1_dfd(draw: ImageDraw.ImageDraw):
    draw_title(draw, "Level 1 DFD", "Core backend processes and data stores")
    process_boxes = [
        Box(170, 330, 560, 140, "1. Authentication and Profiles", font=SECTION_FONT),
        Box(170, 560, 560, 140, "2. Tutor Verification and Setup", font=SECTION_FONT),
        Box(170, 790, 560, 140, "3. Affordability Search and Matching", font=SECTION_FONT),
        Box(170, 1020, 560, 140, "4. Availability and Bookings", font=SECTION_FONT),
        Box(170, 1250, 560, 140, "5. Course and Lesson Management", font=SECTION_FONT),
        Box(170, 1480, 560, 140, "6. Payments and Payouts", font=SECTION_FONT),
        Box(170, 1710, 560, 140, "7. Messaging, Reviews and Disputes", font=SECTION_FONT),
        Box(170, 1940, 560, 140, "8. Learning Impact and Analytics", font=SECTION_FONT),
    ]
    stores = [
        Box(1780, 330, 520, 100, "Users", font=SECTION_FONT),
        Box(1780, 470, 520, 100, "Tutor Profiles", font=SECTION_FONT),
        Box(1780, 610, 520, 100, "Verification Docs", font=SECTION_FONT),
        Box(1780, 750, 520, 100, "Subjects and TutorSubjects", font=SECTION_FONT),
        Box(1780, 890, 520, 100, "Availability Slots", font=SECTION_FONT),
        Box(1780, 1030, 520, 100, "Bookings", font=SECTION_FONT),
        Box(1780, 1170, 520, 100, "Courses and Lessons", font=SECTION_FONT),
        Box(1780, 1310, 520, 100, "Payments and Payouts", font=SECTION_FONT),
        Box(1780, 1450, 520, 100, "Messages, Reviews, Disputes", font=SECTION_FONT),
        Box(1780, 1590, 520, 100, "Assessments and Progress", font=SECTION_FONT),
        Box(1780, 1730, 520, 100, "Analytics Reports", font=SECTION_FONT),
    ]
    externals = [
        Box(760, 140, 420, 110, "Student", font=SECTION_FONT),
        Box(1230, 140, 420, 110, "Tutor", font=SECTION_FONT),
        Box(1700, 140, 420, 110, "Parent", font=SECTION_FONT),
        Box(2040, 140, 320, 110, "Admin", font=SECTION_FONT),
        Box(760, 2200, 420, 110, "Payment Gateway", font=SECTION_FONT),
        Box(1230, 2200, 420, 110, "Media Storage", font=SECTION_FONT),
    ]
    for box in externals + process_boxes + stores:
        draw_box(draw, box)

    edges = [
        Edge((1160, 195), (450, 330)),
        Edge((1440, 195), (450, 560)),
        Edge((1910, 195), (450, 790)),
        Edge((2180, 195), (450, 1020)),
        Edge((450, 470), (1780, 380)),
        Edge((450, 700), (1780, 520)),
        Edge((450, 930), (1780, 660)),
        Edge((450, 1160), (1780, 800)),
        Edge((450, 1390), (1780, 940)),
        Edge((450, 1620), (1780, 1080)),
        Edge((450, 1850), (1780, 1220)),
        Edge((450, 2080), (1780, 1360)),
        Edge((450, 2150), (1780, 1500)),
        Edge((1310, 2250), (1780, 1640)),
        Edge((980, 2250), (1780, 1780)),
        Edge((2040, 430), (2040, 470)),
        Edge((2040, 570), (2040, 610)),
        Edge((2040, 710), (2040, 750)),
        Edge((2040, 850), (2040, 890)),
        Edge((2040, 990), (2040, 1030)),
        Edge((2040, 1130), (2040, 1170)),
        Edge((2040, 1270), (2040, 1310)),
        Edge((2040, 1410), (2040, 1450)),
        Edge((2040, 1550), (2040, 1590)),
        Edge((2040, 1690), (2040, 1730)),
    ]
    for edge in edges:
        draw_arrow(draw, edge)


def level2_dfd(draw: ImageDraw.ImageDraw):
    draw_title(draw, "Level 2 DFD", "Booking and matching workflow breakdown")
    boxes = [
        Box(150, 330, 500, 110, "Student / Parent", font=SECTION_FONT),
        Box(930, 330, 620, 110, "3.1 Search Affordable Tutors", font=SECTION_FONT),
        Box(930, 500, 620, 110, "3.2 View Tutor Profile", font=SECTION_FONT),
        Box(930, 670, 620, 110, "3.3 Check Verification and Availability", font=SECTION_FONT),
        Box(930, 840, 620, 110, "3.4 Create Booking Request", font=SECTION_FONT),
        Box(930, 1010, 620, 110, "3.5 Validate Booking", font=SECTION_FONT),
        Box(930, 1180, 620, 110, "3.6 Tutor Accepts or Rejects", font=SECTION_FONT),
        Box(930, 1350, 620, 110, "3.7 Capture Payment", font=SECTION_FONT),
        Box(930, 1520, 620, 110, "3.8 Complete Session and Review", font=SECTION_FONT),
        Box(930, 1690, 620, 110, "3.9 Handle Disputes and Reporting", font=SECTION_FONT),
        Box(1760, 330, 560, 100, "Users", font=SECTION_FONT),
        Box(1760, 470, 560, 100, "Tutor Profiles", font=SECTION_FONT),
        Box(1760, 610, 560, 100, "Subjects and TutorSubjects", font=SECTION_FONT),
        Box(1760, 750, 560, 100, "Availability Slots", font=SECTION_FONT),
        Box(1760, 890, 560, 100, "Bookings", font=SECTION_FONT),
        Box(1760, 1030, 560, 100, "Payments", font=SECTION_FONT),
        Box(1760, 1170, 560, 100, "Notifications", font=SECTION_FONT),
        Box(1760, 1310, 560, 100, "Reviews and Disputes", font=SECTION_FONT),
        Box(1760, 1450, 560, 100, "Messages", font=SECTION_FONT),
        Box(1760, 1590, 560, 100, "Assessments and Progress", font=SECTION_FONT),
        Box(1760, 1730, 560, 100, "Analytics", font=SECTION_FONT),
        Box(150, 2020, 500, 110, "Tutor", font=SECTION_FONT),
        Box(710, 2020, 500, 110, "Parent", font=SECTION_FONT),
        Box(1270, 2020, 500, 110, "Admin", font=SECTION_FONT),
        Box(1830, 2020, 500, 110, "Payment Gateway", font=SECTION_FONT),
    ]
    for box in boxes:
        draw_box(draw, box)

    edges = [
        Edge((650, 385), (930, 385)),
        Edge((650, 385), (930, 555)),
        Edge((930, 725), (1550, 725)),
        Edge((930, 895), (1550, 895)),
        Edge((1550, 895), (930, 1065)),
        Edge((1550, 1065), (930, 1235)),
        Edge((1550, 1235), (930, 1405)),
        Edge((1550, 1405), (930, 1575)),
        Edge((1550, 1575), (930, 1745)),
        Edge((1550, 1745), (1760, 1180)),
        Edge((1550, 1745), (1760, 1320)),
        Edge((1550, 1745), (1760, 1460)),
        Edge((1550, 1745), (1760, 1600)),
        Edge((1550, 1745), (1760, 1740)),
        Edge((1850, 385), (1550, 385)),
        Edge((1850, 525), (1550, 525)),
        Edge((1850, 665), (1550, 665)),
        Edge((1850, 805), (1550, 805)),
        Edge((1850, 945), (1550, 945)),
        Edge((1850, 1085), (1550, 1085)),
        Edge((1850, 1225), (1550, 1225)),
        Edge((1850, 1365), (1550, 1365)),
        Edge((1850, 1505), (1550, 1505)),
        Edge((1850, 1645), (1550, 1645)),
        Edge((385, 2020), (1150, 1840)),
        Edge((970, 2020), (1150, 1840)),
        Edge((1530, 2020), (1150, 1840)),
        Edge((2080, 2020), (1550, 1390)),
    ]
    for edge in edges:
        draw_arrow(draw, edge)


def erd(draw: ImageDraw.ImageDraw):
    draw_title(draw, "Entity Relationship Diagram", "Affordable Tutor-Student Matching Platform")
    boxes = [
        Box(100, 250, 360, 140, "USER\nid PK\nemail\nrole", font=SMALL_FONT),
        Box(100, 450, 360, 180, "STUDENT_PROFILE\nid PK\nuser_id FK\nfull_name\nlevel\nbudget_min\nbudget_max", font=TINY_FONT),
        Box(100, 690, 360, 180, "PARENT_PROFILE\nid PK\nuser_id FK\nfull_name\nphone_number", font=TINY_FONT),
        Box(100, 930, 360, 180, "PARENT_STUDENT_LINK\nid PK\nparent_id FK\nstudent_id FK\nis_primary", font=TINY_FONT),
        Box(560, 250, 380, 160, "TUTOR_PROFILE\nid PK\nuser_id FK\nfull_name\nhourly_rate", font=TINY_FONT),
        Box(560, 480, 380, 180, "TUTOR_VERIFICATION\nid PK\ntutor_id FK\nstatus\nreviewed_by_id FK", font=TINY_FONT),
        Box(560, 720, 380, 160, "VERIFICATION_DOCUMENT\nid PK\nverification_id FK\ndoc_type\nfile", font=TINY_FONT),
        Box(560, 930, 380, 160, "TUTOR_AGREEMENT\nid PK\ntutor_id FK\nstatus\nsigned_file", font=TINY_FONT),
        Box(1040, 250, 380, 140, "SUBJECT\nid PK\nname", font=TINY_FONT),
        Box(1040, 450, 380, 180, "TUTOR_SUBJECT\nid PK\ntutor_id FK\nsubject_id FK\nlevel", font=TINY_FONT),
        Box(1040, 700, 380, 180, "COURSE\nid PK\ntutor_id FK\nsubject_id FK\nprice\nstatus", font=TINY_FONT),
        Box(1040, 940, 380, 180, "LESSON\nid PK\ncourse_id FK\ntitle\nvideo_file\nis_preview", font=TINY_FONT),
        Box(1520, 250, 380, 180, "AVAILABILITY_SLOT\nid PK\ntutor_id FK\nstart_datetime\nend_datetime", font=TINY_FONT),
        Box(1520, 490, 380, 180, "BOOKING\nid PK\nstudent_id FK\ntutor_id FK\nsubject_id FK\nstatus", font=TINY_FONT),
        Box(1520, 730, 380, 180, "PAYMENT\nid PK\nbooking_id FK\nstudent_id FK\ntutor_id FK\nstatus", font=TINY_FONT),
        Box(1520, 970, 380, 180, "REVIEW\nid PK\nbooking_id FK\nstudent_id FK\ntutor_id FK\nrating", font=TINY_FONT),
        Box(1960, 250, 380, 180, "DISPUTE\nid PK\nbooking_id FK\nreported_by_id FK\nstatus", font=TINY_FONT),
        Box(1960, 490, 380, 160, "CHAT_MESSAGE\nid PK\nbooking_id FK\nsender_id FK\nis_read", font=TINY_FONT),
        Box(1960, 720, 380, 180, "COURSE_PURCHASE\nid PK\nstudent_id FK\ncourse_id FK\nstatus", font=TINY_FONT),
        Box(1960, 960, 380, 180, "LESSON_PROGRESS\nid PK\nstudent_id FK\nlesson_id FK\ncompleted", font=TINY_FONT),
        Box(1960, 1200, 380, 180, "ASSESSMENT_RESULT_CONFIRMATION\nid PK\nstudent_id FK\nlesson_id FK\nimprovement", font=TINY_FONT),
    ]
    for box in boxes:
        draw_box(draw, box)

    edges = [
        Edge((460, 320), (100, 520)),
        Edge((460, 320), (100, 780)),
        Edge((280, 630), (280, 930)),
        Edge((460, 1000), (280, 1110)),
        Edge((460, 320), (560, 330)),
        Edge((760, 410), (760, 480)),
        Edge((760, 660), (760, 720)),
        Edge((760, 900), (760, 930)),
        Edge((940, 330), (1040, 320)),
        Edge((1230, 390), (1230, 450)),
        Edge((1230, 630), (1230, 700)),
        Edge((1230, 880), (1230, 940)),
        Edge((1420, 320), (1520, 340)),
        Edge((1420, 560), (1520, 570)),
        Edge((1420, 820), (1520, 810)),
        Edge((1420, 1060), (1520, 1050)),
        Edge((1900, 320), (1960, 340)),
        Edge((1900, 560), (1960, 570)),
        Edge((1900, 800), (1960, 810)),
        Edge((1900, 1040), (1960, 1050)),
        Edge((1900, 1280), (1960, 1280)),
        Edge((1220, 730), (1520, 610)),
        Edge((1220, 970), (1520, 850)),
        Edge((1220, 970), (1960, 840)),
    ]
    for edge in edges:
        draw_arrow(draw, edge)


def main():
    exports = [
        ("functional-diagram", functional_diagram),
        ("level-0-dfd", level0_dfd),
        ("level-1-dfd", level1_dfd),
        ("level-2-dfd", level2_dfd),
        ("erd", erd),
    ]
    pdfs: list[Path] = []
    pages: list[Image.Image] = []
    for filename, fn in exports:
        pdf_path, img = export_page(filename, fn)
        pdfs.append(pdf_path)
        pages.append(img)
    save_combined_pdf(pages)

    readme = OUT_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Diagram Exports",
                "",
                "All diagrams are exported as white-background A4 portrait PDFs and PNGs.",
                "",
                "- `functional-diagram.pdf` / `.png`",
                "- `level-0-dfd.pdf` / `.png`",
                "- `level-1-dfd.pdf` / `.png`",
                "- `level-2-dfd.pdf` / `.png`",
                "- `erd.pdf` / `.png`",
                "- `all-diagrams.pdf`",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
