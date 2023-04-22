import os 
import uuid
import base64, json
from operator import or_
from flask import Blueprint, render_template, flash, redirect, request, session, url_for, current_app, make_response, send_file
from flask_security import login_required, current_user
from flask_security.decorators import roles_required, roles_accepted
from ..models import db
from .. import userDataStore, db
from project.models import  Producto, Role, User, InventarioMateriaPrima, ExplotacionMaterial, Proveedor,DetCompra,Compra, DetVenta, Venta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash 
import pandas as pd
from itertools import groupby
import cufflinks as cf
import plotly.express as px
import plotly.io as pio
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import plotly.graph_objs as go
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch
import io 
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from reportlab.pdfgen import canvas
from io import BytesIO
import matplotlib
from sqlalchemy import func
matplotlib.use('Agg')


empleado = Blueprint('empleado', __name__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('flask.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

###################### Modulo de Inventario de Materia Prima ############################

@empleado.route('/inventarios', methods=['GET', 'POST'])
@login_required
def inventarios():  
    materiales= InventarioMateriaPrima.query.filter_by(estatus=1).all()
    print(materiales)
    td_style = ""
    td_style2=""
    for material in materiales:
        if material.cantidad <= material.stock_minimo:
            td_style = "bg-danger"
            td_style2 = "fas fa-grimace"  
        elif material.cantidad > material.stock_minimo:
            td_style = "bg-primary"
            td_style2 ="fas fa-grin-alt"
    return render_template('inventarios.html', materiales=materiales,td_style=td_style,td_style2=td_style2)

##########################################################################################

###################### Modulo de Materia Prima ######################

@empleado.route('/materiales', methods=['GET', 'POST'])
@login_required
def materiales():
    if request.method == 'GET':
        materiales= InventarioMateriaPrima.query.all()
        return render_template('MateriaPrimaCrud.html', materiales=materiales)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        cantidad = request.form.get('cantidad')
        stock_minimo = request.form.get('stock_minimo')
        material = InventarioMateriaPrima(nombre=nombre, descripcion=descripcion, cantidad=cantidad, stock_minimo=stock_minimo)
        db.session.add(material)
        db.session.commit()
        flash("El material ha sido agregado exitosamente.", "success")
        return redirect(url_for('administrador.inventarios'))
    
@empleado.route('/modificarMaterial', methods=['GET', 'POST'])
@login_required
def modificarMaterial():
    id = request.args.get('id')
    material = InventarioMateriaPrima.query.get(id)
    if material is None:
        flash("El material no existe", "error")
        return redirect(url_for('administrador.inventarios'))
    if request.method == 'POST':
        material.nombre = request.form.get('nombre')
        material.descripcion = request.form.get('descripcion')
        material.cantidad = request.form.get('cantidad')
        material.stock_minimo = request.form.get('stock_minimo')
        db.session.add(material)
        db.session.commit()
        flash("El registro se ha modificado exitosamente.", "success")
        return redirect(url_for('administrador.inventarios'))
    elif request.method == 'GET':
        return render_template('modificarMateriaPrima.html', material=material, id=id)

@empleado.route('/eliminarMaterial', methods=['GET', 'POST'])
@login_required
def eliminarMaterial():
    id = request.args.get('id')
    material = InventarioMateriaPrima.query.get(id)
    if material is None:
        flash("El material no existe", "error")
        return redirect(url_for('administrador.inventarios'))
    if request.method == 'POST':
        material.estatus = 0
        db.session.add(material)
        db.session.commit()
        flash("El registro se ha eliminado exitosamente.", "success")
        return redirect(url_for('administrador.inventarios'))
    elif request.method == 'GET':
        return render_template('eliminarMateriaPrima.html', material=material, id=id)
    
    
    
    
##########################################################################################







###################### Modulo de Compras ##################################################

#FUNCIONES PARA EL MODULO DE COMPRAS
@empleado.route('/compras', methods=['GET', 'POST'])
@login_required
def compras():
    id = request.args.get('id')
    if request.method == 'GET':
        materiales = InventarioMateriaPrima.query.all()
        proveedores = Proveedor.query.all()
        return render_template('compras.html', materiales=materiales, id=id, proveedores=proveedores)
    elif request.method == 'POST':
        material = InventarioMateriaPrima.query.get(id)
        proveedor = request.form.get('proveedor')
        cantidad = request.form.get('cantidad')
        fecha = request.form.get('fecha')
        precio= request.form.get('precio')
        compra = Compra(proveedor_id=proveedor, fecha=fecha, estatus=0)
        db.session.add(compra)
        
        # Obtener el objeto Producto creado en la sesión de la base de datos
        compraNow = db.session.query(Compra).order_by(Compra.id.desc()).first()
        print(f"Producto: {compraNow.id}")
        # Crear un nuevo objeto CompraMaterial para cada material comprado
        precioTotal= float(cantidad) * float(precio)
        materialC= DetCompra(compra_id=compraNow.id, material_id=material.id, cantidad=cantidad, precio=precioTotal)
        db.session.add(materialC)
        db.session.commit()
        
        flash("La compra esta pendiente por revisar", "warning")
        return redirect(url_for('administrador.inventarios'))
    
    
@empleado.route('/catalogoCompras', methods=['GET', 'POST'])
@login_required
def catalogoCompras():

    fecha = request.form.get('fecha')
    fechaR= request.form.get('fechaR')
    conteoComprasR=0
    conteoComprasP=0
    comprasP = False
    comprasR = False
    
    if request.method == 'POST' and 'confirmar' in request.form:
        idCompra = request.form.get('idCompra')
        idMaterial = request.form.get('idMaterial')
        cantidad = request.form.get('cantidad')
    
        material= InventarioMateriaPrima.query.get(idMaterial)
        compra = Compra.query.get(idCompra)
        compra.estatus = 1
        db.session.add(compra)
        # Aumentar la cantidad de material en el inventario correspondiente
        material.cantidad += int(cantidad)
        db.session.add(material)
        db.session.commit()
        flash("Compra realizada con exito", "success")
        return redirect(url_for('administrador.inventarios', id=idCompra, idM=idMaterial, cant=cantidad))
    if request.method == 'GET':
        compras = db.session.query(Compra, DetCompra, InventarioMateriaPrima, Proveedor)\
                    .join(DetCompra, Compra.id == DetCompra.compra_id)\
                    .outerjoin(InventarioMateriaPrima, DetCompra.material_id == InventarioMateriaPrima.id)\
                    .join(Proveedor, Compra.proveedor_id == Proveedor.id)\
                    .filter(Compra.estatus==0)\
                    .all()
        conteoComprasR= Compra.query.filter_by(estatus=1).count()
        comprasRealizadas = db.session.query(Compra, DetCompra, InventarioMateriaPrima, Proveedor)\
                    .join(DetCompra, Compra.id == DetCompra.compra_id)\
                    .outerjoin(InventarioMateriaPrima, DetCompra.material_id == InventarioMateriaPrima.id)\
                    .join(Proveedor, Compra.proveedor_id == Proveedor.id)\
                    .filter(Compra.estatus==1)\
                    .all()
        conteoComprasP= Compra.query.filter_by(estatus=0).count()
        return render_template('catalogoCompras.html', compras=compras,
                        comprasRealizadas=comprasRealizadas,conteoComprasR=conteoComprasR,
                        conteoComprasP=conteoComprasP,comprasP=comprasP,comprasR=comprasR)





##########################################################################################





###################### Modulo de Ventas ##################################################



@empleado.route('/ventas', methods=['GET', 'POST'])
@login_required
def ventas():
    # Obtener ventas pendientes
    ventas_pendientes = db.session.query(Venta, User).\
        join(User, Venta.user_id == User.id).\
        filter(Venta.estatus == 0).all()

    conteo_ventas_pendientes= db.session.query(func.count()).filter(Venta.estatus == 0).scalar()


    # Obtener ventas enviadas
    ventas_enviadas =  db.session.query(Venta, User).\
        join(User, Venta.user_id == User.id).\
        filter(Venta.estatus == 1).all()
        
    conteo_ventas_enviadas= db.session.query(func.count()).filter(Venta.estatus == 1).scalar()
        
    print(ventas_pendientes)

        
    if request.method == 'POST':
        id_venta = request.form.get('id')
        print(id_venta, " ID Venta")
        venta = Venta.query.filter_by(id=id_venta).first()
        venta.estatus = True        
        db.session.commit()

        flash('Se ha confirmado el envío', 'success')

        return redirect(url_for('empleado.ventas'))

    return render_template('ventas.html', ventas_pendientes=ventas_pendientes, ventas_enviadas=ventas_enviadas,
                           conteo_ventas_pendientes=conteo_ventas_pendientes, 
                           conteo_ventas_enviadas=conteo_ventas_enviadas)

@empleado.route('/detalleVenta', methods=['GET', 'POST'])
@login_required
def detalleVenta():  
    if request.method == 'GET':
        id_venta = request.args.get('id')
        estatus = request.args.get('estatus')
        print(estatus, "ESTATUS")
        detalle_ventas = db.session.query(Venta, DetVenta, Producto)\
        .join(DetVenta, Venta.id == DetVenta.venta_id)\
        .join(Producto, DetVenta.producto_id == Producto.id)\
        .filter(Venta.id == id_venta).all()

        # Creamos un diccionario para almacenar los productos y sus cantidades
        productos = {}
        for venta, det_venta, producto in detalle_ventas:
            if producto.nombre in productos and producto.talla == productos[producto.nombre]['talla']:
                productos[producto.nombre]['cantidad'] += det_venta.cantidad
                productos[producto.nombre]['precio'] += det_venta.precio
            else:
                productos[producto.nombre] = {
                    'talla': producto.talla,
                    'color': producto.color,
                    'modelo': producto.modelo,
                    'precio': det_venta.precio,
                    'cantidad': det_venta.cantidad,
                }

        # Convertimos el diccionario a una lista para pasarlo al template
        lista_productos = []
        for nombre, producto in productos.items():
            lista_productos.append({
                'nombre': nombre,
                'talla': producto['talla'],
                'color': producto['color'],
                'modelo': producto['modelo'],
                'precio': producto['precio'],
                'cantidad': producto['cantidad'],
            })

    if request.method == 'POST':
        id_venta_post = request.form.get('idDetVent')
        print(id_venta_post, " ID Venta")
        venta = Venta.query.filter_by(id=id_venta_post).first()
        venta.estatus = True        
        db.session.commit()

        flash('Se ha confirmado el envío', 'success')

        return redirect(url_for('empleado.ventas'))

    return render_template('detalleVenta.html', detalle_ventas=lista_productos, estatus=estatus, id_venta=id_venta)

##########################################################################################