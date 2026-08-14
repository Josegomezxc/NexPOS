"""Tests del módulo de mensajes del superowner."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.products.models import Category, Product
from app.users.models import Profile

from .models import Mensaje, MensajeEntrega


class MensajesBaseTests(TestCase):
    def setUp(self):
        self.superowner = User.objects.create_superuser(
            username='chelo', password='chelo12345'
        )
        self.superowner.profile.perf_rol = Profile.ROL_SUPEROWNER
        self.superowner.profile.save()
        self.admin = User.objects.create_superuser(
            username='admin', password='admin12345'
        )
        self.admin.profile.perf_rol = Profile.ROL_ADMIN
        self.admin.profile.save()
        self.empleado = User.objects.create_user(
            username='empleado1', password='empleado12345'
        )
        self.cat = Category.objects.create(cate_nombre='Hamburguesas')
        self.prod = Product.objects.create(
            prod_nombre='Cheeseburger', prod_categoria=self.cat,
            prod_precio=Decimal('5.00'),
        )
        self.url_prod_delete = reverse('products:product_delete', args=[self.prod.pk])
        self.url_prod_activate = reverse('products:product_activate', args=[self.prod.pk])
        self.url_cat_delete = reverse('products:category_delete', args=[self.cat.pk])
        self.url_cat_activate = reverse('products:category_activate', args=[self.cat.pk])
        self.url_emp_delete = reverse('users:empleado_delete', args=[self.empleado.pk])
        self.url_emp_activate = reverse('users:empleado_activate', args=[self.empleado.pk])

    def _bloquear_producto(self):
        self.prod.prod_active = False
        self.prod.prod_desactivado_por = self.superowner
        self.prod.prod_desactivado_fecha = timezone.now()
        self.prod.save(update_fields=[
            'prod_active', 'prod_desactivado_por', 'prod_desactivado_fecha',
        ])
class GeneracionMensajesTests(MensajesBaseTests):
    def test_superowner_desactiva_producto_genera_mensaje_para_admin_y_emisor(self):
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(self.url_prod_delete)
        self.assertEqual(resp.status_code, 302)

        mensaje = Mensaje.objects.get()
        self.assertEqual(mensaje.emisor, self.superowner)
        self.assertEqual(mensaje.tipo, Mensaje.TIPO_PRODUCTO)
        self.assertEqual(mensaje.accion, Mensaje.ACCION_DESACTIVO)
        self.assertEqual(mensaje.entidad_nombre, 'Cheeseburger')
        self.assertIn('Cheeseburger', mensaje.texto)

        entregas = set(
            MensajeEntrega.objects.filter(mensaje=mensaje)
            .values_list('destinatario_id', flat=True)
        )
        self.assertEqual(entregas, {self.admin.pk, self.superowner.pk})

    def test_admin_desactiva_producto_no_genera_mensaje(self):
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_prod_delete)
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(Mensaje.objects.count(), 0)

    def test_superowner_reactiva_producto_genera_mensaje(self):
        self._bloquear_producto()
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(self.url_prod_activate)
        self.assertEqual(resp.status_code, 302)

        mensaje = Mensaje.objects.get()
        self.assertEqual(mensaje.accion, Mensaje.ACCION_REACTIVO)
        self.assertEqual(mensaje.entidad_nombre, 'Cheeseburger')

    def test_cascada_categoria_genera_un_solo_mensaje_con_resumen(self):
        p2 = Product.objects.create(
            prod_nombre='Doble Bacon', prod_categoria=self.cat,
            prod_precio=Decimal('7.00'),
        )
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(self.url_cat_delete)
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(Mensaje.objects.count(), 1)
        mensaje = Mensaje.objects.get()
        self.assertEqual(mensaje.tipo, Mensaje.TIPO_CATEGORIA)
        self.assertEqual(mensaje.accion, Mensaje.ACCION_DESACTIVO)
        self.assertEqual(mensaje.entidad_nombre, 'Hamburguesas')
        self.assertIn('Cheeseburger', mensaje.texto)
        self.assertIn('Doble bacon', mensaje.texto)
        self.prod.refresh_from_db()
        p2.refresh_from_db()
        self.assertFalse(self.prod.prod_active)
        self.assertFalse(p2.prod_active)

    def test_reactivacion_categoria_genera_mensaje(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_cat_delete)
        self.client.post(self.url_cat_activate)
        self.assertEqual(Mensaje.objects.count(), 2)
        mensaje = Mensaje.objects.order_by('-creado').first()
        self.assertEqual(mensaje.tipo, Mensaje.TIPO_CATEGORIA)
        self.assertEqual(mensaje.accion, Mensaje.ACCION_REACTIVO)

    def test_superowner_desactiva_empleado_genera_mensaje(self):
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(self.url_emp_delete)
        self.assertEqual(resp.status_code, 302)
        mensaje = Mensaje.objects.get()
        self.assertEqual(mensaje.tipo, Mensaje.TIPO_EMPLEADO)
        self.assertEqual(mensaje.accion, Mensaje.ACCION_DESACTIVO)
        self.assertEqual(mensaje.entidad_nombre, 'empleado1')

    def test_superowner_reactiva_empleado_genera_mensaje(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_emp_delete)
        self.client.post(self.url_emp_activate)
        self.assertEqual(Mensaje.objects.count(), 2)
        mensaje = Mensaje.objects.order_by('-creado').first()
        self.assertEqual(mensaje.tipo, Mensaje.TIPO_EMPLEADO)
        self.assertEqual(mensaje.accion, Mensaje.ACCION_REACTIVO)

    def test_admin_desactiva_empleado_no_genera_mensaje(self):
        self.client.login(username='admin', password='admin12345')
        self.client.post(self.url_emp_delete)
        self.assertEqual(Mensaje.objects.count(), 0)

    def test_desactivacion_desde_form_de_edicion_genera_mensaje(self):
        url = reverse('products:product_update', args=[self.prod.pk])
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(url, {
            'prod_nombre': 'Cheeseburger', 'prod_categoria': self.cat.pk,
            'prod_precio': '5.00',
        })
        self.assertEqual(resp.status_code, 302)
        mensaje = Mensaje.objects.get()
        self.assertEqual(mensaje.tipo, Mensaje.TIPO_PRODUCTO)
        self.assertEqual(mensaje.accion, Mensaje.ACCION_DESACTIVO)

    def test_empleado_sin_entrega_porque_no_genera_ni_recibe(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        self.assertEqual(
            MensajeEntrega.objects.filter(destinatario=self.empleado).count(), 0
        )


class AccesoMensajesTests(MensajesBaseTests):
    def test_empleado_no_accede_al_listado(self):
        self.client.login(username='empleado1', password='empleado12345')
        resp = self.client.get(reverse('mensajes:list'))
        self.assertEqual(resp.status_code, 302)

    def test_empleado_no_accede_al_detalle(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        mensaje = Mensaje.objects.get()
        self.client.login(username='empleado1', password='empleado12345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_todos_los_admins_y_el_emisor_ven_el_mensaje(self):
        otro_admin = User.objects.create_superuser(
            username='admin2', password='admin212345'
        )
        otro_admin.profile.perf_rol = Profile.ROL_ADMIN
        otro_admin.profile.save()
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        mensaje = Mensaje.objects.get()
        self.assertEqual(
            MensajeEntrega.objects.filter(
                mensaje=mensaje, destinatario=otro_admin,
            ).count(), 1
        )

        self.client.login(username='admin2', password='admin212345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_abrir_detalle_marca_leido_solo_al_que_abrio(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        mensaje = Mensaje.objects.get()

        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 200)

        entrega_admin = MensajeEntrega.objects.get(
            mensaje=mensaje, destinatario=self.admin
        )
        self.assertTrue(entrega_admin.leido)
        self.assertIsNotNone(entrega_admin.leido_en)
        entrega_emisor = MensajeEntrega.objects.get(
            mensaje=mensaje, destinatario=self.superowner
        )
        self.assertFalse(entrega_emisor.leido)


class EdicionEliminacionTests(MensajesBaseTests):
    def setUp(self):
        super().setUp()
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        self.mensaje = Mensaje.objects.get()
        self.url_edit = reverse('mensajes:edit', args=[self.mensaje.pk])
        self.url_delete = reverse('mensajes:delete', args=[self.mensaje.pk])

    def test_superowner_edita_su_texto(self):
        resp = self.client.post(self.url_edit, {'texto': 'Aviso personalizado'})
        self.assertEqual(resp.status_code, 302)
        self.mensaje.refresh_from_db()
        self.assertEqual(self.mensaje.texto, 'Aviso personalizado')

    def test_admin_no_puede_editar(self):
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_edit, {'texto': 'Hackeado'})
        self.assertEqual(resp.status_code, 302)
        self.mensaje.refresh_from_db()
        self.assertNotEqual(self.mensaje.texto, 'Hackeado')

    def test_empleado_no_puede_editar(self):
        self.client.login(username='empleado1', password='empleado12345')
        resp = self.client.post(self.url_edit, {'texto': 'Hackeado'})
        self.assertEqual(resp.status_code, 302)
        self.mensaje.refresh_from_db()
        self.assertNotEqual(self.mensaje.texto, 'Hackeado')

    def test_admin_no_puede_eliminar(self):
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_delete)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Mensaje.objects.filter(pk=self.mensaje.pk).exists())

    def test_superowner_elimina_su_mensaje(self):
        resp = self.client.post(self.url_delete)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Mensaje.objects.filter(pk=self.mensaje.pk).exists())


class EstadoVistoTests(MensajesBaseTests):
    """El visto del mensaje: gris hasta que un admin lo abre, verde después.

    Verificar que el superowner abriendo su propio mensaje no activa el visto
    del admin (la lógica de fondo de visto_por_admin no cambia)."""

    def _crear_mensaje(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        return Mensaje.objects.get()

    def test_estado_inicial_es_un_visto(self):
        mensaje = self._crear_mensaje()
        self.assertFalse(mensaje.visto_por_admin)

    def test_superowner_abre_su_mensaje_no_activa_segundo_visto(self):
        mensaje = self._crear_mensaje()
        self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        mensaje.refresh_from_db()
        self.assertFalse(mensaje.visto_por_admin)

    def test_admin_abre_mensaje_activa_segundo_visto(self):
        mensaje = self._crear_mensaje()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 200)
        mensaje.refresh_from_db()
        self.assertTrue(mensaje.visto_por_admin)

    def test_segundo_admin_o_superowner_siguen_sin_cambiar_el_estado(self):
        otro_admin = User.objects.create_superuser(
            username='admin2', password='admin212345'
        )
        otro_admin.profile.perf_rol = Profile.ROL_ADMIN
        otro_admin.profile.save()
        mensaje = self._crear_mensaje()
        self.client.login(username='admin', password='admin12345')
        self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))

        self.client.login(username='admin2', password='admin212345')
        self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        mensaje.refresh_from_db()
        self.assertTrue(mensaje.visto_por_admin)

    def test_listado_muestra_un_icono_que_cambia_de_gris_a_verde(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        mensaje = Mensaje.objects.get()
        url = reverse('mensajes:list')

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'title="Sin leer por el admin"')
        self.assertNotContains(resp, 'title="Leído por el admin"')

        self.client.login(username='admin', password='admin12345')
        self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))

        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.get(url)
        self.assertContains(resp, 'title="Leído por el admin"')

    def test_detalle_muestra_panel_estado_y_destinatarios(self):
        mensaje = self._crear_mensaje()
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Estado del Mensaje')
        self.assertContains(resp, 'Destinatarios')
        self.assertContains(resp, 'Detalles del Mensaje')
        self.assertContains(resp, 'admin')
        self.assertContains(resp, 'chelo')
        self.assertContains(resp, 'Sin leer')

    def test_admin_solo_ve_mensaje_y_detalles(self):
        mensaje = self._crear_mensaje()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Detalles del Mensaje')
        self.assertContains(resp, 'Mensaje #')
        self.assertNotContains(resp, 'Estado del Mensaje')
        self.assertNotContains(resp, 'Estado de lectura')
        self.assertNotContains(resp, 'Destinatarios')
        self.assertNotContains(resp, 'Tú generaste este aviso')

    def test_leyenda_con_iconos_y_texto_actualizado(self):
        mensaje = self._crear_mensaje()
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Tú generaste este aviso')
        self.assertContains(resp, 'El visto del mensaje pasa de gris')
        self.assertContains(resp, 'a verde')

    def test_card_del_mensaje_muestra_emisor_y_enlace_a_la_entidad(self):
        mensaje = self._crear_mensaje()
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Mensaje del superowner')
        self.assertContains(resp, 'Desactivó')
        self.assertContains(resp, 'Cheeseburger')
        self.assertContains(resp, 'Ver producto')
        self.assertContains(
            resp, reverse('products:product_list') + '?detalle=' + str(self.prod.pk)
        )
        self.assertContains(resp, 'Aviso automático generado al desactivar')
        self.assertNotContains(resp, 'id="productModal"')

    def test_ver_producto_inexistente_muestra_popup_informativo(self):
        mensaje = self._crear_mensaje()
        self.prod.delete()
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Ver producto')
        self.assertContains(resp, 'id="productoNoDisponibleModal"')
        self.assertContains(resp, 'ya no se encuentra disponible en el menú')
        self.assertNotContains(resp, 'id="productModal"')
        self.assertNotContains(resp, 'data-abrir-modal-producto')

    def test_estado_del_mensaje_muestra_stepper_y_banner(self):
        mensaje = self._crear_mensaje()
        url = reverse('mensajes:detail', args=[mensaje.pk])
        self.client.login(username='chelo', password='chelo12345')

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Mensaje generado')
        self.assertContains(resp, 'Visto por el admin')
        self.assertContains(resp, 'Sin leer todavía')
        self.assertContains(resp, 'El admin todavía no vio tu mensaje')
        self.assertNotContains(resp, 'El admin ya vio tu mensaje')

        self.client.login(username='admin', password='admin12345')
        self.client.get(url)

        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.get(url)
        self.assertContains(resp, 'El admin ya vio tu mensaje')
        self.assertContains(resp, 'Confirmado el')

    def test_destinatarios_muestra_resumen_de_leidos(self):
        mensaje = self._crear_mensaje()
        url = reverse('mensajes:detail', args=[mensaje.pk])
        self.client.login(username='chelo', password='chelo12345')

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '0 de 2 leyeron este mensaje')

        self.client.login(username='admin', password='admin12345')
        self.client.get(url)

        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.get(url)
        self.assertContains(resp, '1 de 2 leyeron este mensaje')

    def test_listado_agrupa_mensajes_por_dia(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        mensaje = Mensaje.objects.get()
        Mensaje.objects.filter(pk=mensaje.pk).update(
            creado=timezone.now() - timezone.timedelta(days=1)
        )
        resp = self.client.get(reverse('mensajes:list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Ayer')
        self.assertNotContains(resp, 'Hoy')


class TopbarTests(MensajesBaseTests):
    def test_superowner_ve_badge_con_no_leidos(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        resp = self.client.get(reverse('users:dashboard'))
        self.assertGreaterEqual(
            resp.context['topbar_mensajes_count'], 1
        )
        self.assertTrue(resp.context['topbar_mensajes'])

    def test_empleado_no_ve_mensajes_en_topbar(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        self.client.login(username='empleado1', password='empleado12345')
        resp = self.client.get(reverse('users:dashboard'))
        self.assertEqual(resp.context['topbar_mensajes_count'], 0)
        self.assertEqual(resp.context['topbar_mensajes'], [])

    def test_badge_baja_al_marcar_leido(self):
        self.client.login(username='chelo', password='chelo12345')
        self.client.post(self.url_prod_delete)
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('users:dashboard'))
        self.assertGreaterEqual(resp.context['topbar_mensajes_count'], 1)
        mensaje = Mensaje.objects.get()
        self.client.get(reverse('mensajes:detail', args=[mensaje.pk]))
        resp = self.client.get(reverse('users:dashboard'))
        self.assertEqual(resp.context['topbar_mensajes_count'], 0)