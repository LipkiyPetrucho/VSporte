from django.contrib.auth.models import User
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
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


def search_users(query, queryset=None):
    """Searches for users by first name, last name or login (case insensitive)
    using trigrams.
    Returns users by partial match with the query.
    """
    qs = queryset if queryset is not None else User.objects.all()
    search_query = (
        TrigramSimilarity("username", query)
        + TrigramSimilarity("first_name", query)
        + TrigramSimilarity("last_name", query)
    )
    return (
        qs.annotate(similarity=search_query)
        .filter(similarity__gt=0.1)
        .order_by("-similarity")
    )


def get_coplayed_user_ids(user):
    """Users who participated in the same games as the given user."""
    my_games = Game.objects.filter(Q(joined_players=user) | Q(user=user))
    return set(
        User.objects.filter(
            Q(joined_games__in=my_games) | Q(user_games_created__in=my_games)
        )
        .exclude(pk=user.pk)
        .distinct()
        .values_list("pk", flat=True)
    )


def get_friendship_statuses_for_users(viewer, others):
    """Статусы дружбы viewer→other одним запросом. Ключ — pk другого пользователя."""
    other_ids = [user.pk for user in others if user.pk != viewer.pk]
    if not other_ids:
        return {}

    rows = Friendship.objects.filter(
        Q(from_user=viewer, to_user_id__in=other_ids)
        | Q(to_user=viewer, from_user_id__in=other_ids)
    ).values("from_user_id", "to_user_id", "status")

    friends = set()
    pending_sent = set()
    pending_received = set()
    for row in rows:
        other_id = (
            row["to_user_id"]
            if row["from_user_id"] == viewer.pk
            else row["from_user_id"]
        )
        if row["status"] == Friendship.ACCEPTED:
            friends.add(other_id)
        elif row["status"] == Friendship.PENDING:
            if row["from_user_id"] == viewer.pk:
                pending_sent.add(other_id)
            else:
                pending_received.add(other_id)

    statuses = {}
    for pk in other_ids:
        if pk in friends:
            statuses[pk] = "friends"
        elif pk in pending_sent:
            statuses[pk] = "pending_sent"
        elif pk in pending_received:
            statuses[pk] = "pending_received"
        else:
            statuses[pk] = "none"
    return statuses


def get_friendship_status(viewer, other):
    if viewer.pk == other.pk:
        return "self"
    return get_friendship_statuses_for_users(viewer, [other]).get(other.pk, "none")


def apply_played_filter(queryset, user, played_filter):
    if played_filter not in ("played", "not_played"):
        return queryset
    coplayed_ids = get_coplayed_user_ids(user)
    if played_filter == "played":
        return queryset.filter(pk__in=coplayed_ids)
    return queryset.exclude(pk__in=coplayed_ids)


def get_user_games(user):
    return Game.objects.filter(Q(joined_players=user) | Q(user=user)).distinct()


def get_friend_users(user):
    friend_ids = set()
    for from_id, to_id in Friendship.objects.filter(
        Q(from_user=user, status=Friendship.ACCEPTED)
        | Q(to_user=user, status=Friendship.ACCEPTED)
    ).values_list("from_user_id", "to_user_id"):
        friend_ids.add(to_id if from_id == user.pk else from_id)
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


def count_outgoing_friend_requests(user):
    return Friendship.objects.filter(
        from_user=user, status=Friendship.PENDING
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
    games = list(get_user_games(user).order_by("-start_time"))
    now = timezone.now()
    last_game = next((game for game in games if game.start_time <= now), None)
    sport_labels = {**dict(Game.SPORTS), **INTEREST_LABELS}

    if profile.interests:
        interests = [
            sport_labels.get(sport, sport)
            for sport in profile.interests
            if sport in sport_labels
        ]
    else:
        sports = sorted(
            {
                game.sport
                for game in games
                if game.sport in sport_labels
            }
        )
        interests = [sport_labels[sport] for sport in sports]

    return {
        "events_count": len(games),
        "playpals_count": count_playpals(user),
        "last_game": last_game,
        "interests": interests,
    }
