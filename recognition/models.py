from django.db import models

# Create your models here.

class Person(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='recognition/uploads/faces/', blank=True, null=True)
    face_encoding = models.BinaryField() # store the image as binary bites

    def __str__(self):
        return self.name


class AttendanceRecord(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)