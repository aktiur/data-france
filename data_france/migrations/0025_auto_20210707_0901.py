# Generated by Django 3.1.7 on 2021-07-07 09:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("data_france", "0024_circonscriptionlegislative_depute"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="circonscriptionlegislative",
            options={
                "ordering": ("code",),
                "verbose_name": "Circonscription législative",
                "verbose_name_plural": "Circonscriptions législatives",
            },
        ),
        migrations.AlterModelOptions(
            name="depute",
            options={"ordering": ("nom", "prenom"), "verbose_name": "Député⋅e"},
        ),
    ]
