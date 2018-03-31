# Generated by Django 2.0.2 on 2018-03-27 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataapp_first', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedGraph',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('graphDataset', models.CharField(max_length=255)),
                ('graphType', models.CharField(max_length=255)),
                ('graphTitle', models.CharField(max_length=255)),
                ('graphXAxisLabel', models.CharField(max_length=255)),
                ('graphYAxisLabel', models.CharField(max_length=255)),
                ('graphXAxisVar', models.CharField(max_length=255)),
                ('graphYAxisVar', models.CharField(max_length=2000)),
                ('graphOp', models.CharField(max_length=255)),
                ('graphHist', models.CharField(max_length=255)),
            ],
        ),
    ]
