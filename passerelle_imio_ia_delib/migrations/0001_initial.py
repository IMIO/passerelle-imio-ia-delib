# Generated by Django 2.2.19 on 2021-10-12 09:55

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('base', '0029_auto_20210202_1627'),
    ]

    operations = [
        migrations.CreateModel(
            name='IADelibConnector',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50, verbose_name='Title')),
                ('slug', models.SlugField(unique=True, verbose_name='Identifier')),
                ('description', models.TextField(verbose_name='Description')),
                ('url', models.CharField(blank=True, help_text="URL de l'application iA.Delib", max_length=128, verbose_name='URL')),
                ('username', models.CharField(blank=True, max_length=128, verbose_name='Utilisateur')),
                ('password', models.CharField(blank=True, max_length=128, verbose_name='Mot de passe')),
                ('users', models.ManyToManyField(blank=True, related_name='_iadelibconnector_users_+', related_query_name='+', to='base.ApiUser')),
            ],
            options={
                'verbose_name': 'Connecteur iA.Delib',
            },
        ),
    ]