from django.contrib.auth.models import User
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, TextField
from django.db.models.functions import Cast
from django.utils import timezone

from games.models import Game

from .interests import INTEREST_LABELS
from .models import Contact, Friendship, Profile, UserBlock


def ensure_profile(user):
    """Гарантирует наличие Profile у пользователя."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def is_blocked(blocker, blocked):
    if not blocker or not blocked or blocker.pk == blocked.pk:
        return False
    return UserBlock.objects.filter(blocker=blocker, blocked=blocked).exists()


def get_blocked_user_ids(user):
    return set(
        UserBlock.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    )


def block_user(blocker, blocked):
    if blocker.pk == blocked.pk:
        return False

    UserBlock.objects.get_or_create(blocker=blocker, blocked=blocked)
    Friendship.objects.filter(
        Q(from_user=blocker, to_user=blocked) | Q(from_user=blocked, to_user=blocker)
    ).delete()
    Contact.objects.filter(
        Q(user_from=blocker, user_to=blocked) | Q(user_from=blocked, user_to=blocker)
    ).delete()
    return True


def unblock_user(blocker, blocked):
    deleted, _ = UserBlock.objects.filter(blocker=blocker, blocked=blocked).delete()
    return deleted > 0


def get_blocked_users(user):
    blocked_ids = get_blocked_user_ids(user)
    return (
        User.objects.filter(pk__in=blocked_ids, is_active=True)
        .select_related("profile")
        .order_by("username")
    )


def search_users(query):
    """Searches for users by first name, last name or login (case insensitive)
    using trigrams.
    Returns users by partial match with the query.
    """
    username_cast = Cast("username", TextField())
    first_name_cast = Cast("first_name", TextField())
    last_name_cast = Cast("last_name", TextField())

    search_query = (
        TrigramSimilarity(username_cast, query)
        + TrigramSimilarity(first_name_cast, query)
        + TrigramSimilarity(last_name_cast, query)
    )

    results = (
        User.objects.annotate(similarity=search_query)
        .filter(similarity__gt=0.1)
        .order_by("-similarity")
    )
    return results


def get_coplayed_user_ids(user):
    """Users who participated in the same games as the given user."""
    game_ids = Game.objects.filter(
        Q(joined_players=user) | Q(user=user)
    ).values_list("id", flat=True)

    return set(
        User.objects.filter(
            Q(joined_games__id__in=game_ids) | Q(user_games_created__id__in=game_ids)
        )
        .exclude(pk=user.pk)
        .values_list("pk", flat=True)
    )


def get_friendship_status(viewer, other):
    if viewer.pk == other.pk:
        return "self"

    if Friendship.objects.filter(
        Q(from_user=viewer, to_user=other, status=Friendship.ACCEPTED)
        | Q(from_user=other, to_user=viewer, status=Friendship.ACCEPTED)
    ).exists():
        return "friends"

    if Friendship.objects.filter(
        from_user=viewer, to_user=other, status=Friendship.PENDING
    ).exists():
        return "pending_sent"

    if Friendship.objects.filter(
        from_user=other, to_user=viewer, status=Friendship.PENDING
    ).exists():
        return "pending_received"

    return "none"


def apply_played_filter(queryset, user, played_filter):
    coplayed_ids = get_coplayed_user_ids(user)
    if played_filter == "played":
        return queryset.filter(pk__in=coplayed_ids)
    if played_filter == "not_played":
        return queryset.exclude(pk__in=coplayed_ids)
    return queryset


def get_user_games(user):
    return Game.objects.filter(Q(joined_players=user) | Q(user=user)).distinct()


def get_friend_users(user):
    friend_ids = set(
        Friendship.objects.filter(
            from_user=user, status=Friendship.ACCEPTED
        ).values_list("to_user_id", flat=True)
    ) | set(
        Friendship.objects.filter(
            to_user=user, status=Friendship.ACCEPTED
        ).values_list("from_user_id", flat=True)
    )
    return (
        User.objects.filter(pk__in=friend_ids)
        .select_related("profile")
        .order_by("username")
    )


def count_playpals(user):
    return Friendship.objects.filter(
        Q(from_user=user, status=Friendship.ACCEPTED)
        | Q(to_user=user, status=Friendship.ACCEPTED)
    ).count()


def count_incoming_friend_requests(user):
    return Friendship.objects.filter(
        to_user=user, status=Friendship.PENDING
    ).count()


def get_incoming_friend_requests(user):
    friendships = (
        Friendship.objects.filter(to_user=user, status=Friendship.PENDING)
        .select_related("from_user", "from_user__profile")
        .order_by("-created")
    )
    return [
        {"user": friendship.from_user, "friendship": "pending_received"}
        for friendship in friendships
    ]


def get_outgoing_friend_requests(user):
    friendships = (
        Friendship.objects.filter(from_user=user, status=Friendship.PENDING)
        .select_related("to_user", "to_user__profile")
        .order_by("-created")
    )
    return [
        {"user": friendship.to_user, "friendship": "pending_sent"}
        for friendship in friendships
    ]


def get_profile_stats(user):
    profile = ensure_profile(user)
    games = get_user_games(user)
    now = timezone.now()
    last_game = (
        games.filter(start_time__lte=now).order_by("-start_time").first()
    )
    sport_labels = {**dict(Game.SPORTS), **INTEREST_LABELS}

    if profile.interests:
        interests = [
            sport_labels.get(sport, sport)
            for sport in profile.interests
            if sport in sport_labels
        ]
    else:
        sports = (
            games.values_list("sport", flat=True).distinct().order_by("sport")
        )
        interests = [
            sport_labels.get(sport, sport)
            for sport in sports
            if sport in sport_labels
        ]

    return {
        "events_count": games.count(),
        "playpals_count": count_playpals(user),
        "last_game": last_game,
        "interests": interests,
    }
