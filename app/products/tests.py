from decimal import Decimal

from django.test import TestCase

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
        # NOCASE no bloquea, y el slug se deduplica con -2.
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
