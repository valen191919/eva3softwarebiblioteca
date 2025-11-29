from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from .models import Libro, Prestamo
from django.db.models import Q, Count

def home(request):
    """Vista de inicio/home"""
    return render(request, 'home.html')

@login_required
def dashboard(request):
    """
    Dashboard principal del sistema - Se adapta según el rol del usuario
    Muestra nombre del usuario, opciones según su rol y préstamos activos del usuario
    """
    # Obtener el perfil del usuario
    perfil = None
    if hasattr(request.user, 'perfil'):
        perfil = request.user.perfil
    
    # Estadísticas generales
    total_libros = Libro.objects.count()
    libros_disponibles = Libro.objects.filter(disponible=True).count()
    prestamos_activos_totales = Prestamo.objects.filter(fecha_devolucion_real__isnull=True).count()
    
    # Préstamos activos del usuario actual (para lectores)
    mis_prestamos = Prestamo.objects.filter(
        usuario=request.user,
        fecha_devolucion_real__isnull=True
    ).select_related('libro').order_by('fecha_devolucion_esperada')
    
    # Calcular días restantes para cada préstamo
    fecha_actual = timezone.now().date()
    for prestamo in mis_prestamos:
        dias_restantes = (prestamo.fecha_devolucion_esperada - fecha_actual).days
        prestamo.dias_restantes = dias_restantes
        prestamo.esta_vencido = dias_restantes < 0
        prestamo.dias_restantes_abs = abs(dias_restantes)
    
    context = {
        'usuario': request.user,
        'perfil': perfil,
        'total_libros': total_libros,
        'libros_disponibles': libros_disponibles,
        'prestamos_activos': prestamos_activos_totales,
        'mis_prestamos': mis_prestamos,
    }
    return render(request, 'dashboard.html', context)

@login_required
def registrar_prestamo(request):
    """
    Funcionalidad 1: Registro de Préstamo con filtro de búsqueda
    - Muestra SOLO libros disponibles
    - Valida que el libro esté disponible antes de prestar
    - Cambia el estado del libro a "Prestado"
    """
    if request.method == 'POST':
        libro_id = request.POST.get('libro_id')
        dias_prestamo = int(request.POST.get('dias_prestamo', 7))
        
        # VALIDACIÓN 1: Verificar que el libro existe
        try:
            libro = Libro.objects.get(id=libro_id)
        except Libro.DoesNotExist:
            messages.error(request, '❌ El libro seleccionado no existe.')
            return redirect('registrar_prestamo')
        
        # VALIDACIÓN 2: Verificar que el libro está disponible
        if not libro.disponible:
            messages.error(request, f'❌ Lo sentimos, el libro "{libro.titulo}" ya está prestado y no está disponible en este momento.')
            return redirect('registrar_prestamo')
        
        # VALIDACIÓN 3: Verificar que no hay préstamos activos de este libro
        prestamo_activo = Prestamo.objects.filter(
            libro=libro,
            fecha_devolucion_real__isnull=True
        ).exists()
        
        if prestamo_activo:
            messages.error(request, f'❌ El libro "{libro.titulo}" tiene un préstamo activo. No se puede prestar hasta que sea devuelto.')
            return redirect('registrar_prestamo')
        
        # VALIDACIÓN 4: Verificar que el usuario no tiene este libro prestado
        usuario_tiene_libro = Prestamo.objects.filter(
            usuario=request.user,
            libro=libro,
            fecha_devolucion_real__isnull=True
        ).exists()
        
        if usuario_tiene_libro:
            messages.error(request, f'❌ Ya tienes el libro "{libro.titulo}" en préstamo. Debes devolverlo antes de solicitarlo nuevamente.')
            return redirect('registrar_prestamo')
        
        # Todas las validaciones pasaron: Crear el préstamo
        fecha_devolucion_esperada = timezone.now().date() + timedelta(days=dias_prestamo)
        
        Prestamo.objects.create(
            usuario=request.user,
            libro=libro,
            fecha_devolucion_esperada=fecha_devolucion_esperada
        )
        
        # Control de Disponibilidad: Cambiar estado del libro a NO disponible
        libro.disponible = False
        libro.save()
        
        messages.success(request, f'✅ Préstamo registrado exitosamente. Libro: "{libro.titulo}". Debes devolver antes del {fecha_devolucion_esperada.strftime("%d/%m/%Y")}')
        return redirect('dashboard')
    
    # Mostrar SOLO libros disponibles
    busqueda = request.GET.get('buscar', '')
    
    # Filtro base: Solo libros con disponible=True Y sin préstamos activos
    libros_disponibles = Libro.objects.filter(disponible=True)
    
    # Excluir libros con préstamos activos (doble validación)
    libros_con_prestamos_activos = Prestamo.objects.filter(
        fecha_devolucion_real__isnull=True
    ).values_list('libro_id', flat=True)
    
    libros_disponibles = libros_disponibles.exclude(id__in=libros_con_prestamos_activos)
    
    # Aplicar búsqueda si existe
    if busqueda:
        libros_disponibles = libros_disponibles.filter(
            Q(titulo__icontains=busqueda) |
            Q(autor__icontains=busqueda) |
            Q(genero__icontains=busqueda)
        )
    
    # Contar total de libros disponibles
    total_disponibles = libros_disponibles.count()
    
    context = {
        'libros': libros_disponibles,
        'busqueda': busqueda,
        'total_disponibles': total_disponibles,
    }
    return render(request, 'registrar_prestamo.html', context)

@login_required
def registrar_devolucion(request):
    """
    Funcionalidad 2: Registro de Devolución con Cálculo de Multas
    - Muestra préstamos activos del usuario
    - Calcula multa automáticamente si hay atraso ($1000 por día)
    - Devuelve el libro a estado "Disponible"
    """
    if request.method == 'POST':
        prestamo_id = request.POST.get('prestamo_id')
        
        # Validación de seguridad: verificar que el préstamo existe y pertenece al usuario
        try:
            prestamo = Prestamo.objects.get(
                id=prestamo_id, 
                usuario=request.user,
                fecha_devolucion_real__isnull=True  # Solo préstamos activos
            )
        except Prestamo.DoesNotExist:
            messages.error(request, '❌ Préstamo no válido o ya devuelto.')
            return redirect('registrar_devolucion')
        
        # Registrar fecha de devolución real
        fecha_devolucion_real = timezone.now().date()
        prestamo.fecha_devolucion_real = fecha_devolucion_real
        
        # CÁLCULO DE MULTA AUTOMÁTICO - $1000 POR DÍA
        if fecha_devolucion_real > prestamo.fecha_devolucion_esperada:
            dias_atraso = (fecha_devolucion_real - prestamo.fecha_devolucion_esperada).days
            multa_por_dia = Decimal('1000.00')  # $1000 por día de atraso
            prestamo.multa = multa_por_dia * dias_atraso
            
            messages.warning(request, f'⚠️ Devolución con atraso de {dias_atraso} días. Multa: ${prestamo.multa}')
        else:
            prestamo.multa = Decimal('0.00')
            messages.success(request, '✅ Devolución a tiempo. Sin multa.')
        
        prestamo.save()
        
        # Control de Disponibilidad: Devolver libro a estado DISPONIBLE
        libro = prestamo.libro
        libro.disponible = True
        libro.save()
        
        return redirect('registrar_devolucion')
    
    # Mostrar préstamos activos del usuario (sin devolución)
    prestamos_activos = Prestamo.objects.filter(
        usuario=request.user,
        fecha_devolucion_real__isnull=True
    ).select_related('libro')
    
    context = {
        'prestamos': prestamos_activos
    }
    return render(request, 'registrar_devolucion.html', context)

@login_required
def disponibilidad_libros(request):
    """
    Funcionalidad 3: Consulta de Disponibilidad con filtro de búsqueda
    - Muestra todos los libros con su estado
    - Indica cuáles están disponibles y cuáles prestados
    - Permite filtrar por título, autor o género
    """
    # Filtro de búsqueda
    busqueda = request.GET.get('buscar', '')
    libros = Libro.objects.all()
    
    if busqueda:
        libros = libros.filter(
            Q(titulo__icontains=busqueda) |
            Q(autor__icontains=busqueda) |
            Q(genero__icontains=busqueda)
        )
    
    # Contar estadísticas
    total_libros = libros.count()
    libros_disponibles = libros.filter(disponible=True).count()
    libros_prestados = libros.filter(disponible=False).count()
    
    context = {
        'libros': libros,
        'total_libros': total_libros,
        'libros_disponibles': libros_disponibles,
        'libros_prestados': libros_prestados,
        'busqueda': busqueda
    }
    return render(request, 'disponibilidad_libros.html', context)

# ==================== PANEL DE BIBLIOTECARIO ====================

@login_required
def panel_bibliotecario(request):
    """
    Panel exclusivo para bibliotecarios
    Muestra estadísticas y opciones de gestión
    """
    # Verificar que el usuario es bibliotecario o administrador
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol not in ['bibliotecario', 'administrador']:
        messages.error(request, '❌ No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')
    
    # Estadísticas generales
    total_libros = Libro.objects.count()
    libros_por_genero = Libro.objects.values('genero').annotate(total=Count('genero')).order_by('-total')
    prestamos_activos = Prestamo.objects.filter(fecha_devolucion_real__isnull=True).count()
    prestamos_vencidos = Prestamo.objects.filter(
        fecha_devolucion_real__isnull=True,
        fecha_devolucion_esperada__lt=timezone.now().date()
    ).count()
    
    context = {
        'total_libros': total_libros,
        'libros_por_genero': libros_por_genero,
        'prestamos_activos': prestamos_activos,
        'prestamos_vencidos': prestamos_vencidos,
    }
    return render(request, 'panel_bibliotecario.html', context)

@login_required
def gestionar_libros(request):
    """
    Vista UNIFICADA para:
    - Agregar libros (formulario superior)
    - Listar libros (tabla)
    - Editar libros (modal o formulario inline)
    - Eliminar libros
    """
    # Verificar permisos
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol not in ['bibliotecario', 'administrador']:
        messages.error(request, '❌ No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')
    
    # Variable para saber si estamos editando
    libro_editar = None
    
    # AGREGAR LIBRO
    if request.method == 'POST' and 'accion' in request.POST and request.POST['accion'] == 'agregar':
        titulo = request.POST.get('titulo')
        autor = request.POST.get('autor')
        genero = request.POST.get('genero')
        disponible = request.POST.get('disponible') == 'on'
        
        if not titulo or not autor:
            messages.error(request, '❌ El título y el autor son obligatorios.')
        else:
            Libro.objects.create(
                titulo=titulo,
                autor=autor,
                genero=genero,
                disponible=disponible
            )
            messages.success(request, f'✅ Libro "{titulo}" agregado exitosamente.')
            return redirect('gestionar_libros')
    
    # EDITAR LIBRO
    if request.method == 'POST' and 'accion' in request.POST and request.POST['accion'] == 'editar':
        libro_id = request.POST.get('libro_id')
        libro = get_object_or_404(Libro, id=libro_id)
        
        libro.titulo = request.POST.get('titulo')
        libro.autor = request.POST.get('autor')
        libro.genero = request.POST.get('genero')
        libro.disponible = request.POST.get('disponible') == 'on'
        libro.save()
        
        messages.success(request, f'✅ Libro "{libro.titulo}" actualizado exitosamente.')
        return redirect('gestionar_libros')
    
    # PREPARAR FORMULARIO DE EDICIÓN
    if request.method == 'GET' and 'editar' in request.GET:
        libro_id = request.GET.get('editar')
        libro_editar = get_object_or_404(Libro, id=libro_id)
    
    # ELIMINAR LIBRO
    if request.method == 'POST' and 'accion' in request.POST and request.POST['accion'] == 'eliminar':
        libro_id = request.POST.get('libro_id')
        libro = get_object_or_404(Libro, id=libro_id)
        
        # Verificar si tiene préstamos activos
        prestamos_activos = Prestamo.objects.filter(libro=libro, fecha_devolucion_real__isnull=True).exists()
        
        if prestamos_activos:
            messages.error(request, f'❌ No se puede eliminar "{libro.titulo}" porque tiene préstamos activos.')
        else:
            titulo = libro.titulo
            libro.delete()
            messages.success(request, f'✅ Libro "{titulo}" eliminado exitosamente.')
        
        return redirect('gestionar_libros')
    
    # LISTAR LIBROS CON BÚSQUEDA
    busqueda = request.GET.get('buscar', '')
    libros = Libro.objects.all().order_by('titulo')
    
    if busqueda:
        libros = libros.filter(
            Q(titulo__icontains=busqueda) |
            Q(autor__icontains=busqueda)
        )
    
    context = {
        'libros': libros,
        'busqueda': busqueda,
        'generos': Libro.GENEROS,
        'libro_editar': libro_editar,  # Para mostrar el formulario de edición
    }
    return render(request, 'gestionar_libros.html', context)