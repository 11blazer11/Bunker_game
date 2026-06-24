from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Game, GameMessage, PlayerCharacter


class PlayerCharacterRevealTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='player1', password='pass')
        self.game = Game.objects.create()
        self.character = PlayerCharacter.objects.create(
            game=self.game,
            player=self.user,
            age=34,
            gender='female',
            height='175 cm',
            profession='Doctor',
            hobby='Gardening',
            health='Healthy',
            item='Radio',
            special_trait='Calm under pressure',
            phobia='Heights',
            characteristics=[
                ('profession', 'Doctor', 'good'),
                ('hobby', 'Gardening', 'good'),
                ('health', 'Healthy', 'good'),
                ('item', 'Radio', 'good'),
                ('special_trait', 'Calm under pressure', 'good'),
                ('phobia', 'Heights', 'bad'),
            ],
        )

    def test_age_gender_and_height_are_revealable_with_generated_traits(self):
        revealable_types = [
            char_type
            for char_type, _, _ in self.character.get_all_revealable_characteristics()
        ]

        self.assertEqual(
            revealable_types,
            [
                'age',
                'gender',
                'height',
                'profession',
                'hobby',
                'health',
                'item',
                'special_trait',
                'phobia',
            ],
        )

    def test_base_traits_are_hidden_until_revealed(self):
        self.assertIn(('age', 34, 'neutral'), self.character.get_unrevealed_characteristics())
        self.assertNotIn(('age', 34, 'neutral'), self.character.get_revealed_characteristics())

        self.character.reveal_characteristic('age')

        self.assertNotIn(('age', 34, 'neutral'), self.character.get_unrevealed_characteristics())
        self.assertIn(('age', 34, 'neutral'), self.character.get_revealed_characteristics())


class RevealCircleFlowTests(TestCase):
    characteristics = [
        ('profession', 'Doctor', 'good'),
        ('hobby', 'Gardening', 'good'),
        ('health', 'Healthy', 'good'),
        ('item', 'Radio', 'good'),
        ('special_trait', 'Calm under pressure', 'good'),
        ('phobia', 'Heights', 'bad'),
    ]
    reveal_order = [
        'age',
        'gender',
        'height',
        'profession',
        'hobby',
        'health',
        'item',
        'special_trait',
        'phobia',
    ]

    def create_character(self, username, revealed_characteristics):
        user = User.objects.create_user(username=username, password='pass')
        return PlayerCharacter.objects.create(
            game=self.game,
            player=user,
            age=34,
            gender='female',
            height='175 cm',
            profession='Doctor',
            hobby='Gardening',
            health='Healthy',
            item='Radio',
            special_trait='Calm under pressure',
            phobia='Heights',
            characteristics=self.characteristics,
            revealed_characteristics=revealed_characteristics,
        )

    def setUp(self):
        self.game = Game.objects.create(round_number=8)

    def test_vote_starts_after_circle_when_players_still_have_hidden_traits(self):
        current = self.create_character('player1', self.reveal_order[:7])
        self.create_character('player2', self.reveal_order[:8])
        self.create_character('player3', self.reveal_order[:8])
        self.client.force_login(current.player)

        self.client.post(
            reverse('reveal_characteristic', args=[self.game.id]),
            {'char_type': 'special_trait'},
        )

        self.game.refresh_from_db()
        self.assertEqual(self.game.game_phase, 'voting')
        self.assertTrue(GameMessage.objects.filter(game=self.game, text='__VOTE_START__').exists())

    def test_vote_does_not_restart_after_final_traits_are_fully_revealed(self):
        self.game.round_number = 9
        self.game.save()
        current = self.create_character('player1', self.reveal_order[:8])
        self.create_character('player2', self.reveal_order)
        self.client.force_login(current.player)

        self.client.post(
            reverse('reveal_characteristic', args=[self.game.id]),
            {'char_type': 'phobia'},
        )

        self.game.refresh_from_db()
        self.assertEqual(self.game.game_phase, 'revealing')
        self.assertFalse(GameMessage.objects.filter(game=self.game, text='__VOTE_START__').exists())
