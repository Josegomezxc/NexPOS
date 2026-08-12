"""Migración: nomenclatura tbl_ con prefijos en perfiles.

- users_profile -> tbl_perfiles (perf_*)
- activo -> perf_active
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_profile_superowner'),
    ]

    operations = [
        migrations.RenameField('Profile', 'id', 'id_perf'),
        migrations.RenameField('Profile', 'user', 'perf_usuario'),
        migrations.RenameField('Profile', 'rol', 'perf_rol'),
        migrations.RenameField('Profile', 'telefono', 'perf_telefono'),
        migrations.RenameField('Profile', 'documento', 'perf_documento'),
        migrations.RenameField('Profile', 'activo', 'perf_active'),
        migrations.RenameField('Profile', 'creado', 'perf_creado'),
        migrations.RenameField('Profile', 'actualizado', 'perf_actualizado'),
        migrations.AlterModelTable('Profile', 'tbl_perfiles'),
    ]