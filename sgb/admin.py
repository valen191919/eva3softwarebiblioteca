from django.contrib import admin
from .models import Libro, Prestamo

@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    # Campos a mostrar en la lista
    list_display = ('titulo', 'autor', 'genero', 'disponible')
    # Filtros laterales
    list_filter = ('disponible', 'genero')
    # Barra de búsqueda
    search_fields = ('titulo', 'autor')
    # Campos editables directamente desde la lista
    list_editable = ('disponible',)
    # Ordenar por título
    ordering = ('titulo',)
    # Campos a mostrar en el formulario
    fields = ('titulo', 'autor', 'genero', 'disponible')

@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    # Campos a mostrar en la lista
    list_display = ('usuario', 'libro', 'fecha_prestamo', 'fecha_devolucion_esperada', 
                    'fecha_devolucion_real', 'multa', 'estado_prestamo')
    # Filtros laterales
    list_filter = ('fecha_prestamo', 'fecha_devolucion_real')
    # Barra de búsqueda
    search_fields = ('usuario__username', 'libro__titulo')
    # Campos de solo lectura
    readonly_fields = ('fecha_prestamo', 'multa')
    # Ordenar por fecha más reciente
    ordering = ('-fecha_prestamo',)
    # Agrupar campos en el formulario
    fieldsets = (
        ('Información del Préstamo', {
            'fields': ('usuario', 'libro')
        }),
        ('Fechas', {
            'fields': ('fecha_prestamo', 'fecha_devolucion_esperada', 'fecha_devolucion_real')
        }),
        ('Multa', {
            'fields': ('multa',)
        }),
    )
    
    # Método personalizado para mostrar el estado
    def estado_prestamo(self, obj):
        if obj.fecha_devolucion_real:
            return "✅ Devuelto"
        return "📚 Activo"
    estado_prestamo.short_description = 'Estado'