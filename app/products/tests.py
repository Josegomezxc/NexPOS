from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.users.models import Profile

from .forms import CategoryForm, ProductForm
from .models import Category, Product


class ProductTests(TestCase):
    def test_crear_producto(self):
        cat = Category.objects.create(cate_nombre='Hamburguesas', cate_orden=1)
        p = Product.objects.create(
            prod_nombre='Cheeseburger', prod_categoria=cat, prod_precio=Decimal('2500.00')
        )
        self.assertIn('Cheeseburger', str(p))
        self.assertEqual(p.prod_precio, Decimal('2500.00'))

    def test_slug_automatico_categoria(self):
        cat = Category.objects.create(cate_nombre='Salchipapas Especiales')
        self.assertEqual(cat.cate_slug, 'salchipapas-especiales')

    def test_desactivacion_logica_no_borra_historial(self):
        cat = Category.objects.create(cate_nombre='Bebidas')
        p = Product.objects.create(prod_nombre='Cola 500ml', prod_categoria=cat, prod_precio=Decimal('1.00'))
        p.prod_active = False
        p.save()
        self.assertFalse(Product.objects.get(pk=p.pk).prod_active)

    def test_orden_automatico_al_crear(self):
        c1 = Category.objects.create(cate_nombre='Primera')
        c2 = Category.objects.create(cate_nombre='Segunda')
        c3 = Category.objects.create(cate_nombre='Tercera')
        self.assertEqual(c1.cate_orden, 1)
        self.assertEqual(c2.cate_orden, 2)
        self.assertEqual(c3.cate_orden, 3)

    def test_orden_automatico_continua_despues_de_borrado(self):
        c1 = Category.objects.create(cate_nombre='A')
        c2 = Category.objects.create(cate_nombre='B')
        c1.delete()
        c3 = Category.objects.create(cate_nombre='C')
        self.assertEqual(c3.cate_orden, 3)

    def test_orden_explicito_se_respeta(self):
        c = Category.objects.create(cate_nombre='Manual', cate_orden=10)
        self.assertEqual(c.cate_orden, 10)
        siguiente = Category.objects.create(cate_nombre='Auto')
        self.assertEqual(siguiente.cate_orden, 11)

    def test_slug_duplicado_no_rompe(self):
        c1 = Category.objects.create(cate_nombre='Hamburguesas')
        # Mismo slug ('hamburguesas') pero nombre distinto: el nombre único
        # no bloquea, y el slug se deduplica con -2.
        c2 = Category.objects.create(cate_nombre='Hamburguesas!')
        self.assertNotEqual(c1.cate_slug, c2.cate_slug)
        self.assertEqual(c1.cate_slug, 'hamburguesas')
        self.assertEqual(c2.cate_slug, 'hamburguesas-2')
        self.assertEqual(Category.objects.count(), 2)


class FormulariosTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(cate_nombre='Bebidas')

    # ---------- Nombres ----------

    def test_nombre_con_letras_sueltas_se_normaliza(self):
        form = ProductForm(data={
            'prod_nombre': 'c o      l a    s', 'prod_categoria': self.cat.pk,
            'prod_precio': '2.50', 'prod_active': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['prod_nombre'], 'Colas')

    def test_nombre_con_palabras_reales_se_conserva(self):
        form = CategoryForm(data={
            'cate_nombre': 'Papas   Fritas', 'cate_color': '#2563EB', 'cate_active': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['cate_nombre'], 'Papas fritas')

    def test_nombre_solo_espacios_rechazado(self):
        form = CategoryForm(data={'cate_nombre': '     ', 'cate_color': '#2563EB', 'cate_active': 'on'})
        self.assertFalse(form.is_valid())
        self.assertIn('El nombre es obligatorio.', form.errors['cate_nombre'])

    def test_nombre_sin_normalizar_no_rompe_unico(self):
        """'Hamburguesas' y 'Hamburguesas ' deben colisionar tras normalizar."""
        Category.objects.create(cate_nombre='Hamburguesas')
        form = CategoryForm(data={'cate_nombre': 'Hamburguesas  ', 'cate_active': 'on'})
        self.assertFalse(form.is_valid())

    # ---------- Precio ----------

    def test_precio_mas_de_2_decimales_rechazado(self):
        form = ProductForm(data={
            'prod_nombre': 'Cola', 'prod_categoria': self.cat.pk,
            'prod_precio': '1.005', 'prod_active': 'on',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('más de 2 decimales', form.errors['prod_precio'][0])

    def test_precio_con_demasiados_enteros_rechazado(self):
        form = ProductForm(data={
            'prod_nombre': 'Cola', 'prod_categoria': self.cat.pk,
            'prod_precio': '100000000', 'prod_active': 'on',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('8 dígitos enteros', form.errors['prod_precio'][0])

    def test_precio_absurdo_con_coma_rechazado(self):
        form = ProductForm(data={
            'prod_nombre': 'Cola', 'prod_categoria': self.cat.pk,
            'prod_precio': '111111111111111111,000000000000000111111111',
            'prod_active': 'on',
        })
        self.assertFalse(form.is_valid())

    def test_precio_valido_aceptado(self):
        form = ProductForm(data={
            'prod_nombre': 'Cola', 'prod_categoria': self.cat.pk,
            'prod_precio': '99999999.99', 'prod_active': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['prod_precio'], Decimal('99999999.99'))

class BloqueoDuenoProductosTests(TestCase):
    """Candado del superowner: el admin no puede reactivar lo que el dueño desactivó."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', password='admin12345'
        )
        self.superowner = User.objects.create_superuser(
            username='chelo', password='chelo12345'
        )
        self.superowner.profile.perf_rol = Profile.ROL_SUPEROWNER
        self.superowner.profile.save()
        self.cat = Category.objects.create(cate_nombre='Hamburguesas')
        self.prod = Product.objects.create(
            prod_nombre='Cheeseburger', prod_categoria=self.cat,
            prod_precio=Decimal('5.00'),
        )
        self.url_reactivar = reverse('products:product_activate', args=[self.prod.pk])
        self.url_desactivar = reverse('products:product_delete', args=[self.prod.pk])

    def _bloquear_producto(self):
        self.prod.prod_active = False
        self.prod.prod_desactivado_por = self.superowner
        self.prod.prod_desactivado_fecha = timezone.now()
        self.prod.save(update_fields=[
            'prod_active', 'prod_desactivado_por', 'prod_desactivado_fecha',
        ])

    def test_admin_no_puede_reactivar_producto_del_dueno(self):
        self._bloquear_producto()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_reactivar)
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

    def test_superowner_reactiva_y_limpia_el_candado(self):
        self._bloquear_producto()
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(self.url_reactivar)
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertTrue(self.prod.prod_active)
        self.assertIsNone(self.prod.prod_desactivado_por)
        self.assertIsNone(self.prod.prod_desactivado_fecha)

    def test_admin_reactiva_producto_desactivado_por_admin(self):
        self.prod.prod_active = False
        self.prod.prod_desactivado_por = self.admin
        self.prod.prod_desactivado_fecha = timezone.now()
        self.prod.save(update_fields=[
            'prod_active', 'prod_desactivado_por', 'prod_desactivado_fecha',
        ])
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_reactivar)
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertTrue(self.prod.prod_active)

    def test_desactivacion_registra_quien_y_cuando(self):
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(self.url_desactivar)
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)
        self.assertIsNotNone(self.prod.prod_desactivado_fecha)

    def test_candado_cascada_categoria_a_sus_productos(self):
        # El superowner desactiva la categoría: el candado se propaga al producto
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(
            reverse('products:category_delete', args=[self.cat.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

        # El admin no puede reactivar el producto suelto
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_reactivar)
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.prod_active)

    def test_admin_no_puede_editar_producto_bloqueado_por_el_dueno(self):
        self._bloquear_producto()
        self.client.login(username='admin', password='admin12345')
        url = reverse('products:product_update', args=[self.prod.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        # ni siquiera vía POST del form con prod_active marcado
        resp = self.client.post(url, {
            'prod_nombre': 'Hack', 'prod_categoria': self.cat.pk,
            'prod_precio': '5.00', 'prod_active': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_nombre, 'Cheeseburger')
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

    def test_superowner_puede_editar_producto_bloqueado(self):
        self._bloquear_producto()
        self.client.login(username='chelo', password='chelo12345')
        url = reverse('products:product_update', args=[self.prod.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_sigue_pudiendo_editar_producto_activo(self):
        self.client.login(username='admin', password='admin12345')
        url = reverse('products:product_update', args=[self.prod.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_lista_no_muestra_editar_en_card_bloqueada_por_dueno(self):
        self._bloquear_producto()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('products:product_list'))
        self.assertNotContains(
            resp, reverse('products:product_update', args=[self.prod.pk])
        )

    def test_lista_muestra_editar_en_card_activa(self):
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('products:product_list'))
        self.assertContains(
            resp, reverse('products:product_update', args=[self.prod.pk])
        )

    def test_admin_no_puede_editar_categoria_bloqueada_por_el_dueno(self):
        self.cat.cate_active = False
        self.cat.cate_desactivado_por = self.superowner
        self.cat.cate_desactivado_fecha = timezone.now()
        self.cat.save(update_fields=[
            'cate_active', 'cate_desactivado_por', 'cate_desactivado_fecha',
        ])
        self.client.login(username='admin', password='admin12345')
        url = reverse('products:category_update', args=[self.cat.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        resp = self.client.post(url, {'cate_nombre': 'Hack', 'cate_active': 'on'})
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.assertFalse(self.cat.cate_active)
        self.assertEqual(self.cat.cate_nombre, 'Hamburguesas')

    def test_superowner_puede_editar_categoria_bloqueada(self):
        self.cat.cate_active = False
        self.cat.cate_desactivado_por = self.superowner
        self.cat.cate_desactivado_fecha = timezone.now()
        self.cat.save(update_fields=[
            'cate_active', 'cate_desactivado_por', 'cate_desactivado_fecha',
        ])
        self.client.login(username='chelo', password='chelo12345')
        url = reverse('products:category_update', args=[self.cat.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_lista_muestra_icono_y_marca_del_dueno(self):
        self._bloquear_producto()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('products:product_list'))
        self.assertContains(resp, 'fa-lock')
        self.assertContains(resp, 'data-bloqueo-dueno')
        self.assertContains(resp, 'chelo')
        self.assertContains(resp, 'data-tipo="Producto"')
        self.assertContains(resp, 'modalBloqueoDueno')

    # ----- Reactivación de categoría en cascada (respeta roles) -----

    def _desactivar_categoria_como(self, user):
        self.client.login(username=user, password=user + '12345')
        return self.client.post(
            reverse('products:category_delete', args=[self.cat.pk])
        )

    def test_admin_reactiva_categoria_y_sus_productos_sin_candado(self):
        self._desactivar_categoria_como('admin')
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.admin)

        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(
            reverse('products:category_activate', args=[self.cat.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertTrue(self.cat.cate_active)
        self.assertIsNone(self.cat.cate_desactivado_por)
        self.assertTrue(self.prod.prod_active)
        self.assertIsNone(self.prod.prod_desactivado_por)
        self.assertIsNone(self.prod.prod_desactivado_fecha)

    def test_admin_reactiva_categoria_sin_tocar_producto_con_candado(self):
        # Admin desactiva la categoría; luego el superowner bloquea el
        # producto individualmente; el admin reactiva la categoría.
        self._desactivar_categoria_como('admin')
        self.prod.prod_active = False
        self.prod.prod_desactivado_por = self.superowner
        self.prod.prod_desactivado_fecha = timezone.now()
        self.prod.save(update_fields=[
            'prod_active', 'prod_desactivado_por', 'prod_desactivado_fecha',
        ])

        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(
            reverse('products:category_activate', args=[self.cat.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertTrue(self.cat.cate_active)
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

    def test_superowner_reactiva_categoria_y_limpia_candado_de_productos(self):
        self._desactivar_categoria_como('chelo')
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(
            reverse('products:category_activate', args=[self.cat.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertTrue(self.cat.cate_active)
        self.assertTrue(self.prod.prod_active)
        self.assertIsNone(self.prod.prod_desactivado_por)
        self.assertIsNone(self.prod.prod_desactivado_fecha)

    # ----- Desactivación de categoría protegida (popup de bloqueo) -----

    def test_admin_no_puede_desactivar_categoria_con_producto_del_dueno(self):
        self._bloquear_producto()

        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(
            reverse('products:category_delete', args=[self.cat.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertTrue(self.cat.cate_active)
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

    def test_superowner_si_puede_desactivar_categoria_con_producto_suyo(self):
        self._bloquear_producto()

        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(
            reverse('products:category_delete', args=[self.cat.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertFalse(self.cat.cate_active)
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

    def test_admin_ve_popup_con_nombre_del_producto_en_card_protegida(self):
        self._bloquear_producto()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('products:category_list'))
        self.assertContains(resp, 'data-bloqueo-categoria="1"')
        self.assertContains(resp, 'data-bloqueado-nombres="Cheeseburger"')
        self.assertContains(resp, 'btn-bloqueo-categoria')
        self.assertContains(resp, 'modalBloqueoCategoria')
        self.assertContains(resp, 'md-bloqueo-categoria-nombres')

    def test_superowner_ve_confirmacion_normal_en_card_con_producto_suyo(self):
        self._bloquear_producto()
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.get(reverse('products:category_list'))
        self.assertNotContains(resp, 'data-bloqueo-categoria')
        self.assertContains(resp, 'data-confirm-url')

    # ----- Edición desde el formulario (validación como los botones) -----

    def test_admin_no_desactiva_categoria_protegida_via_form(self):
        self._bloquear_producto()
        self.client.login(username='admin', password='admin12345')
        url = reverse('products:category_update', args=[self.cat.pk])
        resp = self.client.post(
            url, {'cate_nombre': 'Hamburguesas', 'cate_color': '#fb8500'}
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertTrue(self.cat.cate_active)
        self.assertEqual(self.cat.cate_nombre, 'Hamburguesas')
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

    def test_admin_ve_popup_en_form_categoria_protegida(self):
        self._bloquear_producto()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(
            reverse('products:category_update', args=[self.cat.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'modalBloqueoCategoria')
        self.assertContains(resp, 'md-bloqueo-categoria-nombres')
        self.assertContains(resp, 'Cheeseburger')
        self.assertContains(resp, 'name="cate_active"')

    def test_superowner_desactiva_categoria_protegida_via_form(self):
        self._bloquear_producto()
        self.client.login(username='chelo', password='chelo12345')
        url = reverse('products:category_update', args=[self.cat.pk])
        resp = self.client.post(
            url, {'cate_nombre': 'Hamburguesas', 'cate_color': '#fb8500'}
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertFalse(self.cat.cate_active)
        self.assertEqual(self.cat.cate_desactivado_por, self.superowner)
        self.assertFalse(self.prod.prod_active)

    def test_admin_desactiva_categoria_sin_proteger_via_form(self):
        self.client.login(username='admin', password='admin12345')
        url = reverse('products:category_update', args=[self.cat.pk])
        resp = self.client.post(
            url, {'cate_nombre': 'Hamburguesas', 'cate_color': '#fb8500'}
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertFalse(self.cat.cate_active)
        self.assertEqual(self.cat.cate_desactivado_por, self.admin)
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.admin)

    def test_admin_reactiva_categoria_via_form_en_cascada(self):
        self.client.login(username='admin', password='admin12345')
        self.client.post(reverse('products:category_delete', args=[self.cat.pk]))
        resp = self.client.post(
            reverse('products:category_update', args=[self.cat.pk]),
            {'cate_nombre': 'Hamburguesas', 'cate_color': '#fb8500',
             'cate_active': 'on'},
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertTrue(self.cat.cate_active)
        self.assertIsNone(self.cat.cate_desactivado_por)
        self.assertTrue(self.prod.prod_active)
        self.assertIsNone(self.prod.prod_desactivado_por)

    def test_form_reactivacion_respeta_producto_con_candado(self):
        self.client.login(username='admin', password='admin12345')
        self.client.post(reverse('products:category_delete', args=[self.cat.pk]))
        self._bloquear_producto()
        resp = self.client.post(
            reverse('products:category_update', args=[self.cat.pk]),
            {'cate_nombre': 'Hamburguesas', 'cate_color': '#fb8500',
             'cate_active': 'on'},
        )
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertTrue(self.cat.cate_active)
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.superowner)

    def test_form_producto_desactivacion_registra_actor(self):
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(
            reverse('products:product_update', args=[self.prod.pk]),
            {'prod_nombre': 'Cheeseburger', 'prod_categoria': self.cat.pk,
             'prod_precio': '5.00'},
        )
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.prod_active)
        self.assertEqual(self.prod.prod_desactivado_por, self.admin)
        self.assertIsNotNone(self.prod.prod_desactivado_fecha)

    def test_form_producto_reactivacion_limpia_registro(self):
        self.prod.prod_active = False
        self.prod.prod_desactivado_por = self.admin
        self.prod.prod_desactivado_fecha = timezone.now()
        self.prod.save(update_fields=[
            'prod_active', 'prod_desactivado_por', 'prod_desactivado_fecha',
        ])
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(
            reverse('products:product_update', args=[self.prod.pk]),
            {'prod_nombre': 'Cheeseburger', 'prod_categoria': self.cat.pk,
             'prod_precio': '5.00', 'prod_active': 'on'},
        )
        self.assertEqual(resp.status_code, 302)
        self.prod.refresh_from_db()
        self.assertTrue(self.prod.prod_active)
        self.assertIsNone(self.prod.prod_desactivado_por)
        self.assertIsNone(self.prod.prod_desactivado_fecha)
