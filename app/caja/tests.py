"""Tests del módulo Caja (cobro POS)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app.orders.models import Order, OrderItem
from app.products.models import Category, Product


class CajaTests(TestCase):
    def setUp(self):
        self.emp = User.objects.create_user(username='cajero', password='pass1234')
        cat = Category.objects.create(cate_nombre='Bebidas')
        self.p = Product.objects.create(prod_nombre='Cola', prod_categoria=cat, prod_precio=Decimal('1.00'))
        self.client.login(username='cajero', password='pass1234')

    def _pedido_pendiente(self, **extra):
        pedido = Order.objects.create(pedi_vendedor=self.emp, **extra)
        OrderItem.objects.create(
            deta_pedido=pedido, deta_producto=self.p, deta_cantidad=2, deta_precio_unitario=self.p.prod_precio,
        )
        pedido.recalcular_totales()
        return pedido

    def _cobrar(self, pedido, follow=False, **extra):
        data = {
            'metodo_pago': 'efectivo',
            'recibido': '10.00',
            'tipo_identificacion': '07',
        }
        data.update(extra)
        return self.client.post(
            reverse('caja:caja_completar', args=[pedido.pk]), data=data, follow=follow,
        )

    # ---------- Permisos ----------

    def test_anonimo_redirige_login(self):
        self.client.logout()
        resp = self.client.get(reverse('caja:index'))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse('caja:caja_detalle', args=[1]))
        self.assertEqual(resp.status_code, 302)

    def test_empleado_accede_a_caja(self):
        resp = self.client.get(reverse('caja:index'))
        self.assertEqual(resp.status_code, 200)

    # ---------- Búsqueda por ticket ----------

    def test_buscar_por_numero_muestra_tarjeta(self):
        pedido = self._pedido_pendiente()
        resp = self.client.get(reverse('caja:index'), {'q': pedido.pedi_numero})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, pedido.pedi_numero)

    def test_buscar_sin_resultado_muestra_empty_state(self):
        resp = self.client.get(reverse('caja:index'), {'q': 'P-99999999-99999'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No hay pedidos en este rango')

    def test_buscar_cobrado_muestra_tarjeta(self):
        pedido = self._pedido_pendiente()
        pedido.completar(usuario=self.emp)
        resp = self.client.get(reverse('caja:index'), {'q': pedido.pedi_numero})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, pedido.pedi_numero)
        # La tarjeta debe mostrar badge de Cobrado, no redirigir
        self.assertContains(resp, 'badge-success')

    # ---------- Listado con todos los estados ----------

    def test_index_muestra_todos_los_estados(self):
        pendiente = self._pedido_pendiente()
        cobrado = self._pedido_pendiente()
        cobrado.completar(usuario=self.emp)
        cancelado = self._pedido_pendiente()
        cancelado.cancelar()

        resp = self.client.get(reverse('caja:index'))

        self.assertContains(resp, pendiente.pedi_numero)
        self.assertContains(resp, cobrado.pedi_numero)
        self.assertContains(resp, cancelado.pedi_numero)
        self.assertContains(resp, 'badge-warning">Pendiente')
        self.assertContains(resp, 'badge-success">Cobrado')
        self.assertContains(resp, 'badge-danger">Cancelado')

    # ---------- Detalle ----------

    def test_detalle_redirige_si_ya_no_esta_pendiente(self):
        pedido = self._pedido_pendiente()
        resp = self.client.get(reverse('caja:caja_detalle', args=[pedido.pk]))
        self.assertEqual(resp.status_code, 200)
        pedido.completar(usuario=self.emp)
        resp = self.client.get(reverse('caja:caja_detalle', args=[pedido.pk]))
        self.assertRedirects(resp, reverse('caja:index') + '?aviso=cobrado')
        pedido.cancelar()
        resp = self.client.get(reverse('caja:caja_detalle', args=[pedido.pk]))
        self.assertRedirects(resp, reverse('caja:index') + '?aviso=cancelado')

    def test_ticket_visible_para_cualquier_empleado(self):
        otro = User.objects.create_user(username='otro', password='pass1234')
        pedido = Order.objects.create(pedi_vendedor=otro)
        OrderItem.objects.create(
            deta_pedido=pedido, deta_producto=self.p, deta_cantidad=1, deta_precio_unitario=self.p.prod_precio,
        )
        pedido.recalcular_totales()
        resp = self.client.get(reverse('caja:caja_ticket', args=[pedido.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Pagar en Caja')

    def test_ticket_visible_para_pedido_cobrado(self):
        pedido = self._pedido_pendiente()
        pedido.completar(usuario=self.emp)
        resp = self.client.get(reverse('caja:caja_ticket', args=[pedido.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, pedido.get_pedi_metodo_pago_display())

    # ---------- Cobro POS ----------

    def test_consumidor_final_autocompleta_datos(self):
        pedido = self._pedido_pendiente()
        resp = self._cobrar(pedido)
        self.assertEqual(resp.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.pedi_cliente, 'CONSUMIDOR FINAL')
        self.assertEqual(pedido.pedi_identificacion, '9999999999999')
        self.assertEqual(pedido.pedi_tipo_identificacion, '07')

    def test_recibido_no_numerico_rechazado(self):
        pedido = self._pedido_pendiente()
        resp = self._cobrar(pedido, recibido='abc')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'monto recibido válido')
        pedido.refresh_from_db()
        self.assertEqual(pedido.pedi_active, Order.ESTADO_PENDIENTE)

    def test_no_se_cobra_pedido_ya_completado(self):
        pedido = self._pedido_pendiente()
        pedido.completar(usuario=self.emp)
        resp = self._cobrar(pedido)
        self.assertRedirects(resp, reverse('caja:index') + '?aviso=cobrado')
        pedido.refresh_from_db()
        self.assertEqual(pedido.pedi_active, Order.ESTADO_COMPLETADO)

    def test_no_se_cobra_pedido_ya_cancelado(self):
        pedido = self._pedido_pendiente()
        pedido.cancelar()
        resp = self._cobrar(pedido)
        self.assertRedirects(resp, reverse('caja:index') + '?aviso=cancelado')
        pedido.refresh_from_db()
        self.assertEqual(pedido.pedi_active, Order.ESTADO_CANCELADO)

    def test_mensaje_success_tras_cobrar(self):
        pedido = self._pedido_pendiente()
        resp = self._cobrar(pedido, follow=True)
        self.assertContains(resp, 'Cobrado')
