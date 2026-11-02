
import random

from django.shortcuts import render, redirect
from .models import Topic, ControlTest, Question, Answer, StudentResult


def home(request):
    sinflar = range(5, 12)

    mavjud_turlar = set(
        ControlTest.objects.filter(
            faol=True
        ).values_list("turi", flat=True).distinct()
    )

    nazorat_turlari = [
        {"turi": turi, "nomi": nomi}
        for turi, nomi in ControlTest.NAZORAT_TURLARI
        if turi in mavjud_turlar
    ]

    return render(request, 'core/home.html', {
        'sinflar': sinflar,
        'nazorat_turlari': nazorat_turlari,
    })


def class_detail(request, sinf):
    if sinf < 5 or sinf > 11:
        return render(request, 'core/home.html', {
            'sinflar': range(5, 12)
        })

    mavzular = Topic.objects.filter(
        sinf=sinf,
        faol=True
    )

    return render(request, 'core/class_detail.html', {
        'sinf': sinf,
        'mavzular': mavzular
    })
def control_grade_select(request, turi):
    nazorat_turlari = dict(ControlTest.NAZORAT_TURLARI)

    if turi not in nazorat_turlari:
        return redirect("home")

    nazorat_sinflari = ControlTest.objects.filter(
        turi=turi,
        faol=True
    ).order_by("sinf")

    return render(request, "core/control_grade_select.html", {
        "nazorat_turi": turi,
        "nazorat_nomi": nazorat_turlari[turi],
        "nazorat_sinflari": nazorat_sinflari,
    })
def control_test_start(request, turi, sinf):
    nazorat = ControlTest.objects.filter(
        turi=turi,
        sinf=sinf,
        faol=True
    ).first()

    if not nazorat:
        return redirect("home")

    savollar = list(
        nazorat.questions.filter(
            faol=True
        ).prefetch_related("answers")
    )

    if not savollar:
        return redirect("home")
    session_key = f"control_student_{turi}_{sinf}"
    answer_order_key = f"control_answers_{turi}_{sinf}"
    
    # Javoblar tartibini sessiyada saqlash
    javob_tartibi = request.session.get(answer_order_key)

    if not javob_tartibi:
        javob_tartibi = {}

        for savol in savollar:
            javoblar = list(savol.answers.all())
            random.shuffle(javoblar)

            javob_tartibi[str(savol.id)] = [
                javob.id for javob in javoblar
            ]

        request.session[answer_order_key] = javob_tartibi

    # Javoblarni saqlangan tartibda joylashtirish
    for savol in savollar:
        javoblar = list(savol.answers.all())
        javoblar_by_id = {
            javob.id: javob for javob in javoblar
        }

        tartib = javob_tartibi.get(str(savol.id), [])

        if tartib and all(jid in javoblar_by_id for jid in tartib):
            savol.aralash_javoblar = [
                javoblar_by_id[jid] for jid in tartib
            ]
        else:
            random.shuffle(javoblar)
            savol.aralash_javoblar = javoblar
    
       # 1. Ism-familiyani qabul qilish
    if request.method == "POST" and "boshlash" in request.POST:
        ism_familiya = request.POST.get(
            "ism_familiya", ""
        ).strip()

        if len(ism_familiya.split()) < 2:
            return render(request, "core/control_student_info.html", {
                "nazorat": nazorat,
                "sinf": sinf,
                "xato": "Iltimos, ism va familiyangizni to‘liq kiriting."
            })

        request.session[session_key] = ism_familiya
        return redirect("control_test_start", turi=turi, sinf=sinf)

    # 2. Ism-familiya kiritilmagan bo‘lsa, avval ma'lumot so‘rash
    ism_familiya = request.session.get(session_key)

    if not ism_familiya:
        return render(request, "core/control_student_info.html", {
            "nazorat": nazorat,
            "sinf": sinf,
        })

    # 3. Test javoblarini tekshirish
    if request.method == "POST":
        togri_javoblar = 0

        for savol in savollar:
            javob_id = request.POST.get(f"savol_{savol.id}")

            if not javob_id:
                return render(request, "core/control_test.html", {
                    "nazorat": nazorat,
                    "savollar": savollar,
                    "sinf": sinf,
                    "xato": "Iltimos, barcha savollarga javob bering."
                })

            togri = Answer.objects.filter(
                id=javob_id,
                question=savol,
                togri=True
            ).exists()

            if togri:
                togri_javoblar += 1

        jami_savollar = len(savollar)
        xato_javoblar = jami_savollar - togri_javoblar

        ball = round(
            (togri_javoblar / jami_savollar) * 100
        )

        # 4. Natijani bazaga saqlash
        StudentResult.objects.create(
            ism_familiya=ism_familiya,
            sinf=sinf,
            control_test=nazorat,
            jami_savollar=jami_savollar,
            togri_javoblar=togri_javoblar,
            xato_javoblar=xato_javoblar,
            ball=ball,
        )
        request.session.pop(session_key, None)
        request.session.pop(answer_order_key, None)

        return render(request, "core/control_result.html", {
            "nazorat": nazorat,
            "sinf": sinf,
            "ism_familiya": ism_familiya,
            "jami_savollar": jami_savollar,
            "togri_javoblar": togri_javoblar,
            "xato_javoblar": xato_javoblar,
            "ball": ball,
        })

    # 5. Test sahifasini ko‘rsatish
    return render(request, "core/control_test.html", {
        "nazorat": nazorat,
        "savollar": savollar,
        "sinf": sinf,
    })


def topic_test_start(request, sinf):
    if sinf < 5 or sinf > 11:
        return redirect("home")

    session_key = f"topic_test_{sinf}"
    student_key = f"topic_student_{sinf}"

    # 1. Mavzularni tanlash va savollarni shakllantirish
    if request.method == "POST" and "mavzular" in request.POST:
        topic_ids = request.POST.getlist("mavzular")

        mavzular = list(
            Topic.objects.filter(
                id__in=topic_ids,
                sinf=sinf,
                faol=True
            )
        )

        if not mavzular:
            return redirect("class_detail", sinf=sinf)

        target_count = 10 if len(mavzular) == 1 else 20

        # Har bir mavzudan faqat to'liq savollarni olish
        pools = {}

        for mavzu in mavzular:
            savollar = list(
                Question.objects.filter(
                    topic=mavzu,
                    faol=True
                ).prefetch_related("answers")
            )

            valid_questions = []

            for savol in savollar:
                javoblar = list(savol.answers.all())
                togri_soni = sum(
                    1 for javob in javoblar if javob.togri
                )

                if len(javoblar) == 4 and togri_soni == 1:
                    valid_questions.append(savol)

            random.shuffle(valid_questions)
            pools[mavzu.id] = valid_questions

        # Jami yaroqli savollar sonini tekshirish
        available_count = sum(
            len(pool) for pool in pools.values()
        )

        if available_count < target_count:
            return render(
                request,
                "core/class_detail.html",
                {
                    "sinf": sinf,
                    "mavzular": Topic.objects.filter(
                        sinf=sinf,
                        faol=True
                    ).order_by("tartib", "nomi"),
                    "xato": (
                        f"Test tuzish uchun savollar yetarli emas. "
                        f"Kerak: {target_count} ta. "
                        f"Mavjud: {available_count} ta. "
                        f"Har bir savolda 4 ta javob va 1 ta "
                        f"to'g'ri javob bo'lishi kerak."
                    )
                }
            )

        # Savollarni mavzular orasida imkon qadar teng taqsimlash
        tanlangan_savollar = []

        while len(tanlangan_savollar) < target_count:
            progress = False

            topic_order = list(pools.keys())
            random.shuffle(topic_order)

            for topic_id in topic_order:
                if len(tanlangan_savollar) >= target_count:
                    break

                if pools[topic_id]:
                    tanlangan_savollar.append(
                        pools[topic_id].pop()
                    )
                    progress = True

            if not progress:
                break

        random.shuffle(tanlangan_savollar)

        # Har bir savol javoblarini tasodifiy aralashtirish
        javob_tartibi = {}

        for savol in tanlangan_savollar:
            javoblar = list(savol.answers.all())
            random.shuffle(javoblar)

            javob_tartibi[str(savol.id)] = [
                javob.id for javob in javoblar
            ]

        request.session[session_key] = {
            "savol_ids": [s.id for s in tanlangan_savollar],
            "topic_ids": [m.id for m in mavzular],
            "javob_tartibi": javob_tartibi,
        }

        request.session.pop(student_key, None)

        return redirect("topic_test_start", sinf=sinf)

    # 2. Ism-familiyani qabul qilish
    if request.method == "POST" and "boshlash" in request.POST:
        test_data = request.session.get(session_key)

        if not test_data:
            return redirect("class_detail", sinf=sinf)

        ism_familiya = request.POST.get(
            "ism_familiya", ""
        ).strip()

        if len(ism_familiya.split()) < 2:
            return render(request, "core/topic_student_info.html", {
                "sinf": sinf,
                "xato": "Iltimos, ism va familiyangizni to'liq kiriting."
            })

        request.session[student_key] = ism_familiya

        return redirect("topic_test_start", sinf=sinf)

    # 3. Test ma'lumotlarini olish
    test_data = request.session.get(session_key)

    if not test_data:
        return redirect("class_detail", sinf=sinf)

    savollar = list(
        Question.objects.filter(
            id__in=test_data["savol_ids"],
            topic__sinf=sinf,
            topic__faol=True,
            faol=True
        ).prefetch_related("answers")
    )

    savollar_by_id = {s.id: s for s in savollar}

    savollar = [
        savollar_by_id[sid]
        for sid in test_data["savol_ids"]
        if sid in savollar_by_id
        
    ]
    # Javoblarni sessiyada saqlangan tartibda joylashtirish
    javob_tartibi = test_data.get("javob_tartibi", {})

    for savol in savollar:
        javoblar = list(savol.answers.all())
        javoblar_by_id = {
            javob.id: javob for javob in javoblar
        }

        tartib = javob_tartibi.get(str(savol.id), [])

        if tartib and all(jid in javoblar_by_id for jid in tartib):
            savol.aralash_javoblar = [
                javoblar_by_id[jid] for jid in tartib
            ]
        else:
            random.shuffle(javoblar)
            savol.aralash_javoblar = javoblar

            javob_tartibi[str(savol.id)] = [
                javob.id for javob in javoblar
            ]

    # Yangi tartibni ham sessiyada saqlab qo'yish
    test_data["javob_tartibi"] = javob_tartibi
    request.session[session_key] = test_data
    if len(savollar) != len(test_data["savol_ids"]):
        request.session.pop(session_key, None)
        request.session.pop(student_key, None)
        return redirect("class_detail", sinf=sinf)

    # 4. Ism-familiya kiritilmagan bo'lsa
    ism_familiya = request.session.get(student_key)

    if not ism_familiya:
        return render(request, "core/topic_student_info.html", {
            "sinf": sinf,
        })

    # 5. Test javoblarini tekshirish
    if request.method == "POST" and "yakunlash" in request.POST:
        togri_javoblar = 0

        for savol in savollar:
            javob_id = request.POST.get(f"savol_{savol.id}")

            if not javob_id:
                return render(request, "core/topic_test.html", {
                    "sinf": sinf,
                    "savollar": savollar,
                    "xato": "Iltimos, barcha savollarga javob bering."
                })

            togri = Answer.objects.filter(
                id=javob_id,
                question=savol,
                togri=True
            ).exists()

            if togri:
                togri_javoblar += 1

        jami_savollar = len(savollar)
        xato_javoblar = jami_savollar - togri_javoblar

        ball = round(
            (togri_javoblar / jami_savollar) * 100
        )

        natija = StudentResult.objects.create(
            ism_familiya=ism_familiya,
            sinf=sinf,
            control_test=None,
            jami_savollar=jami_savollar,
            togri_javoblar=togri_javoblar,
            xato_javoblar=xato_javoblar,
            ball=ball,
        )

        mavzular = Topic.objects.filter(
            id__in=test_data["topic_ids"]
        )
        natija.topics.set(mavzular)

        request.session.pop(session_key, None)
        request.session.pop(student_key, None)

        return render(request, "core/topic_result.html", {
            "sinf": sinf,
            "ism_familiya": ism_familiya,
            "jami_savollar": jami_savollar,
            "togri_javoblar": togri_javoblar,
            "xato_javoblar": xato_javoblar,
            "ball": ball,
        })

    # 6. Test sahifasi
    return render(request, "core/topic_test.html", {
        "sinf": sinf,
        "savollar": savollar,
    })
