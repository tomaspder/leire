from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.routers import SafeMigrationRouter
from core.safety import ensure_demo_database, ensure_schema_changes_allowed

PASSWORD = "clave-de-prueba-larga-123"


class AuthenticationTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        for name in ["home", "panel", "consulta", "distritos_list", "distritos_create"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(response.url.startswith(reverse("login")), name)

    def test_anonymous_cannot_post(self):
        response = self.client.post(reverse("distritos_create"), {"name": "X", "code": "X"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("login")))

    def test_login_and_logout(self):
        User.objects.create_user("ana", password=PASSWORD)
        response = self.client.post(reverse("login"), {"username": "ana", "password": PASSWORD})
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("home")).status_code, 302)

    def test_wrong_password_rejected(self):
        User.objects.create_user("ana", password=PASSWORD)
        response = self.client.post(reverse("login"), {"username": "ana", "password": "incorrecta"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_no_public_signup(self):
        self.assertNotEqual(self.client.get("/registro/").status_code, 200)
        self.assertNotContains(self.client.get(reverse("login")), "Registr")

    def test_private_headers(self):
        User.objects.create_user("ana", password=PASSWORD)
        self.client.login(username="ana", password=PASSWORD)
        response = self.client.get(reverse("home"))
        self.assertIn("private", response["Cache-Control"])
        self.assertIn("noindex", response["X-Robots-Tag"])

    def test_demo_banner_visible(self):
        User.objects.create_user("ana", password=PASSWORD)
        self.client.login(username="ana", password=PASSWORD)
        self.assertContains(self.client.get(reverse("home")), "Datos de demostración: cifras ficticias")


class GroupsCommandTests(TestCase):
    def test_groups_created_with_expected_permissions(self):
        call_command("configurar_grupos", stdout=mock.MagicMock())
        from django.contrib.auth.models import Group

        consulta = Group.objects.get(name="Consulta")
        edicion = Group.objects.get(name="Edición")
        self.assertTrue(all(p.codename.startswith("view_") for p in consulta.permissions.all()))
        self.assertEqual(consulta.permissions.count(), 6)
        self.assertEqual(edicion.permissions.count(), 24)
        self.assertFalse(Permission.objects.filter(group=consulta, codename__startswith="delete_").exists())


class FakeConnection:
    def __init__(self, name, host):
        self.settings_dict = {"NAME": name, "HOST": host}


class SafetyTests(SimpleTestCase):
    def test_demo_database_accepted(self):
        ensure_demo_database(FakeConnection("leire_demo", "localhost"))
        ensure_demo_database(FakeConnection("test_leire_demo", "/var/run/postgresql"))

    def test_rejects_name_without_demo(self):
        with self.assertRaisesMessage(CommandError, "no parece de demostración"):
            ensure_demo_database(FakeConnection("investigacion", "localhost"))

    def test_rejects_remote_host(self):
        with self.assertRaisesMessage(CommandError, "no es local"):
            ensure_demo_database(FakeConnection("leire_demo", "db.universidad.example"))

    @override_settings(APP_DB_MODE="real")
    def test_rejects_real_mode(self):
        with self.assertRaisesMessage(CommandError, "APP_DB_MODE=demo"):
            ensure_demo_database(FakeConnection("leire_demo", "localhost"))

    @override_settings(APP_DB_MODE="real")
    def test_migrate_blocked_in_real_mode(self):
        with mock.patch.dict("os.environ", {"ALLOW_REAL_DB_MIGRATIONS": ""}):
            with self.assertRaisesMessage(CommandError, "Bloqueado"):
                ensure_schema_changes_allowed()
            with self.assertRaisesMessage(CommandError, "Bloqueado"):
                call_command("migrate", "--check", verbosity=0)
            with self.assertRaisesMessage(CommandError, "Bloqueado"):
                call_command("flush", interactive=False, verbosity=0)

    @override_settings(APP_DB_MODE="real")
    def test_router_skips_demo_tables_in_real_mode(self):
        router = SafeMigrationRouter()
        self.assertFalse(router.allow_migrate("default", "demografia"))
        self.assertIsNone(router.allow_migrate("default", "auth"))

    def test_router_allows_demo_tables_in_demo_mode(self):
        self.assertIsNone(SafeMigrationRouter().allow_migrate("default", "demografia"))
