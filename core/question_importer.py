
import re
from docx import Document


QUESTION_PATTERN = re.compile(r"^\s*\d+\s*[.)]\s*(.*)$")
ANSWER_PATTERN = re.compile(r"^\s*([A-D])\s*[).]\s*(.*)$", re.IGNORECASE)


def import_questions_from_file(uploaded_file):
    document = Document(uploaded_file)
    lines = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
    ]

    questions = []
    current_question = None
    current_answer = None

    def finish_question():
        nonlocal current_question

        if current_question is None:
            return

        answers = current_question["answers"]

        if len(answers) != 4:
            raise ValueError(
                f'{current_question["matn"][:60]}... '
                f'savolida 4 ta javob varianti topilmadi.'
            )

        correct_count = sum(
            1 for answer in answers if answer["togri"]
        )

        if correct_count != 1:
            raise ValueError(
                f'{current_question["matn"][:60]}... '
                "savolida aynan bitta to‘g‘ri javob bo‘lishi kerak."
            )

        questions.append(current_question)
        current_question = None

    for line in lines:
        if not line:
            continue

        question_match = QUESTION_PATTERN.match(line)

        if question_match:
            finish_question()

            current_question = {
                "matn": question_match.group(1).strip(),
                "answers": []
            }
            current_answer = None
            continue

        answer_match = ANSWER_PATTERN.match(line)

        if answer_match and current_question is not None:
            answer_text = answer_match.group(2).strip()
            is_correct = answer_text.endswith("*")

            if is_correct:
                answer_text = answer_text[:-1].rstrip()

            current_answer = {
                "matn": answer_text,
                "togri": is_correct
            }

            current_question["answers"].append(current_answer)
            continue

        if current_question is not None:
            if current_answer is not None:
                current_answer["matn"] += " " + line
            else:
                current_question["matn"] += " " + line

    finish_question()

    if not questions:
        raise ValueError("DOCX fayldan savollar topilmadi.")

    return questions
