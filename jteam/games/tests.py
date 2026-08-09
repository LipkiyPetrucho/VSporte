from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import timedelta
from freezegun import freeze_time
import json
from account.models import Profile
from .models import Game, GameTeamAssignment
from .tasks import update_game_status

class GameStatusUpdateTest(TestCase):
    def setUp(self):
        """Создаем тестовые данные"""
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Игра, которая должна начаться (время начала в прошлом)
        self.game_to_start = Game.objects.create(
            user=self.user,
            sport='football',
            place='Test Place 1',
            start_time=timezone.now() - timedelta(minutes=5),
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
            status='open'
        )
        
        # Игра, которая должна закончиться (время начала + длительность в прошлом)
        past_time = timezone.now() - timedelta(hours=2)
        self.game_to_finish = Game.objects.create(
            user=self.user,
            sport='football',
            place='Test Place 2',
            start_time=past_time,
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
            status='started'
        )
        
        # Игра, которая еще не должна начаться (время начала в будущем)
        self.future_game = Game.objects.create(
            user=self.user,
            sport='football',
            place='Test Place 3',
            start_time=timezone.now() + timedelta(hours=1),
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
            status='open'
        )

    def test_game_status_update(self):
        """Тест обновления статусов игр"""
        # Запускаем задачу обновления статусов
        update_game_status()
        
        # Перезагружаем объекты из базы данных
        self.game_to_start.refresh_from_db()
        self.game_to_finish.refresh_from_db()
        self.future_game.refresh_from_db()
        
        # Проверяем, что статусы обновились правильно
        self.assertEqual(self.game_to_start.status, 'started', 
                        'Игра в прошлом должна иметь статус "started"')
        
        self.assertEqual(self.game_to_finish.status, 'finished', 
                        'Законченная игра должна иметь статус "finished"')
        
        self.assertEqual(self.future_game.status, 'open', 
                        'Будущая игра должна остаться со статусом "open"')

    def test_status_transitions(self):
        """Тест последовательного изменения статусов"""
        current_time = timezone.now()
        
        # Создаем игру, которая начнется через минуту
        game = Game.objects.create(
            user=self.user,
            sport='football',
            place='Test Place 4',
            start_time=current_time + timedelta(minutes=1),
            duration=timedelta(minutes=2),
            price=100,
            max_players=10,
            status='open'
        )
        
        # Проверяем начальный статус
        self.assertEqual(game.status, 'open')
        
        # Перемещаемся на 2 минуты вперед (игра должна начаться)
        with freeze_time(current_time + timedelta(minutes=2)):
            update_game_status()
            game.refresh_from_db()
            self.assertEqual(game.status, 'started')
        
        # Перемещаемся еще на 2 минуты вперед (игра должна закончиться)
        with freeze_time(current_time + timedelta(minutes=4)):
            update_game_status()
            game.refresh_from_db()
            self.assertEqual(game.status, 'finished')

    def test_edge_cases(self):
        """Тест граничных случаев"""
        current_time = timezone.now()
        
        # Игра, которая начинается прямо сейчас
        game_now = Game.objects.create(
            user=self.user,
            sport='football',
            place='Test Place 5',
            start_time=current_time,
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
            status='open'
        )
        
        # Игра с нулевой продолжительностью
        game_zero_duration = Game.objects.create(
            user=self.user,
            sport='football',
            place='Test Place 6',
            start_time=current_time - timedelta(minutes=1),
            duration=timedelta(0),
            price=100,
            max_players=10,
            status='started'
        )
        
        update_game_status()
        game_now.refresh_from_db()
        game_zero_duration.refresh_from_db()
        
        self.assertEqual(game_now.status, 'started')
        self.assertEqual(game_zero_duration.status, 'finished')

    def test_game_sync_status_method(self):
        """Синхронизация статуса отдельной игры без Celery."""
        past_game = Game.objects.create(
            user=self.user,
            sport='football',
            place='Test Place 7',
            start_time=timezone.now() - timedelta(hours=2),
            duration=timedelta(minutes=30),
            price=100,
            max_players=10,
            status='open',
        )
        past_game.sync_status()
        self.assertEqual(past_game.status, 'finished')


class GameTeamsApiTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organizer = User.objects.create_user(
            username="organizer",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.organizer)

        self.player = User.objects.create_user(
            username="player1",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.player)

        self.outsider = User.objects.create_user(
            username="outsider",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.outsider)

        self.game = Game.objects.create(
            user=self.organizer,
            sport="football",
            place="Test Arena",
            start_time=timezone.now() + timedelta(hours=2),
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
            extra_players=2,
            is_team_game=True,
            status="open",
            slug="football-test-teams",
        )
        self.game.joined_players.add(self.organizer, self.player)
        self.teams_url = reverse(
            "games:teams",
            args=[self.game.pk, self.game.slug],
        )

    def _post_teams(self, payload, user=None):
        self.client.force_login(user or self.organizer)
        return self.client.post(
            self.teams_url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_assign_and_unassign_user(self):
        response = self._post_teams({"user_id": self.player.pk, "team": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(
            GameTeamAssignment.objects.filter(
                game=self.game,
                user=self.player,
                team=1,
            ).exists()
        )
        team_a_ids = [e["user_id"] for e in data["team_roster"]["teams"]["1"]]
        self.assertIn(self.player.pk, team_a_ids)

        response = self._post_teams({"user_id": self.player.pk, "team": None})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(
            GameTeamAssignment.objects.filter(
                game=self.game,
                user=self.player,
            ).exists()
        )
        bench_ids = [
            e["user_id"]
            for e in data["team_roster"]["bench"]
            if e["type"] == "user"
        ]
        self.assertIn(self.player.pk, bench_ids)

    def test_assign_offline_slot(self):
        response = self._post_teams({"offline_slot": 0, "team": 2})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(
            GameTeamAssignment.objects.filter(
                game=self.game,
                offline_slot=0,
                team=2,
            ).exists()
        )
        team_b = data["team_roster"]["teams"]["2"]
        self.assertTrue(any(e.get("offline_slot") == 0 for e in team_b))

    def test_unassign_offline_slot(self):
        self._post_teams({"offline_slot": 1, "team": 1})
        response = self._post_teams({"offline_slot": 1, "team": None})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertFalse(
            GameTeamAssignment.objects.filter(
                game=self.game,
                offline_slot=1,
            ).exists()
        )
        bench_slots = [
            e["offline_slot"]
            for e in data["team_roster"]["bench"]
            if e["type"] == "offline"
        ]
        self.assertIn(1, bench_slots)

    def test_reassign_user_between_teams(self):
        self._post_teams({"user_id": self.player.pk, "team": 1})
        response = self._post_teams({"user_id": self.player.pk, "team": 2})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        assignment = GameTeamAssignment.objects.get(
            game=self.game,
            user=self.player,
        )
        self.assertEqual(assignment.team, 2)
        self.assertEqual(
            GameTeamAssignment.objects.filter(
                game=self.game,
                user=self.player,
            ).count(),
            1,
        )
        team_b_ids = [e["user_id"] for e in data["team_roster"]["teams"]["2"]]
        self.assertIn(self.player.pk, team_b_ids)

    def test_leave_clears_assignment(self):
        GameTeamAssignment.objects.create(
            game=self.game,
            user=self.player,
            team=1,
        )
        self.client.force_login(self.player)
        response = self.client.post(
            reverse("games:join"),
            {"id": self.game.pk, "action": "leave"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertFalse(
            GameTeamAssignment.objects.filter(
                game=self.game,
                user=self.player,
            ).exists()
        )

    def test_extra_players_trim_clears_offline_assignments(self):
        GameTeamAssignment.objects.create(
            game=self.game,
            offline_slot=1,
            team=1,
        )
        GameTeamAssignment.objects.create(
            game=self.game,
            offline_slot=0,
            team=2,
        )
        self.client.force_login(self.organizer)
        response = self.client.post(
            reverse(
                "games:organizer_settings",
                args=[self.game.pk, self.game.slug],
            ),
            {"extra_players": "1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["extra_players"], 1)
        self.assertFalse(
            GameTeamAssignment.objects.filter(
                game=self.game,
                offline_slot=1,
            ).exists()
        )
        self.assertTrue(
            GameTeamAssignment.objects.filter(
                game=self.game,
                offline_slot=0,
            ).exists()
        )
        self.assertIn("team_roster", data)

    def test_non_organizer_forbidden(self):
        response = self._post_teams(
            {"user_id": self.player.pk, "team": 1},
            user=self.player,
        )
        self.assertEqual(response.status_code, 403)

    def test_rejects_non_joined_user(self):
        response = self._post_teams({"user_id": self.outsider.pk, "team": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertFalse(
            GameTeamAssignment.objects.filter(
                game=self.game,
                user=self.outsider,
            ).exists()
        )

    def test_rejects_when_not_team_game(self):
        self.game.is_team_game = False
        self.game.save(update_fields=["is_team_game"])
        response = self._post_teams({"user_id": self.player.pk, "team": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")

    def test_rejects_offline_slot_out_of_range(self):
        response = self._post_teams({"offline_slot": 2, "team": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertFalse(
            GameTeamAssignment.objects.filter(
                game=self.game,
                offline_slot=2,
            ).exists()
        )


class GameChatAccessTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organizer = User.objects.create_user(
            username="chat_org",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.organizer)

        self.player = User.objects.create_user(
            username="chat_player",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.player)

        self.outsider = User.objects.create_user(
            username="chat_outsider",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.outsider)

        self.game = Game.objects.create(
            user=self.organizer,
            sport="football",
            place="Chat Arena",
            start_time=timezone.now() + timedelta(hours=2),
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
            status="open",
            slug="football-test-chat",
        )
        self.game.joined_players.add(self.organizer, self.player)
        self.chat_url = reverse(
            "games:chat",
            args=[self.game.pk, self.game.slug],
        )
        self.messages_url = reverse(
            "games:chat_messages",
            args=[self.game.pk, self.game.slug],
        )

    def test_participant_can_open_chat(self):
        self.client.force_login(self.player)
        response = self.client.get(self.chat_url)
        self.assertEqual(response.status_code, 200)

    def test_outsider_redirected_from_chat(self):
        self.client.force_login(self.outsider)
        response = self.client.get(self.chat_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.game.get_absolute_url())

    def test_outsider_messages_api_forbidden(self):
        self.client.force_login(self.outsider)
        response = self.client.get(self.messages_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "error")


class GameRemovePlayerTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organizer = User.objects.create_user(
            username="remove_org",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.organizer)

        self.player = User.objects.create_user(
            username="remove_player",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.player)

        self.outsider = User.objects.create_user(
            username="remove_outsider",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.outsider)

        self.game = Game.objects.create(
            user=self.organizer,
            sport="football",
            place="Remove Arena",
            start_time=timezone.now() + timedelta(hours=2),
            duration=timedelta(hours=1),
            price=100,
            max_players=10,
            is_team_game=True,
            status="open",
            slug="football-test-remove",
        )
        self.game.joined_players.add(self.organizer, self.player)
        GameTeamAssignment.objects.create(
            game=self.game,
            user=self.player,
            team=1,
        )
        self.join_url = reverse("games:join")

    def _remove(self, user_id, as_user=None):
        self.client.force_login(as_user or self.organizer)
        return self.client.post(
            self.join_url,
            {
                "id": self.game.pk,
                "action": "remove_player",
                "user_id": user_id,
            },
        )

    def test_organizer_can_remove_player(self):
        from notifications.models import Notification

        response = self._remove(self.player.pk)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertFalse(
            self.game.joined_players.filter(pk=self.player.pk).exists()
        )
        self.assertFalse(
            GameTeamAssignment.objects.filter(
                game=self.game,
                user=self.player,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.player,
                actor=self.organizer,
                notification_type=Notification.TYPE_GAME_PLAYER_REMOVED,
            ).exists()
        )

    def test_cannot_remove_organizer(self):
        response = self._remove(self.organizer.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertTrue(
            self.game.joined_players.filter(pk=self.organizer.pk).exists()
        )

    def test_non_organizer_forbidden(self):
        response = self._remove(self.player.pk, as_user=self.outsider)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertTrue(
            self.game.joined_players.filter(pk=self.player.pk).exists()
        )
