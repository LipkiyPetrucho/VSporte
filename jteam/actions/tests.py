from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from actions.models import Action
from actions.utils import create_action
from games.models import Game

User = get_user_model()


class CreateActionQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="actor", password="testpass123"
        )
        self.game = Game.objects.create(
            user=self.user,
            sport="football",
            place="Action Place",
            start_time=timezone.now() + timedelta(hours=2),
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
        )

    def test_create_action_deduplicates_within_a_minute(self):
        self.assertTrue(create_action(self.user, "создал(а) игру", self.game))
        self.assertFalse(create_action(self.user, "создал(а) игру", self.game))
        self.assertEqual(Action.objects.count(), 1)

    def test_similar_action_uses_exists_not_full_fetch(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        create_action(self.user, "создал(а) игру", self.game)
        with CaptureQueriesContext(connection) as ctx:
            created = create_action(self.user, "создал(а) игру", self.game)

        self.assertFalse(created)
        inserts = [
            query["sql"]
            for query in ctx.captured_queries
            if query["sql"].lstrip().upper().startswith("INSERT")
        ]
        self.assertEqual(inserts, [])
        action_selects = [
            query["sql"]
            for query in ctx.captured_queries
            if "actions_action" in query["sql"]
            and query["sql"].lstrip().upper().startswith("SELECT")
        ]
        self.assertEqual(len(action_selects), 1)
        self.assertIn("LIMIT 1", action_selects[0].upper())
