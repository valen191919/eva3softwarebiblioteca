
from django.db import models
from django.contrib.auth.models import User

class PerfilUsuario(models.Model):
    ROLES = [
        ('lector', 'Lector'),
        ('bibliotecario', 'Bibliotecario'),
        ('administrador', 'Administrador'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rut = models.CharField(max_length=12, unique=True)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=15)
    rol = models.CharField(max_length=20, choices=ROLES, default='lector')
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.get_rol_display()}"
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"