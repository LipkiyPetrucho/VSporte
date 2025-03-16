from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from freezegun import freeze_time
from .models import Game
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
