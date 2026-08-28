from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from account.models import Profile
from games.models import Game, GameMessage
from notifications.models import Notification
from notifications.services import notify_game_chat_message, notify_game_updated

User = get_user_model()


class BulkNotificationTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="notify_org", password="testpass123"
        )
        Profile.objects.get_or_create(user=self.organizer)
        self.player_one = User.objects.create_user(
            username="notify_p1", password="testpass123"
        )
        Profile.objects.get_or_create(user=self.player_one)
        self.player_two = User.objects.create_user(
            username="notify_p2", password="testpass123"
        )
        Profile.objects.get_or_create(user=self.player_two)

        self.game = Game.objects.create(
            user=self.organizer,
            sport="football",
            place="Notify Place",
            start_time=timezone.now() + timedelta(hours=2),
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
        )
        self.game.joined_players.add(
            self.organizer, self.player_one, self.player_two
        )

    def test_chat_notifications_use_single_insert(self):
        message = GameMessage.objects.create(
            game=self.game,
            author=self.organizer,
            text="Привет",
        )
        message = (
            GameMessage.objects.select_related(
                "author",
                "author__profile",
                "game",
                "game__user",
                "game__user__profile",
            )
            .prefetch_related("game__joined_players__profile")
            .get(pk=message.pk)
        )

        with CaptureQueriesContext(connection) as ctx:
            notify_game_chat_message(message)

        inserts = [
            query["sql"]
            for query in ctx.captured_queries
            if query["sql"].lstrip().upper().startswith("INSERT")
        ]
        self.assertEqual(len(inserts), 1)
        self.assertEqual(
            Notification.objects.filter(
                notification_type=Notification.TYPE_CHAT_MESSAGE
            ).count(),
            2,
        )
        recipient_ids = set(
            Notification.objects.values_list("recipient_id", flat=True)
        )
        self.assertEqual(recipient_ids, {self.player_one.pk, self.player_two.pk})

    def test_game_updated_skips_duplicates_within_a_minute(self):
        notify_game_updated(self.game, self.organizer)
        notify_game_updated(self.game, self.organizer)
        self.assertEqual(
            Notification.objects.filter(
                notification_type=Notification.TYPE_GAME_UPDATED
            ).count(),
            2,
        )


class NotificationListQueryTests(TestCase):
    def setUp(self):
        self.recipient = User.objects.create_user(
            username="notify_list_user", password="testpass123"
        )
        Profile.objects.get_or_create(user=self.recipient)
        self.actor = User.objects.create_user(
            username="notify_list_actor", password="testpass123"
        )
        Profile.objects.get_or_create(user=self.actor)

    def test_list_prefetches_game_targets(self):
        from django.urls import reverse

        games = []
        for index in range(5):
            game = Game.objects.create(
                user=self.actor,
                sport="football",
                place=f"Notify List {index}",
                start_time=timezone.now() + timedelta(hours=2 + index),
                duration=timedelta(hours=1),
                price=100,
                max_players=10,
            )
            games.append(game)
            Notification.objects.create(
                recipient=self.recipient,
                actor=self.actor,
                notification_type=Notification.TYPE_GAME_UPDATED,
                target=game,
            )

        self.client.force_login(self.recipient)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["notifications"]), 5)

        game_selects = [
            query["sql"]
            for query in ctx.captured_queries
            if query["sql"].lstrip().upper().startswith("SELECT")
            and "FROM" in query["sql"].upper()
            and "games_game" in query["sql"]
            and "games_game_joined_players" not in query["sql"]
        ]
        self.assertEqual(len(game_selects), 1)
        self.assertIn(" IN (", game_selects[0].upper())
