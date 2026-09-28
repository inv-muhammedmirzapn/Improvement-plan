from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import ProductStock, StockReservation
from .services import (
    DuplicateOrder,
    OutOfStock,
    StockDiscontinued,
    StockNotFound,
    reserve_stock,
)
from .tasks import generate_packing_slip, notify_wms


class SoftDeleteManagerTests(TestCase):
    def setUp(self):
        self.stock = ProductStock.objects.create(sku="SKU-SOFT-1", available_quantity=100)
        self.res1 = StockReservation.objects.create(
            stock=self.stock, quantity=5, order_reference="ORD-001"
        )
        self.res2 = StockReservation.objects.create(
            stock=self.stock, quantity=10, order_reference="ORD-002"
        )

    def test_default_queryset_excludes_soft_deleted(self):
        self.assertEqual(StockReservation.objects.count(), 2)

        # Soft delete single instance
        self.res1.delete()
        self.res1.refresh_from_db()
        self.assertTrue(self.res1.is_deleted)

        # Default manager should exclude it
        self.assertEqual(StockReservation.objects.count(), 1)
        self.assertNotIn(self.res1, StockReservation.objects.all())

        # with_deleted access path returns all records
        self.assertEqual(StockReservation.objects.with_deleted.count(), 2)
        self.assertIn(self.res1, StockReservation.objects.with_deleted.all())

    def test_bulk_soft_delete(self):
        StockReservation.objects.filter(stock=self.stock).delete()
        self.assertEqual(StockReservation.objects.count(), 0)
        self.assertEqual(StockReservation.objects.with_deleted.count(), 2)

    def test_hard_delete(self):
        self.res1.hard_delete()
        self.assertEqual(StockReservation.objects.with_deleted.count(), 1)


class StockReservationServiceTests(TestCase):
    def setUp(self):
        self.stock = ProductStock.objects.create(sku="SKU-TEST-1", available_quantity=10)

    @patch("core.services.notify_wms.delay")
    @patch("core.services.generate_packing_slip.delay")
    def test_reserve_stock_success(self, mock_slip_delay, mock_wms_delay):
        with self.captureOnCommitCallbacks(execute=True):
            res = reserve_stock(sku="SKU-TEST-1", quantity=3, order_reference="ORD-100")
        self.stock.refresh_from_db()

        self.assertEqual(self.stock.available_quantity, 7)
        self.assertEqual(res.quantity, 3)
        self.assertEqual(res.order_reference, "ORD-100")

        # Verify on_commit callbacks fired with primitive id
        mock_wms_delay.assert_called_once_with(str(res.id))
        mock_slip_delay.assert_called_once_with(str(res.id))

    @patch("core.services.notify_wms.delay")
    @patch("core.services.generate_packing_slip.delay")
    def test_reserve_stock_out_of_stock(self, mock_slip_delay, mock_wms_delay):
        with self.assertRaises(OutOfStock):
            reserve_stock(sku="SKU-TEST-1", quantity=15, order_reference="ORD-101")

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.available_quantity, 10)
        mock_wms_delay.assert_not_called()
        mock_slip_delay.assert_not_called()

    def test_reserve_stock_discontinued(self):
        self.stock.is_discontinued = True
        self.stock.save()

        with self.assertRaises(StockDiscontinued):
            reserve_stock(sku="SKU-TEST-1", quantity=2, order_reference="ORD-102")

    def test_reserve_stock_not_found(self):
        with self.assertRaises(StockNotFound):
            reserve_stock(sku="NON-EXISTENT", quantity=1, order_reference="ORD-103")

    def test_reserve_stock_duplicate_order(self):
        reserve_stock(sku="SKU-TEST-1", quantity=2, order_reference="ORD-DUP")
        with self.assertRaises(DuplicateOrder):
            reserve_stock(sku="SKU-TEST-1", quantity=2, order_reference="ORD-DUP")


class ConcurrencyStockReservationTests(TransactionTestCase):
    """
    Uses TransactionTestCase so transactions actually commit to the DB,
    enabling multi-threaded concurrency testing.
    """

    def setUp(self):
        self.stock = ProductStock.objects.create(sku="SKU-CONCURRENT", available_quantity=10)

    def tearDown(self):
        StockReservation.objects.with_deleted.all().hard_delete()
        ProductStock.objects.all().delete()

    @patch("core.services.notify_wms.delay")
    @patch("core.services.generate_packing_slip.delay")
    def test_two_concurrent_requests_for_eight_units(self, mock_slip, mock_wms):
        """
        Warehouse has 10 units. Two concurrent requests each ask for 8 units.
        Exactly one must succeed (stock reduced to 2), and the other must fail with OutOfStock.
        """
        results = []

        def attempt_reservation(order_ref):
            # Close connection per thread to ensure separate DB connections
            connection.close()
            try:
                res = reserve_stock(sku="SKU-CONCURRENT", quantity=8, order_reference=order_ref)
                results.append(("SUCCESS", res))
            except OutOfStock:
                results.append(("OUT_OF_STOCK", None))
            except Exception as e:
                results.append(("ERROR", str(e)))
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(attempt_reservation, "ORD-CONC-1")
            f2 = executor.submit(attempt_reservation, "ORD-CONC-2")
            f1.result()
            f2.result()

        successes = [r for r in results if r[0] == "SUCCESS"]
        out_of_stocks = [r for r in results if r[0] == "OUT_OF_STOCK"]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(out_of_stocks), 1)

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.available_quantity, 2)


class ReserveStockAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.stock = ProductStock.objects.create(sku="SKU-API-1", available_quantity=10)

    @patch("core.services.notify_wms.delay")
    @patch("core.services.generate_packing_slip.delay")
    def test_api_reserve_success(self, mock_slip, mock_wms):
        resp = self.client.post(
            "/api/stock/SKU-API-1/reserve/",
            {"quantity": 4, "order_reference": "ORD-API-1"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("reservation_id", resp.data)
        self.assertEqual(resp.data["quantity"], 4)
        self.assertEqual(resp.data["order_reference"], "ORD-API-1")

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.available_quantity, 6)

    def test_api_reserve_out_of_stock(self):
        resp = self.client.post(
            "/api/stock/SKU-API-1/reserve/",
            {"quantity": 20, "order_reference": "ORD-API-2"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data, {"error": "out of stock"})

    def test_api_reserve_not_found(self):
        resp = self.client.post(
            "/api/stock/SKU-UNKNOWN/reserve/",
            {"quantity": 1, "order_reference": "ORD-API-3"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.data, {"error": "sku not found"})

    def test_api_reserve_discontinued(self):
        self.stock.is_discontinued = True
        self.stock.save()

        resp = self.client.post(
            "/api/stock/SKU-API-1/reserve/",
            {"quantity": 1, "order_reference": "ORD-API-4"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp.data, {"error": "Product Discontinued"})


class BackgroundTasksTests(TestCase):
    def setUp(self):
        self.stock = ProductStock.objects.create(sku="SKU-TASK-1", available_quantity=50)
        self.reservation = StockReservation.objects.create(
            stock=self.stock, quantity=5, order_reference="ORD-TASK-1"
        )

    @patch("requests.post")
    def test_notify_wms_success(self, mock_post):
        mock_post.return_value.raise_for_status.return_value = None

        notify_wms(str(self.reservation.id))

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        self.assertEqual(call_kwargs["headers"]["Idempotency-Key"], str(self.reservation.id))
        self.assertEqual(call_kwargs["json"]["sku"], "SKU-TASK-1")
        self.assertEqual(call_kwargs["json"]["quantity"], 5)

    def test_generate_packing_slip_creates_pdf_and_is_idempotent(self):
        path = f"packing_slips/{self.reservation.order_reference}.pdf"
        if default_storage.exists(path):
            default_storage.delete(path)

        # First run generates PDF
        saved_path = generate_packing_slip(str(self.reservation.id))
        self.assertEqual(saved_path, path)
        self.assertTrue(default_storage.exists(path))

        # Second run should return existing path without recreating
        second_path = generate_packing_slip(str(self.reservation.id))
        self.assertEqual(second_path, path)

        # Cleanup
        default_storage.delete(path)
