
import re
from html import escape

from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.oxml.ns import qn


QUESTION_PATTERN = re.compile(r"^\s*\d+\s*[.)]\s*(.*)$")
ANSWER_PATTERN = re.compile(r"^\s*([A-D])\s*[).]\s*(.*)$", re.IGNORECASE)


def extract_images(paragraph):
    """Paragraf ichidagi JPG/PNG rasmlarni ajratib olish."""
    images = []

    for blip in paragraph._p.xpath(".//a:blip"):
        relationship_id = blip.get(qn("r:embed"))

        if not relationship_id:
            continue

        try:
            image_part = paragraph.part.related_parts[relationship_id]
            image_data = image_part.blob
            image_type = image_part.content_type

            if image_type in ("image/jpeg", "image/png"):
                images.append({
                    "rasm": image_data,
                    "rasm_turi": image_type,
                })

        except (KeyError, AttributeError):
            continue

    return images


def get_list_marker(paragraph, counters):
    """Word raqamlangan va belgili ro‘yxat belgilarini aniqlash."""

    p_pr = paragraph._p.pPr

    if p_pr is None or p_pr.numPr is None:
        return ""

    num_pr = p_pr.numPr

    if num_pr.numId is None:
        return ""

    num_id = num_pr.numId.val
    ilvl = num_pr.ilvl.val if num_pr.ilvl is not None else 0

    numbering = paragraph.part.numbering_part.element

    num_element = next(
        (
            item for item in numbering.findall(qn("w:num"))
            if item.get(qn("w:numId")) == str(num_id)
        ),
        None
    )

    if num_element is None:
        return ""

    abstract_id = num_element.find(qn("w:abstractNumId")).get(qn("w:val"))

    abstract = next(
        (
            item for item in numbering.findall(qn("w:abstractNum"))
            if item.get(qn("w:abstractNumId")) == abstract_id
        ),
        None
    )

    if abstract is None:
        return ""

    level = next(
        (
            item for item in abstract.findall(qn("w:lvl"))
            if int(item.get(qn("w:ilvl"))) == ilvl
        ),
        None
    )

    if level is None:
        return ""

    num_format = level.find(qn("w:numFmt")).get(qn("w:val"))
    level_text = level.find(qn("w:lvlText")).get(qn("w:val"))

    key = (num_id, ilvl)

    if key not in counters:
        start = level.find(qn("w:start"))
        counters[key] = int(start.get(qn("w:val"))) if start is not None else 1
    else:
        counters[key] += 1

    number = counters[key]

    if num_format == "decimal":
        marker = str(number)

    elif num_format == "lowerLetter":
        marker = chr(96 + number) if 1 <= number <= 26 else str(number)

    elif num_format == "upperLetter":
        marker = chr(64 + number) if 1 <= number <= 26 else str(number)

    elif num_format == "lowerRoman":
        marker = str(number)

    elif num_format == "upperRoman":
        marker = str(number)

    elif num_format == "bullet":
        marker = level_text
        return marker + " "

    else:
        marker = str(number)

    marker = level_text.replace(f"%{ilvl + 1}", marker)

    return marker + " "


def table_to_html(table):
    """DOCX jadvalini ro‘yxat raqamlari va belgilari bilan HTML ga o'tkazish."""

    rows = []

    # Hisoblagich barcha kataklar uchun umumiy bo‘ladi.
    counters = {}

    for row_index, row in enumerate(table.rows):
        cells = []

        for cell in row.cells:
            paragraphs = []

            for paragraph in cell.paragraphs:
                text = escape(paragraph.text.strip())

                if not text:
                    continue

                # Word ro‘yxat belgisini aniqlash.
                marker = get_list_marker(paragraph, counters)

                background = (
                    "#e2e8f0" if row_index == 0 else "#ffffff"
                )

                paragraphs.append(
                    f'<p style="margin:4px 0;">'
                    f'{escape(marker)}{text}'
                    f'</p>'
                )

            cell_html = "".join(paragraphs)

            cells.append(
                f'<td style="'
                f'border:1px solid #333333; '
                f'padding:10px; '
                f'text-align:left; '
                f'vertical-align:middle; '
                f'background-color:{ "#e2e8f0" if row_index == 0 else "#ffffff" };'
                f'">{cell_html}</td>'
            )

        rows.append(
            '<tr>' + "".join(cells) + '</tr>'
        )

    return (
        '<table style="'
        'width:100%; '
        'border-collapse:collapse; '
        'border:2px solid #333333; '
        'margin:15px 0; '
        'color:#1e293b;'
        '">'
        '<tbody>'
        + "".join(rows)
        + '</tbody></table>'
    )


def import_questions_from_file(uploaded_file):
    document = Document(uploaded_file)

    questions = []
    current_question = None
    current_answer = None

    def add_question_text(text):
        if not text or current_question is None:
            return

        current_question["matn"] += (
            " " if current_question["matn"] else ""
        ) + text

        current_question["blocks"].append({
            "turi": "text",
            "matn": text,
        })

    def add_question_image(image):
        if current_question is None:
            return

        current_question["blocks"].append({
            "turi": "image",
            "rasm": image["rasm"],
            "rasm_turi": image["rasm_turi"],
        })

    def add_answer_image(image):
        if current_answer is None:
            add_question_image(image)
            return

        if current_answer["rasm"] is None:
            current_answer["rasm"] = image["rasm"]
            current_answer["rasm_turi"] = image["rasm_turi"]
        else:
            add_question_image(image)

    def finish_question():
        nonlocal current_question, current_answer

        if current_question is None:
            return

        answers = current_question["answers"]

        if len(answers) != 4:
            raise ValueError(
                f'{current_question["matn"][:60]}... '
                "savolida 4 ta javob varianti topilmadi."
            )

        correct_count = sum(
            1 for answer in answers if answer["togri"]
        )

        if correct_count != 1:
            raise ValueError(
                f'{current_question["matn"][:60]}... '
                "savolida aynan bitta to‘g‘ri javob "
                "bo‘lishi kerak."
            )

        if not current_question["matn"].strip() and not current_question["blocks"]:
            raise ValueError("Savol matni yoki rasmi topilmadi.")

        questions.append(current_question)
        current_question = None
        current_answer = None

    # DOCX hujjatidagi paragraf va jadvallar tartibini saqlash.
    for element in document.element.body.iterchildren():

        if element.tag == qn("w:p"):
            paragraph = Paragraph(element, document)

            line = paragraph.text.strip()
            images = extract_images(paragraph)

            if not line and not images:
                continue

            question_match = QUESTION_PATTERN.match(line)

            if question_match:
                finish_question()

                current_question = {
                    "matn": "",
                    "blocks": [],
                    "answers": [],
                }

                current_answer = None

                question_text = question_match.group(1).strip()

                if question_text:
                    add_question_text(question_text)

                for image in images:
                    add_question_image(image)

                continue

            answer_match = ANSWER_PATTERN.match(line)

            if answer_match and current_question is not None:
                answer_text = answer_match.group(2).strip()

                is_correct = answer_text.endswith("*")

                if is_correct:
                    answer_text = answer_text[:-1].rstrip()

                current_answer = {
                    "matn": answer_text,
                    "togri": is_correct,
                    "rasm": None,
                    "rasm_turi": "",
                }

                current_question["answers"].append(current_answer)

                for image in images:
                    add_answer_image(image)

                continue

            if current_question is not None:

                if line:
                    if current_answer is not None:
                        current_answer["matn"] += " " + line
                    else:
                        add_question_text(line)

                for image in images:
                    if current_answer is not None:
                        add_answer_image(image)
                    else:
                        add_question_image(image)

        elif element.tag == qn("w:tbl"):
            if current_question is None:
                continue

            table = Table(element, document)
            html_table = table_to_html(table)

            current_question["blocks"].append({
                "turi": "table",
                "matn": html_table,
            })

    finish_question()

    if not questions:
        raise ValueError(
            "DOCX fayldan savollar topilmadi."
        )

    return questions
