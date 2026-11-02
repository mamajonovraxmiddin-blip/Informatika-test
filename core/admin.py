
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django import forms
from django.http import JsonResponse, HttpResponse
from django.db import transaction

from openpyxl import Workbook, load_workbook
from openpyxl.styles import (
    Font, Alignment, PatternFill, Border, Side
)

from .models import (
    Topic, Question, Answer, ControlTest, StudentResult
)


# =====================================================
# FORMLAR
# =====================================================

class QuestionImportForm(forms.Form):
    sinf = forms.ChoiceField(
        choices=[("", "Sinfni tanlang")] +
                [(i, f"{i}-sinf") for i in range(5, 12)],
        label="Sinf"
    )

    topic = forms.ModelChoiceField(
        queryset=Topic.objects.none(),
        label="Mavzu",
        empty_label="Avval sinfni tanlang"
    )

    file = forms.FileField(label="Test fayli (DOCX)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sinf = self.data.get("sinf") or self.initial.get("sinf")

        if sinf:
            self.fields["topic"].queryset = Topic.objects.filter(
                sinf=sinf,
                faol=True
            ).order_by("tartib", "nomi")


class ControlTestImportForm(forms.Form):
    control_test = forms.ModelChoiceField(
        queryset=ControlTest.objects.filter(faol=True).order_by(
            "sinf", "turi"
        ),
        label="Nazorat testi",
        empty_label="Nazorat turini tanlang"
    )

    file = forms.FileField(label="Test fayli (DOCX)")


class TopicExcelImportForm(forms.Form):
    file = forms.FileField(
        label="Excel fayl (.xlsx)",
        help_text="Ustunlar: Sinf, Mavzu nomi, Tartib"
    )


# =====================================================
# MAVZULAR ADMINI
# =====================================================

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    change_list_template = "admin/core/topic/change_list.html"

    list_display = ("nomi", "sinf", "tartib", "faol")
    list_filter = ("sinf", "faol")
    search_fields = ("nomi", "tavsif")
    list_editable = ("tartib", "faol")
    ordering = ("sinf", "tartib")

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel),
                name="core_topic_import_excel"
            ),
        ]

        return custom_urls + urls

    def import_excel(self, request):
        if request.method == "POST":
            form = TopicExcelImportForm(
                request.POST,
                request.FILES
            )

            if form.is_valid():
                uploaded_file = form.cleaned_data["file"]

                if not uploaded_file.name.lower().endswith(".xlsx"):
                    form.add_error(
                        "file",
                        "Faqat .xlsx formatidagi Excel fayl yuklang."
                    )
                else:
                    try:
                        workbook = load_workbook(
                            uploaded_file,
                            read_only=True,
                            data_only=True
                        )
                        sheet = workbook.active

                        rows = sheet.iter_rows(values_only=True)
                        headers = next(rows, None)

                        if not headers:
                            raise ValueError("Excel fayli bo‘sh.")

                        normalized_headers = [
                            str(value).strip().lower()
                            if value is not None else ""
                            for value in headers
                        ]

                        required = ["sinf", "mavzu nomi", "tartib"]

                        if not all(
                            header in normalized_headers
                            for header in required
                        ):
                            raise ValueError(
                                "Excel ustunlari quyidagicha bo‘lishi kerak: "
                                "Sinf, Mavzu nomi, Tartib."
                            )

                        sinf_index = normalized_headers.index("sinf")
                        nomi_index = normalized_headers.index("mavzu nomi")
                        tartib_index = normalized_headers.index("tartib")

                        added = 0
                        duplicates = 0
                        errors = []

                        with transaction.atomic():
                            for row_number, row in enumerate(rows, start=2):
                                try:
                                    sinf_value = row[sinf_index]
                                    nomi_value = row[nomi_index]
                                    tartib_value = row[tartib_index]

                                    sinf = int(sinf_value)
                                    nomi = str(nomi_value).strip()
                                    tartib = int(tartib_value)

                                    if sinf not in range(5, 12):
                                        raise ValueError(
                                            "Sinf 5 dan 11 gacha bo‘lishi kerak."
                                        )

                                    if not nomi:
                                        raise ValueError(
                                            "Mavzu nomi kiritilmagan."
                                        )

                                    if tartib < 1:
                                        raise ValueError(
                                            "Tartib raqami 1 yoki undan katta bo‘lishi kerak."
                                        )

                                    if Topic.objects.filter(
                                        sinf=sinf,
                                        nomi__iexact=nomi
                                    ).exists():
                                        duplicates += 1
                                        continue

                                    Topic.objects.create(
                                        sinf=sinf,
                                        nomi=nomi,
                                        tartib=tartib,
                                        faol=True
                                    )
                                    added += 1

                                except (ValueError, TypeError, IndexError):
                                    errors.append(
                                        f"{row_number}-qator: ma’lumot noto‘g‘ri."
                                    )

                        workbook.close()

                        messages.success(
                            request,
                            f"Import yakunlandi. Qo‘shildi: {added} ta. "
                            f"Takroriy: {duplicates} ta. "
                            f"Xatoli: {len(errors)} ta."
                        )

                        for error in errors[:15]:
                            messages.warning(request, error)

                        if len(errors) > 15:
                            messages.warning(
                                request,
                                f"Yana {len(errors) - 15} ta xatoli qator mavjud."
                            )

                        return redirect("admin:core_topic_changelist")

                    except Exception as error:
                        messages.error(
                            request,
                            f"Excel faylni o‘qishda xatolik: {error}"
                        )

        else:
            form = TopicExcelImportForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Mavzularni Excel fayldan yuklash",
            "form": form,
            "opts": self.model._meta,
        }

        return render(
            request,
            "admin/core/import_topics.html",
            context
        )


# =====================================================
# NAZORAT TESTLARI ADMINI
# =====================================================

@admin.register(ControlTest)
class ControlTestAdmin(admin.ModelAdmin):
    change_list_template = "admin/core/controltest/change_list.html"

    list_display = ("sinf", "turi", "faol", "yaratilgan_vaqt")
    list_filter = ("sinf", "turi", "faol")
    list_editable = ("faol",)
    ordering = ("sinf", "turi")

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_control_questions),
                name="core_controltest_import"
            ),
        ]

        return custom_urls + urls

    def import_control_questions(self, request):
        from .question_importer import import_questions_from_file

        if request.method == "POST":
            form = ControlTestImportForm(
                request.POST,
                request.FILES
            )

            if form.is_valid():
                control_test = form.cleaned_data["control_test"]
                uploaded_file = form.cleaned_data["file"]

                if not uploaded_file.name.lower().endswith(".docx"):
                    form.add_error(
                        "file",
                        "Faqat DOCX formatidagi Word fayl yuklash mumkin."
                    )
                else:
                    try:
                        parsed_questions = import_questions_from_file(
                            uploaded_file
                        )

                        with transaction.atomic():
                            start_order = control_test.questions.count()

                            for index, item in enumerate(
                                parsed_questions,
                                start=1
                            ):
                                question = Question.objects.create(
                                    control_test=control_test,
                                    matn=item["matn"],
                                    tartib=start_order + index,
                                    faol=True
                                )

                                Answer.objects.bulk_create([
                                    Answer(
                                        question=question,
                                        matn=answer["matn"],
                                        togri=answer["togri"],
                                        tartib=answer_index
                                    )
                                    for answer_index, answer in enumerate(
                                        item["answers"],
                                        start=1
                                    )
                                ])

                        messages.success(
                            request,
                            f"{control_test}: "
                            f"{len(parsed_questions)} ta savol muvaffaqiyatli yuklandi."
                        )

                        return redirect(
                            "admin:core_controltest_changelist"
                        )

                    except Exception as error:
                        messages.error(
                            request,
                            f"Import qilishda xatolik: {error}"
                        )

        else:
            form = ControlTestImportForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Nazorat testlariga savollar yuklash",
            "form": form,
            "opts": self.model._meta,
        }

        return render(
            request,
            "admin/core/import_control_questions.html",
            context
        )


# =====================================================
# SAVOLLAR ADMINI
# =====================================================

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    min_num = 2
    fields = ("matn", "togri", "tartib")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    change_list_template = "admin/core/question/change_list.html"

    list_display = ("matn", "topic", "tartib", "faol")
    list_filter = ("topic__sinf", "topic", "faol")
    search_fields = ("matn", "topic__nomi")
    list_editable = ("tartib", "faol")
    ordering = ("topic", "tartib")
    inlines = [AnswerInline]

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_questions),
                name="core_question_import"
            ),
            path(
                "topic-options/",
                self.admin_site.admin_view(self.topic_options),
                name="core_question_topic_options"
            ),
        ]

        return custom_urls + urls

    def topic_options(self, request):
        sinf = request.GET.get("sinf")

        topics = Topic.objects.filter(
            sinf=sinf,
            faol=True
        ).order_by("tartib", "nomi")

        data = [
            {"id": topic.id, "nomi": topic.nomi}
            for topic in topics
        ]

        return JsonResponse({"topics": data})

    def import_questions(self, request):
        from .question_importer import import_questions_from_file

        if request.method == "POST":
            form = QuestionImportForm(request.POST, request.FILES)

            if form.is_valid():
                sinf = int(form.cleaned_data["sinf"])
                topic = form.cleaned_data["topic"]
                uploaded_file = form.cleaned_data["file"]

                extension = uploaded_file.name.lower().rsplit(".", 1)[-1]

                if topic.sinf != sinf:
                    form.add_error(
                        "topic",
                        "Tanlangan mavzu ushbu sinfga tegishli emas."
                    )

                elif extension != "docx":
                    form.add_error(
                        "file",
                        "Faqat DOCX formatidagi Word fayl yuklash mumkin."
                    )

                else:
                    try:
                        parsed_questions = import_questions_from_file(
                            uploaded_file
                        )

                        with transaction.atomic():
                            start_order = Question.objects.filter(
                                topic=topic
                            ).count()

                            for index, item in enumerate(
                                parsed_questions,
                                start=1
                            ):
                                question = Question.objects.create(
                                    topic=topic,
                                    matn=item["matn"],
                                    tartib=start_order + index,
                                    faol=True
                                )

                                Answer.objects.bulk_create([
                                    Answer(
                                        question=question,
                                        matn=answer["matn"],
                                        togri=answer["togri"],
                                        tartib=answer_index
                                    )
                                    for answer_index, answer in enumerate(
                                        item["answers"],
                                        start=1
                                    )
                                ])

                        messages.success(
                            request,
                            f"Muvaffaqiyatli import qilindi: "
                            f"{len(parsed_questions)} ta savol."
                        )

                        return redirect("admin:core_question_changelist")

                    except Exception as error:
                        messages.error(
                            request,
                            f"Import qilishda xatolik: {error}"
                        )

        else:
            form = QuestionImportForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Testlarni fayldan yuklash",
            "form": form,
            "opts": self.model._meta,
        }

        return render(
            request,
            "admin/core/import_questions.html",
            context
        )


# =====================================================
# JAVOBLAR ADMINI
# =====================================================

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("matn", "question", "togri", "tartib")
    list_filter = ("togri",)
    search_fields = ("matn", "question__matn")


# =====================================================
# O'QUVCHILAR NATIJALARI ADMINI
# =====================================================


@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    change_list_template = "admin/core/studentresult/change_list.html"

    list_display = (
        "ism_familiya",
        "sinf",
        "test_turi",
        "topics_display",
        "jami_savollar",
        "togri_javoblar",
        "xato_javoblar",
        "ball",
        "yaratilgan_vaqt",
    )

    list_filter = (
        "sinf",
        "control_test__turi",
        "yaratilgan_vaqt",
    )

    search_fields = ("ism_familiya",)
    date_hierarchy = "yaratilgan_vaqt"
    ordering = ("-yaratilgan_vaqt",)

    actions = ["export_to_excel"]

    @admin.display(description="Test turi")
    def test_turi(self, obj):
        if obj.control_test:
            return obj.control_test.get_turi_display()

        return "Mavzuli test"

    @admin.display(description="Tanlangan mavzular")
    def topics_display(self, obj):
        mavzular = obj.topics.all()

        if not mavzular:
            return "—"

        return ", ".join(m.nomi for m in mavzular)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.select_related(
            "control_test"
        ).prefetch_related(
            "topics"
        )

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "export-all/",
                self.admin_site.admin_view(self.export_all),
                name="core_studentresult_export_all",
            ),
        ]

        return custom_urls + urls

    # Tanlangan natijalarni eksport qilish
    @admin.action(description="Tanlangan natijalarni Excelga yuklab olish")
    def export_to_excel(self, request, queryset):
        return self.create_excel_response(queryset)

    # Filtrlangan barcha natijalarni eksport qilish
    def export_all(self, request):
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        return self.create_excel_response(queryset)

    # Excel faylini yaratish
    def create_excel_response(self, queryset):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Oquvchilar natijalari"

        headers = [
            "№",
            "O‘quvchi ism-familiyasi",
            "Sinf",
            "Test turi",
            "Tanlangan mavzular",
            "Jami savollar",
            "To‘g‘ri javoblar",
            "Xato javoblar",
            "Ball",
            "Topshirilgan vaqt",
        ]

        sheet.append(headers)

        green_fill = PatternFill(
            fill_type="solid",
            fgColor="C6EFCE"
        )
        yellow_fill = PatternFill(
            fill_type="solid",
            fgColor="FFEB9C"
        )
        red_fill = PatternFill(
            fill_type="solid",
            fgColor="FFC7CE"
        )

        green_font = Font(
            name="Arial", size=10, bold=True, color="006100"
        )
        yellow_font = Font(
            name="Arial", size=10, bold=True, color="9C6500"
        )
        red_font = Font(
            name="Arial", size=10, bold=True, color="9C0006"
        )

        queryset = queryset.select_related(
            "control_test"
        ).prefetch_related(
            "topics"
        )

        for index, result in enumerate(queryset, start=1):
            row_number = index + 1

            if result.control_test:
                test_turi = result.control_test.get_turi_display()
            else:
                test_turi = "Mavzuli test"

            mavzular = ", ".join(
                mavzu.nomi for mavzu in result.topics.all()
            )

            sheet.append([
                index,
                result.ism_familiya,
                f"{result.sinf}-sinf",
                test_turi,
                mavzular or "—",
                result.jami_savollar,
                result.togri_javoblar,
                result.xato_javoblar,
                result.ball,
                result.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M"),
            ])

            ball_cell = sheet.cell(
                row=row_number,
                column=9
            )

            if result.ball >= 86:
                ball_cell.fill = green_fill
                ball_cell.font = green_font

            elif result.ball >= 70:
                ball_cell.fill = yellow_fill
                ball_cell.font = yellow_font

            else:
                ball_cell.fill = red_fill
                ball_cell.font = red_font

        header_fill = PatternFill(
            fill_type="solid",
            fgColor="17365D"
        )

        header_font = Font(
            name="Arial",
            size=10,
            bold=True,
            color="FFFFFF"
        )

        thin_border = Border(
            left=Side(style="thin", color="D9E2F3"),
            right=Side(style="thin", color="D9E2F3"),
            top=Side(style="thin", color="D9E2F3"),
            bottom=Side(style="thin", color="D9E2F3"),
        )

        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True
            )
            cell.border = thin_border

        sheet.row_dimensions[1].height = 35

        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True
                )

                if cell.column != 9:
                    cell.font = Font(
                        name="Arial",
                        size=10
                    )

            row[1].alignment = Alignment(
                horizontal="left",
                vertical="center"
            )
            row[4].alignment = Alignment(
                horizontal="left",
                vertical="center",
                wrap_text=True
            )

        widths = {
            "A": 6,
            "B": 32,
            "C": 12,
            "D": 25,
            "E": 40,
            "F": 16,
            "G": 18,
            "H": 16,
            "I": 12,
            "J": 22,
        }

        for column, width in widths.items():
            sheet.column_dimensions[column].width = width

        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        sheet.sheet_view.showGridLines = False

        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.fitToWidth = 1
        sheet.sheet_properties.pageSetUpPr.fitToPage = True

        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        response["Content-Disposition"] = (
            'attachment; filename="oquvchilar_natijalari.xlsx"'
        )

        workbook.save(response)

        return response

admin.site.site_header = "Asaka tumani 48-maktab"
admin.site.site_title = "48-maktab boshqaruv paneli"
admin.site.index_title = "Boshqaruv paneli"