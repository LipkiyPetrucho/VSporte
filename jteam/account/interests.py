"""Каталог интересов пользователя: категории, подписи и иконки."""

# (slug, label, font-awesome icon class without "fas ")
INTEREST_CATEGORIES = (
    (
        "Командные виды спорта",
        (
            ("football", "Футбол", "fa-futbol"),
            ("basketball", "Баскетбол", "fa-basketball"),
            ("volleyball", "Волейбол", "fa-volleyball"),
            ("handball", "Гандбол", "fa-hand-fist"),
            ("rugby", "Регби", "fa-football"),
            ("baseball", "Бейсбол", "fa-baseball-bat-ball"),
            ("ice hockey", "Хоккей", "fa-hockey-puck"),
        ),
    ),
    (
        "Ракеточные и сеточные виды спорта",
        (
            ("tennis", "Теннис", "fa-table-tennis-paddle-ball"),
            ("badminton", "Бадминтон", "fa-feather"),
            ("beach volleyball", "Пляжный волейбол", "fa-volleyball"),
        ),
    ),
    (
        "Водные виды спорта",
        (
            ("water polo", "Водное поло", "fa-person-swimming"),
            ("sup", "SUP", "fa-water"),
            ("sailing", "Парусный спорт", "fa-sailboat"),
        ),
    ),
    (
        "Точные и стратегические виды спорта",
        (
            ("curling", "Кёрлинг", "fa-circle"),
            ("paintball", "Пейнтбол", "fa-crosshairs"),
            ("chess", "Шахматы", "fa-chess"),
            ("bowling", "Боулинг", "fa-bowling-ball"),
        ),
    ),
    (
        "Индивидуальные и беговые виды спорта",
        (
            ("running", "Бег", "fa-person-running"),
            ("equestrian", "Конный спорт", "fa-horse"),
        ),
    ),
)

INTEREST_CHOICES = tuple(
    (slug, label)
    for _category, items in INTEREST_CATEGORIES
    for slug, label, _icon in items
)

INTEREST_LABELS = dict(INTEREST_CHOICES)

INTEREST_ICONS = {
    slug: icon
    for _category, items in INTEREST_CATEGORIES
    for slug, _label, icon in items
}

INTEREST_SLUGS = frozenset(INTEREST_LABELS)
