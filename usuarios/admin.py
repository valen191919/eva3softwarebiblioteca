from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import PerfilUsuario

# Inline para mostrar el perfil junto con el usuario
class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'
    # Campos que se mostrarán al crear/editar usuario
    fields = ('rut', 'direccion', 'telefono', 'rol')

# Extender el admin de User para incluir el perfil
class UserAdmin(BaseUserAdmin):
    inlines = (PerfilUsuarioInline,)
    
    # Mostrar estos campos en la lista de usuarios
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_rol', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'perfil__rol')
    
    # Método para mostrar el rol en la lista
    def get_rol(self, obj):
        if hasattr(obj, 'perfil'):
            return obj.perfil.get_rol_display()
        return "Sin perfil"
    get_rol.short_description = 'Rol'
    
    # Sobrescribir el método save para crear perfil automáticamente
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()

# Re-registrar UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Registro simple del modelo PerfilUsuario (por si se quiere acceder directamente)
@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rut', 'telefono', 'rol')
    list_filter = ('rol',)
    search_fields = ('usuario__username', 'rut', 'usuario__first_name', 'usuario__last_name')
    # Campos de solo lectura
    readonly_fields = ('usuario',)