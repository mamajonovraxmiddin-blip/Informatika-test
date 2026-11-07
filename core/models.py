
from django.db import models


SINF_CHOICES = [
    (i, f"{i}-sinf") for i in range(5, 12)
]


class Topic(models.Model):
    sinf = models.PositiveSmallIntegerField(
        verbose_name="Sinf",
        choices=SINF_CHOICES
    )
    nomi = models.CharField(
        max_length=200,
        verbose_name="Mavzu nomi"
    )
    tavsif = models.TextField(
        blank=True,
        verbose_name="Mavzu haqida"
    )
    tartib = models.PositiveIntegerField(
        default=1,
        verbose_name="Tartib raqami"
    )
    faol = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )
    yaratilgan_vaqt = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Mavzu"
        verbose_name_plural = "Mavzular"
        ordering = ["sinf", "tartib", "nomi"]
        constraints = [
            models.UniqueConstraint(
                fields=["sinf", "nomi"],
                name="unique_topic_per_grade"
            )
        ]

    def __str__(self):
        return f"{self.sinf}-sinf — {self.nomi}"


class ControlTest(models.Model):
    NAZORAT_TURLARI = [
        ("1-chorak", "1-chorak nazorati"),
        ("2-chorak", "2-chorak nazorati"),
        ("3-chorak", "3-chorak nazorati"),
        ("4-chorak", "4-chorak nazorati"),
        ("yillik", "Yillik nazorat"),
    ]

    sinf = models.PositiveSmallIntegerField(
        verbose_name="Sinf",
        choices=SINF_CHOICES
    )
    turi = models.CharField(
        max_length=20,
        choices=NAZORAT_TURLARI,
        verbose_name="Nazorat turi"
    )
    faol = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )
    yaratilgan_vaqt = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Nazorat testi"
        verbose_name_plural = "Nazorat testlari"
        ordering = ["sinf", "turi"]
        constraints = [
            models.UniqueConstraint(
                fields=["sinf", "turi"],
                name="unique_control_test_per_grade"
            )
        ]

    def __str__(self):
        return f"{self.sinf}-sinf — {self.get_turi_display()}"


class Question(models.Model):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Mavzu",
        null=True,
        blank=True
    )
    control_test = models.ForeignKey(
        ControlTest,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Nazorat testi",
        null=True,
        blank=True
    )
    matn = models.TextField(
        verbose_name="Savol matni"
    )
    tartib = models.PositiveIntegerField(
        default=1,
        verbose_name="Tartib"
    )
    faol = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )
    yaratilgan_vaqt = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Test savoli"
        verbose_name_plural = "Test savollari"
        ordering = ["tartib", "id"]

    def __str__(self):
        return self.matn[:100]


class QuestionContentBlock(models.Model):
    BLOCK_TYPES = [
        ("text", "Matn"),
        ("image", "Rasm"),
        ("table", "Jadval"),
    ]

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="content_blocks",
        verbose_name="Savol"
    )
    turi = models.CharField(
        max_length=10,
        choices=BLOCK_TYPES,
        verbose_name="Blok turi"
    )
    matn = models.TextField(
        blank=True,
        verbose_name="Matn yoki jadval HTML"
    )
    rasm = models.BinaryField(
        null=True,
        blank=True,
        verbose_name="Rasm fayli"
    )
    rasm_turi = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Rasm formati"
    )
    tartib = models.PositiveIntegerField(
        default=1,
        verbose_name="Joylashuv tartibi"
    )

    class Meta:
        verbose_name = "Savol tarkibi"
        verbose_name_plural = "Savol tarkiblari"
        ordering = ["tartib", "id"]

    def __str__(self):
        return (
            f"{self.question_id}-savol — "
            f"{self.get_turi_display()}"
        )


class Answer(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Savol"
    )
    matn = models.CharField(
        max_length=1000,
        verbose_name="Javob varianti"
    )
    togri = models.BooleanField(
        default=False,
        verbose_name="To‘g‘ri javob"
    )
    tartib = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Tartib"
    )
    rasm = models.BinaryField(
        null=True,
        blank=True,
        verbose_name="Javob rasmi"
    )
    rasm_turi = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Rasm formati"
    )

    class Meta:
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"
        ordering = ["tartib", "id"]

    def __str__(self):
        return self.matn


class StudentResult(models.Model):
    ism_familiya = models.CharField(
        max_length=200,
        verbose_name="O‘quvchining ism-familiyasi"
    )
    sinf = models.PositiveSmallIntegerField(
        verbose_name="Sinf"
    )
    control_test = models.ForeignKey(
        ControlTest,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="Nazorat testi",
        null=True,
        blank=True
    )
    topics = models.ManyToManyField(
        Topic,
        related_name="student_results",
        verbose_name="Tanlangan mavzular",
        blank=True
    )
    jami_savollar = models.PositiveIntegerField(
        verbose_name="Jami savollar"
    )
    togri_javoblar = models.PositiveIntegerField(
        verbose_name="To‘g‘ri javoblar"
    )
    xato_javoblar = models.PositiveIntegerField(
        verbose_name="Xato javoblar"
    )
    ball = models.PositiveSmallIntegerField(
        verbose_name="Natija (100 ballik tizim)"
    )
    yaratilgan_vaqt = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Test topshirilgan vaqt"
    )

    class Meta:
        verbose_name = "O‘quvchi natijasi"
        verbose_name_plural = "O‘quvchilar natijalari"
        ordering = ["-yaratilgan_vaqt"]

    def __str__(self):
        return f"{self.ism_familiya} — {self.ball} ball"
