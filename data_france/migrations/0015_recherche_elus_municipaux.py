# Generated by Django 3.0.5 on 2021-01-19 12:18
from django.contrib.postgres.search import SearchVectorField
from django.db import migrations

add_search_index = """
CREATE INDEX data_france_elumunicipal_search_index ON data_france_elumunicipal USING GIN ("search");
"""

drop_search_index = "DROP INDEX data_france_commune_search_index"


class Migration(migrations.Migration):

    dependencies = [
        ("data_france", "0014_elumunicipal"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="elumunicipal",
            options={
                "ordering": ("commune", "nom", "prenom", "date_naissance"),
                "verbose_name": "Élu⋅e municipal⋅e",
                "verbose_name_plural": "Élu⋅es municipaux⋅les",
            },
        ),
        migrations.AddField(
            model_name="elumunicipal",
            name="search",
            field=SearchVectorField(verbose_name="Champ de recherche", null=True),
        ),
        migrations.RunSQL(sql=add_search_index, reverse_sql=drop_search_index),
    ]
