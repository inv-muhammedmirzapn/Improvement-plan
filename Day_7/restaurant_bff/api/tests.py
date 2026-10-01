"""
Integration tests for Restaurant BFF.

Tests: menu management, order acceptance, rejection, state transitions,
authorization checks.
"""
import uuid
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient


RESTAURANT_ID = str(uuid.uuid4())
ORDER_ID = str(uuid.uuid4())
ITEM_ID = str(uuid.uuid4())


class RestaurantBFFTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_headers = {'HTTP_X_RESTAURANT_ID': RESTAURANT_ID}

    def test_requires_restaurant_auth(self):
        """Without X-Restaurant-ID header, all endpoints return 401."""
        response = self.client.get('/api/restaurant/orders/')
        self.assertEqual(response.status_code, 401)

    @patch('api.gateway.create_menu_item')
    def test_create_menu_item(self, mock_create):
        mock_create.return_value = {
            'id': ITEM_ID,
            'name': 'Chicken Biryani',
            'price': '250.00',
            'is_available': True,
        }
        response = self.client.post(
            '/api/restaurant/menu-items/',
            data={'name': 'Chicken Biryani', 'price': '250.00'},
            format='json',
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 201)

    @patch('api.gateway.update_menu_item')
    def test_update_menu_item(self, mock_update):
        mock_update.return_value = {'id': ITEM_ID, 'price': '275.00', 'is_available': True}
        response = self.client.patch(
            f'/api/restaurant/menu-items/{ITEM_ID}/',
            data={'price': '275.00'},
            format='json',
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

    @patch('api.gateway.set_item_availability')
    def test_set_item_availability(self, mock_avail):
        mock_avail.return_value = {'id': ITEM_ID, 'is_available': False}
        response = self.client.post(
            f'/api/restaurant/menu-items/{ITEM_ID}/availability/',
            data={'is_available': False},
            format='json',
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

    @patch('api.gateway.get_restaurant_orders')
    def test_list_orders(self, mock_list):
        mock_list.return_value = [{'id': ORDER_ID, 'status': 'PENDING'}]
        response = self.client.get('/api/restaurant/orders/', **self.auth_headers)
        self.assertEqual(response.status_code, 200)

    @patch('api.gateway.accept_order')
    def test_accept_order(self, mock_accept):
        mock_accept.return_value = {'id': ORDER_ID, 'status': 'CONFIRMED'}
        response = self.client.post(
            f'/api/restaurant/orders/{ORDER_ID}/accept/',
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'CONFIRMED')

    @patch('api.gateway.reject_order')
    def test_reject_order(self, mock_reject):
        mock_reject.return_value = {'id': ORDER_ID, 'status': 'REJECTED'}
        response = self.client.post(
            f'/api/restaurant/orders/{ORDER_ID}/reject/',
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'REJECTED')

    @patch('api.gateway.accept_order')
    def test_accept_already_cancelled_returns_409(self, mock_accept):
        from api.gateway import ServiceConflict
        mock_accept.side_effect = ServiceConflict('Cannot transition from CANCELLED to CONFIRMED.')
        response = self.client.post(
            f'/api/restaurant/orders/{ORDER_ID}/accept/',
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 409)

    @patch('api.gateway.start_preparing')
    def test_start_preparing(self, mock_prepare):
        mock_prepare.return_value = {'id': ORDER_ID, 'status': 'PREPARING'}
        response = self.client.post(
            f'/api/restaurant/orders/{ORDER_ID}/preparing/',
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

    @patch('api.gateway.mark_ready')
    def test_mark_ready(self, mock_ready):
        mock_ready.return_value = {'id': ORDER_ID, 'status': 'READY'}
        response = self.client.post(
            f'/api/restaurant/orders/{ORDER_ID}/ready/',
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

    @patch('api.gateway.close_restaurant')
    def test_close_restaurant(self, mock_close):
        mock_close.return_value = {'id': RESTAURANT_ID, 'status': 'CLOSED'}
        response = self.client.post('/api/restaurant/close/', **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'CLOSED')

    @patch('api.gateway.close_restaurant')
    def test_close_restaurant_idempotent(self, mock_close):
        """Calling close twice should not error."""
        mock_close.return_value = {'id': RESTAURANT_ID, 'status': 'CLOSED'}
        self.client.post('/api/restaurant/close/', **self.auth_headers)
        response = self.client.post('/api/restaurant/close/', **self.auth_headers)
        self.assertEqual(response.status_code, 200)
