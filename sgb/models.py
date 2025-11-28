from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Libro(models.Model):
    GENEROS = [
        ('ficcion', 'Ficción'),
        ('no_ficcion', 'No Ficción'),
        ('ciencia', 'Ciencia'),
        ('historia', 'Historia'),
        ('biografia', 'Biografía'),
        ('fantasia', 'Fantasía'),
        ('romance', 'Romance'),
        ('terror', 'Terror'),
        ('poesia', 'Poesía'),
        ('otro', 'Otro'),
    ]
    
    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=100)
    genero = models.CharField(max_length=20, choices=GENEROS, default='otro')
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo
    
    class Meta:
        verbose_name = "Libro"
        verbose_name_plural = "Libros"


class Prestamo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)

    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion_esperada = models.DateField()
    fecha_devolucion_real = models.DateField(null=True, blank=True)
    multa = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.usuario.username} - {self.libro.titulo}"
    
    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"