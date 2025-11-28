from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import PerfilUsuario

def login_view(request):
    """Vista de Login"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "❌ Credenciales inválidas")
            return render(request, "login.html")

    return render(request, "login.html")


def registro_view(request):
    """Vista de Registro de Nuevos Usuarios (Lectores)"""
    if request.method == "POST":
        # Datos del usuario
        username = request.POST.get("username")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        
        # Datos del perfil
        rut = request.POST.get("rut")
        direccion = request.POST.get("direccion")
        telefono = request.POST.get("telefono")
        
        # Validaciones básicas
        if password != password2:
            messages.error(request, "❌ Las contraseñas no coinciden")
            return render(request, "registro.html")
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "❌ El nombre de usuario ya existe")
            return render(request, "registro.html")
        
        if PerfilUsuario.objects.filter(rut=rut).exists():
            messages.error(request, "❌ El RUT ya está registrado")
            return render(request, "registro.html")
        
        # Crear usuario
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            
            # Crear perfil con rol "lector" por defecto
            PerfilUsuario.objects.create(
                usuario=user,
                rut=rut,
                direccion=direccion,
                telefono=telefono,
                rol='lector'
            )
            
            messages.success(request, "✅ Cuenta creada exitosamente. Ya puedes iniciar sesión.")
            return redirect("login")
            
        except Exception as e:
            messages.error(request, f"❌ Error al crear la cuenta: {str(e)}")
            return render(request, "registro.html")
    
    return render(request, "registro.html")


def logout_view(request):
    """Vista de Logout"""
    logout(request)
    messages.success(request, "✅ Sesión cerrada exitosamente")
    return redirect("home")