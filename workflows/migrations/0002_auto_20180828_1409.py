# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-08-28 12:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transition',
            name='condition',
            field=models.TextField(blank=True, verbose_name='Condition'),
        ),
    ]
