from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator

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
    
    def tiene_prestamo_activo(self):
        """
        Verifica si el libro tiene un préstamo activo
        Retorna True si hay un préstamo sin devolver
        """
        return Prestamo.objects.filter(
            libro=self,
            fecha_devolucion_real__isnull=True
        ).exists()
    
    def puede_prestarse(self):
        """
        Verifica si el libro puede ser prestado
        Retorna True solo si está disponible Y no tiene préstamo activo
        """
        return self.disponible and not self.tiene_prestamo_activo()
    
    class Meta:
        verbose_name = "Libro"
        verbose_name_plural = "Libros"


class Prestamo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)

    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion_esperada = models.DateField()
    fecha_devolucion_real = models.DateField(null=True, blank=True)
    
    # Campo multa con validación mejorada
    multa = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    def __str__(self):
        return f"{self.usuario.username} - {self.libro.titulo}"
    
    def save(self, *args, **kwargs):
        """
        Sobrescribir save para asegurar que multa siempre sea un valor válido
        """
        if self.multa is None or str(self.multa).strip() == '':
            self.multa = Decimal('0.00')
        try:
            # Verificar que es un decimal válido
            self.multa = Decimal(str(self.multa))
        except:
            self.multa = Decimal('0.00')
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"