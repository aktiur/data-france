# Generated by Django 3.1.6 on 2021-03-10 04:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_france', '0019_auto_20210209_0834'),
    ]

    operations = [
        migrations.AddField(
            model_name='elumunicipal',
            name='parrainage2017',
            field=models.CharField(blank=True, editable=False, max_length=80, verbose_name='Personne parrainée aux Présidentielles de 2017'),
        ),
    ]
