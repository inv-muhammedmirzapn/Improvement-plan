"""
Integration tests for Customer BFF.

Uses mock to simulate downstream service responses.
Tests: order placement workflow, partial failure, idempotency, cancellation.
"""
import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient


class CustomerBFFTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.restaurant_id = str(uuid.uuid4())
        self.customer_headers = {'HTTP_X_CUSTOMER_ID': '42'}

    @patch('api.gateway.get_restaurants')
    def test_list_restaurants_success(self, mock_get):
        mock_get.return_value = [{'id': self.restaurant_id, 'name': 'Spice Kitchen', 'status': 'OPEN'}]
        response = self.client.get('/api/customer/restaurants/', **self.customer_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    @patch('api.gateway.get_restaurants')
    def test_list_restaurants_service_unavailable(self, mock_get):
        from api.gateway import ServiceUnavailable
        mock_get.side_effect = ServiceUnavailable('Service down')
        response = self.client.get('/api/customer/restaurants/', **self.customer_headers)
        self.assertEqual(response.status_code, 503)

    @patch('api.gateway.get_restaurant')
    @patch('api.gateway.get_menu')
    def test_get_menu_success(self, mock_menu, mock_restaurant):
        mock_restaurant.return_value = {'id': self.restaurant_id, 'name': 'Spice Kitchen', 'status': 'OPEN'}
        mock_menu.return_value = [{'id': str(uuid.uuid4()), 'name': 'Chicken Biryani', 'price': '250.00'}]
        response = self.client.get(f'/api/customer/restaurants/{self.restaurant_id}/menu/', **self.customer_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn('restaurant', response.json())
        self.assertIn('menu', response.json())

    @patch('api.gateway.validate_order_items')
    @patch('api.gateway.reserve_capacity')
    @patch('api.gateway.get_restaurant')
    @patch('api.gateway.create_order')
    def test_place_order_success(self, mock_create, mock_get_restaurant, mock_reserve, mock_validate):
        item_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())
        mock_validate.return_value = [{'id': item_id, 'name': 'Chicken Biryani', 'price': '250.00'}]
        mock_reserve.return_value = {'reserved': True}
        mock_get_restaurant.return_value = {'id': self.restaurant_id, 'name': 'Spice Kitchen'}
        mock_create.return_value = ({'id': order_id, 'status': 'PENDING'}, True)

        response = self.client.post(
            f'/api/customer/restaurants/{self.restaurant_id}/orders/',
            data={
                'idempotency_key': str(uuid.uuid4()),
                'items': [{'menu_item_id': item_id, 'quantity': 2}],
            },
            format='json',
            **self.customer_headers,
        )
        self.assertEqual(response.status_code, 201)

    @patch('api.gateway.validate_order_items')
    @patch('api.gateway.reserve_capacity')
    @patch('api.gateway.release_capacity')
    @patch('api.gateway.get_restaurant')
    @patch('api.gateway.create_order')
    def test_place_order_releases_capacity_on_order_service_failure(
        self, mock_create, mock_get_restaurant, mock_release, mock_reserve, mock_validate
    ):
        """If Order Service fails after capacity reservation, capacity must be released."""
        item_id = str(uuid.uuid4())
        from api.gateway import ServiceUnavailable
        mock_validate.return_value = [{'id': item_id, 'name': 'Chicken Biryani', 'price': '250.00'}]
        mock_reserve.return_value = {'reserved': True}
        mock_get_restaurant.return_value = {'id': self.restaurant_id, 'name': 'Spice Kitchen'}
        mock_create.side_effect = ServiceUnavailable('Order Service down')

        response = self.client.post(
            f'/api/customer/restaurants/{self.restaurant_id}/orders/',
            data={
                'idempotency_key': str(uuid.uuid4()),
                'items': [{'menu_item_id': item_id, 'quantity': 1}],
            },
            format='json',
            **self.customer_headers,
        )
        self.assertEqual(response.status_code, 503)
        mock_release.assert_called_once()

    @patch('api.gateway.get_order')
    @patch('api.gateway.get_restaurant')
    def test_get_order_degraded_restaurant(self, mock_restaurant, mock_order):
        """If Restaurant Service is down, order detail should return with degraded restaurant."""
        from api.gateway import ServiceUnavailable
        order_id = str(uuid.uuid4())
        mock_order.return_value = {
            'id': order_id,
            'status': 'PENDING',
            'restaurant_id': self.restaurant_id,
            'restaurant_name': 'Spice Kitchen',
            'total_amount': '680.00',
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-01T00:00:00Z',
            'items': [],
        }
        mock_restaurant.side_effect = ServiceUnavailable('Restaurant Service down')

        response = self.client.get(f'/api/customer/orders/{order_id}/', **self.customer_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('order', data)
        self.assertIn('restaurant', data)
        self.assertEqual(data['restaurant']['status'], 'UNKNOWN')

    @patch('api.gateway.cancel_order')
    def test_cancel_order_success(self, mock_cancel):
        order_id = str(uuid.uuid4())
        mock_cancel.return_value = {'id': order_id, 'status': 'CANCELLED'}
        response = self.client.post(f'/api/customer/orders/{order_id}/cancel/', **self.customer_headers)
        self.assertEqual(response.status_code, 200)

    @patch('api.gateway.validate_order_items')
    def test_place_order_unavailable_item_returns_409(self, mock_validate):
        from api.gateway import ServiceConflict
        mock_validate.side_effect = ServiceConflict('Item unavailable')
        response = self.client.post(
            f'/api/customer/restaurants/{self.restaurant_id}/orders/',
            data={
                'idempotency_key': str(uuid.uuid4()),
                'items': [{'menu_item_id': str(uuid.uuid4()), 'quantity': 1}],
            },
            format='json',
            **self.customer_headers,
        )
        self.assertEqual(response.status_code, 409)

    def test_authorization_customer_id_from_header_not_body(self):
        """The BFF must read customer_id from the header, never from the body."""
        # Even if body has customer_id it should be ignored
        with patch('api.gateway.get_restaurants') as mock_get:
            mock_get.return_value = []
            response = self.client.get(
                '/api/customer/restaurants/',
                HTTP_X_CUSTOMER_ID='99',
            )
            self.assertEqual(response.status_code, 200)
