from django.db import migrations


CITIES = [
    ("samara", "Самара"),
    ("moskva", "Москва"),
    ("sankt-peterburg", "Санкт-Петербург"),
    ("kazan", "Казань"),
    ("ekaterinburg", "Екатеринбург"),
    ("novosibirsk", "Новосибирск"),
    ("nizhniy-novgorod", "Нижний Новгород"),
    ("krasnodar", "Краснодар"),
    ("voronezh", "Воронеж"),
    ("rostov-na-donu", "Ростов-на-Дону"),
    ("ufa", "Уфа"),
    ("perm", "Пермь"),
    ("volgograd", "Волгоград"),
    ("krasnoyarsk", "Красноярск"),
    ("tolyatti", "Тольятти"),
]


def seed_cities(apps, schema_editor):
    City = apps.get_model("location", "City")
    for slug, name in CITIES:
        City.objects.get_or_create(slug=slug, defaults={"name": name})


def unseed_cities(apps, schema_editor):
    City = apps.get_model("location", "City")
    slugs = [slug for slug, _ in CITIES]
    City.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("location", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_cities, unseed_cities),
    ]
