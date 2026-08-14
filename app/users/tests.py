from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Profile


class VerificarUsuarioTests(TestCase):
    """API JSON usada por la validación en tiempo real del formulario."""

    def setUp(self):
        User.objects.create_user(username='juan', password='juan12345')

    def test_disponible(self):
        resp = self.client.get(reverse('users:verificar_usuario'), {'username': 'nuevo1'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'disponible': True})

    def test_usado(self):
        resp = self.client.get(reverse('users:verificar_usuario'), {'username': 'juan'})
        self.assertEqual(resp.json(), {'disponible': False, 'motivo': 'usado'})

    def test_usado_ignora_mayusculas(self):
        resp = self.client.get(reverse('users:verificar_usuario'), {'username': 'JUAN'})
        self.assertEqual(resp.json(), {'disponible': False, 'motivo': 'usado'})

    def test_reservado(self):
        resp = self.client.get(reverse('users:verificar_usuario'), {'username': 'admin'})
        self.assertEqual(resp.json(), {'disponible': False, 'motivo': 'reservado'})

    def test_formato_invalido(self):
        resp = self.client.get(reverse('users:verificar_usuario'), {'username': 'ab'})
        self.assertEqual(resp.json(), {'disponible': False, 'motivo': 'formato'})
        resp = self.client.get(reverse('users:verificar_usuario'), {'username': 'espa cio'})
        self.assertEqual(resp.json(), {'disponible': False, 'motivo': 'formato'})

    def test_vacio(self):
        resp = self.client.get(reverse('users:verificar_usuario'))
        self.assertEqual(resp.json(), {'disponible': False, 'motivo': 'vacio'})


class UsersTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', password='admin12345', email='a@a.com'
        )
        self.empleado = User.objects.create_user(
            username='juan', password='juan12345'
        )

    def test_profile_creado_automaticamente(self):
        self.assertTrue(hasattr(self.admin, 'profile'))
        self.assertTrue(hasattr(self.empleado, 'profile'))
        self.assertEqual(self.admin.profile.perf_rol, Profile.ROL_ADMIN)

    def test_login_ok(self):
        ok = self.client.login(username='juan', password='juan12345')
        self.assertTrue(ok)

    def test_dashboard_requiere_login(self):
        resp = self.client.get(reverse('users:dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_empleado_list_solo_admin(self):
        self.client.login(username='juan', password='juan12345')
        resp = self.client.get(reverse('users:empleado_list'))
        self.assertEqual(resp.status_code, 302)
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('users:empleado_list'))
        self.assertEqual(resp.status_code, 200)

    def test_perfil_no_permite_autopromoverse(self):
        """Un empleado NO puede subir su rol a admin desde su perfil."""
        self.client.login(username='juan', password='juan12345')
        resp = self.client.post(reverse('users:perfil'), {
            'username': 'juan',
            'first_name': 'Juan',
            'last_name': 'Perez',
            'email': 'juan@ejemplo.com',
            'rol': Profile.ROL_ADMIN,  # intento de escalada
        })
        self.assertEqual(resp.status_code, 302)
        self.empleado.profile.refresh_from_db()
        self.assertEqual(self.empleado.profile.perf_rol, Profile.ROL_EMPLEADO)
        self.assertFalse(self.empleado.is_superuser)

    def test_perfil_no_permite_autodesactivarse(self):
        self.client.login(username='juan', password='juan12345')
        resp = self.client.post(reverse('users:perfil'), {
            'username': 'juan',
            'first_name': 'Juan',
            'last_name': '',
            'email': '',
            'is_active': '',  # intento de desactivación
        })
        self.assertEqual(resp.status_code, 302)
        self.empleado.refresh_from_db()
        self.assertTrue(self.empleado.is_active)

    def test_login_bloqueado_tras_intentos_fallidos(self):
        """Tras N intentos fallidos, el login se bloquea con cooldown."""
        from django.conf import settings
        from django.contrib.messages import get_messages
        from django.core.cache import cache

        cache.clear()
        max_intentos = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
        for _ in range(max_intentos):
            self.client.post(reverse('users:login'), {
                'username': 'juan', 'password': 'incorrecta',
            })

        # Un intento más (fallido) queda bloqueado, no vuelve a validar credenciales
        resp = self.client.post(reverse('users:login'), {
            'username': 'juan', 'password': 'otra-incorrecta',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('users:login'))
        mensajes = list(get_messages(resp.wsgi_request))
        self.assertTrue(any('Demasiados intentos' in str(m) for m in mensajes))
        cache.clear()


class BloqueoDuenoUsuariosTests(TestCase):
    """Candado del superowner: el admin no puede reactivar un usuario que el due�o desactiv�."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', password='admin12345'
        )
        self.superowner = User.objects.create_superuser(
            username='chelo', password='chelo12345'
        )
        self.superowner.profile.perf_rol = Profile.ROL_SUPEROWNER
        self.superowner.profile.save()
        self.empleado = User.objects.create_user(
            username='juan', password='juan12345'
        )
        self.url_reactivar = reverse('users:empleado_activate', args=[self.empleado.pk])
        self.url_desactivar = reverse('users:empleado_delete', args=[self.empleado.pk])

    def _bloquear_usuario(self):
        self.empleado.is_active = False
        self.empleado.save(update_fields=['is_active'])
        perfil = self.empleado.profile
        perfil.perf_active = False
        perfil.perf_desactivado_por = self.superowner
        perfil.perf_desactivado_fecha = timezone.now()
        perfil.save(update_fields=[
            'perf_active', 'perf_desactivado_por', 'perf_desactivado_fecha',
        ])

    def test_admin_no_puede_reactivar_usuario_del_dueno(self):
        self._bloquear_usuario()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_reactivar)
        self.assertEqual(resp.status_code, 302)
        self.empleado.refresh_from_db()
        self.assertFalse(self.empleado.is_active)
        self.empleado.profile.refresh_from_db()
        self.assertFalse(self.empleado.profile.perf_active)

    def test_superowner_reactiva_y_limpia_el_candado(self):
        self._bloquear_usuario()
        self.client.login(username='chelo', password='chelo12345')
        resp = self.client.post(self.url_reactivar)
        self.assertEqual(resp.status_code, 302)
        self.empleado.refresh_from_db()
        self.assertTrue(self.empleado.is_active)
        self.empleado.profile.refresh_from_db()
        self.assertTrue(self.empleado.profile.perf_active)
        self.assertIsNone(self.empleado.profile.perf_desactivado_por)

    def test_admin_reactiva_usuario_desactivado_por_admin(self):
        self.empleado.is_active = False
        self.empleado.save(update_fields=['is_active'])
        perfil = self.empleado.profile
        perfil.perf_active = False
        perfil.perf_desactivado_por = self.admin
        perfil.perf_desactivado_fecha = timezone.now()
        perfil.save(update_fields=[
            'perf_active', 'perf_desactivado_por', 'perf_desactivado_fecha',
        ])
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_reactivar)
        self.assertEqual(resp.status_code, 302)
        self.empleado.refresh_from_db()
        self.assertTrue(self.empleado.is_active)

    def test_desactivacion_registra_quien_y_cuando(self):
        self.client.login(username='admin', password='admin12345')
        resp = self.client.post(self.url_desactivar)
        self.assertEqual(resp.status_code, 302)
        self.empleado.refresh_from_db()
        self.assertFalse(self.empleado.is_active)
        self.empleado.profile.refresh_from_db()
        self.assertEqual(self.empleado.profile.perf_desactivado_por, self.admin)
        self.assertIsNotNone(self.empleado.profile.perf_desactivado_fecha)

    def test_admin_no_puede_editar_usuario_bloqueado_por_el_dueno(self):
        self._bloquear_usuario()
        self.client.login(username='admin', password='admin12345')
        url = reverse('users:empleado_update', args=[self.empleado.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        # ni siquiera vía POST del form con is_active marcado
        resp = self.client.post(url, {'username': 'juan', 'is_active': 'on'})
        self.assertEqual(resp.status_code, 302)
        self.empleado.refresh_from_db()
        self.assertFalse(self.empleado.is_active)
        self.empleado.profile.refresh_from_db()
        self.assertFalse(self.empleado.profile.perf_active)

    def test_superowner_puede_editar_usuario_bloqueado(self):
        self._bloquear_usuario()
        self.client.login(username='chelo', password='chelo12345')
        url = reverse('users:empleado_update', args=[self.empleado.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_sigue_pudiendo_editar_usuario_activo(self):
        self.client.login(username='admin', password='admin12345')
        url = reverse('users:empleado_update', args=[self.empleado.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_lista_no_muestra_editar_en_card_bloqueada_por_dueno(self):
        self._bloquear_usuario()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('users:empleado_list'))
        self.assertNotContains(
            resp, reverse('users:empleado_update', args=[self.empleado.pk])
        )

    def test_lista_muestra_editar_en_card_activa(self):
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('users:empleado_list'))
        self.assertContains(
            resp, reverse('users:empleado_update', args=[self.empleado.pk])
        )

    def test_lista_muestra_icono_y_marca_del_dueno(self):
        self._bloquear_usuario()
        self.client.login(username='admin', password='admin12345')
        resp = self.client.get(reverse('users:empleado_list'))
        self.assertContains(resp, 'fa-lock')
        self.assertContains(resp, 'data-bloqueo-dueno')
        self.assertContains(resp, 'chelo')
        self.assertContains(resp, 'data-tipo="Usuario"')
        self.assertContains(resp, 'modalBloqueoDueno')

    # ----- Edición desde el formulario: sincroniza el candado del perfil -----

    def test_form_empleado_desactivacion_sincroniza_perfil(self):
        self.client.login(username='admin', password='admin12345')
        url = reverse('users:empleado_update', args=[self.empleado.pk])
        resp = self.client.post(url, {
            'username': 'juan', 'perf_rol': Profile.ROL_EMPLEADO,
        })
        self.assertEqual(resp.status_code, 302)
        self.empleado.refresh_from_db()
        self.assertFalse(self.empleado.is_active)
        self.empleado.profile.refresh_from_db()
        self.assertFalse(self.empleado.profile.perf_active)
        self.assertEqual(self.empleado.profile.perf_desactivado_por, self.admin)
        self.assertIsNotNone(self.empleado.profile.perf_desactivado_fecha)

    def test_form_empleado_reactivacion_limpia_registro(self):
        self.empleado.is_active = False
        self.empleado.save(update_fields=['is_active'])
        perfil = self.empleado.profile
        perfil.perf_active = False
        perfil.perf_desactivado_por = self.admin
        perfil.perf_desactivado_fecha = timezone.now()
        perfil.save(update_fields=[
            'perf_active', 'perf_desactivado_por', 'perf_desactivado_fecha',
        ])
        self.client.login(username='admin', password='admin12345')
        url = reverse('users:empleado_update', args=[self.empleado.pk])
        resp = self.client.post(url, {
            'username': 'juan', 'perf_rol': Profile.ROL_EMPLEADO,
            'is_active': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        self.empleado.refresh_from_db()
        self.assertTrue(self.empleado.is_active)
        self.empleado.profile.refresh_from_db()
        self.assertTrue(self.empleado.profile.perf_active)
        self.assertIsNone(self.empleado.profile.perf_desactivado_por)
        self.assertIsNone(self.empleado.profile.perf_desactivado_fecha)
