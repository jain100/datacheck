from django.db import models

# Create your models here.

class Document(models.Model):
    docfile = models.FileField(upload_to='documents/%Y/%m/%d')


class SavedGraph(models.Model):
    graphDataset = models.CharField(max_length=255,)
    graphType = models.CharField(max_length=255,)

    graphTitle = models.CharField(max_length=255,)
    graphXAxisLabel = models.CharField(max_length=255,)
    graphYAxisLabel = models.CharField(max_length=255,)

    graphXAxisVar = models.CharField(max_length=255,)
    graphYAxisVar = models.CharField(max_length=2000,)
    graphOp = models.CharField(max_length=255,)
    graphHist = models.CharField(max_length=255,)
