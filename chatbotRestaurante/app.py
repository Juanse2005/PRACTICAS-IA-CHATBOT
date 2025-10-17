from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import re
import os

app = Flask(__name__)

#Archivo donde se guardan los pedidos
PEDIDOS_FILE = "pedidos.json"

MENU = {
    "Hamburguesa": {
        "precio": 12000,
        "imagen": "xcd",
    },
     "Perro": {
        "precio": 15000,
        "imagen": "xcd",
    },
      "Perro con papas":{
        "precio": 18000,
        "imagen": "xcd",
    },
       "Picada":{
        "precio": 12000,
        "imagen": "xcd",
    },
        "Gaseosa":{
        "precio": 12000,
        "imagen": "xcd",
    },
        "Salchipapa":{
        "precio": 12000,
        "imagen": "xcd",
    }
}

#IA: Simple para interpretar pedidos
def parse_pedido(texto):
    texto = texto.lower()
    pedido = []
    for producto, datos in MENU.items():
        prod_escaped = re.escape(producto)
        if re.search(rf'(\b{prod_escaped}s?\b)', texto):
            #Buscar cantidad antes del producto: "2 Hamburguesas"
            m = re.search(rf'(\d+)\s*(?:{prod_escaped}s?\b)', texto)
            #O buscar cantidad despues del producto: "Hamburguesas 2"
            if not m:
                m = re.search(rf'\b(?:{prod_escaped}s?\b\s*(\d+)', texto)
                cantidad = int(m.group(1)) if m else 1
                pedido.append({
                    "producto": producto,
                    "catidad": cantidad,
                    "subtotal": datos["precio"] * cantidad
                })
    return pedido

#Comprobar si un texto parece ua dirección
def es_direccion(texto):
    texto = texto.lower()
    palabras_calle = r'\b(calle|cll|cl|cra|carrera|av|cr|avenida|transversal|tv|via|carretera|kilometro|manzana|interior|bloque|diagonal|dg)\b'
    if re.search(palabras_calle,texto):
        return True
    if "#" in texto:
        return True
    if re.search(r'\b(no\.?|numero|n°)\b.*\d+', texto):
        return True
    if re.search(r"\d{1,5}",texto) and len(texto.split()) <= 10 and any(c.isalpha() for c in texto):
        return True
    return False

#Ejecutar pagina principal
@app.route("/")
def index():
    return render_template("index.html", menu=MENU)

# Endpoint del chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    mensaje = (data.get("mensaje" or "").strip().lower())
    pedido_actual = data.get("pedido", []) or []
    direccio_actual = data.get("direccion", "") or ""
    
    # Codigo para detectar productos (Si el texto contiene nombres del menú)
    # Usamos parse_pedido para obtenner cada uno de los items
    posibles_pedido = parse_pedido(mensaje)
    if posibles_pedido:
        pedido_actual = posibles_pedido
        total = sum(item["subtotal"] for item in pedido_actual)
        respuesta = (
            f"Entendido 👌 tu pedido es: "
            + ", ".join(f"{p['cantidad']} {p['producto']}" for p in pedido_actual)
            + f". total: ${total}. Cual es tu dirección?"
        )
        return jsonify({"respuesta":respuesta, "fase":"direccion","pedido":pedido_actual})
    #detectar dirección
    if es_direccion(mensaje):
        direccion_actual = mensaje
        respuesta = "Perfecto 😊. Como deseas pagar? efectivo, tarjeta o transacción"
        return jsonify({
            "respuesta": respuesta,
            "fase": "pago",
            "pedido": pedido_actual,
            "direccion": direccion_actual
        })
    #Detectar forma de pago y guardar pedido
    if any(palabra in mensaje for palabra in ["efectivo","tarjeta", " transferencia"]):
        #determinar forma de pago exacta
        if "efectivo" in mensaje:
            forma_pago = "efectivo"
        elif "tarjeta" in mensaje:
            forma_pago = "tarjeta"
        else:
            forma_pago = "transferencia"
        nuevo_pedido = {
            "pedido": pedido_actual,
            "direccion": direccion_actual if direccio_actual else "Pendiente dirección",
            "pago": forma_pago,
            "estado": "pendiente"
        }
        if not os.path.exists(PEDIDOS_FILE):
            with open (PEDIDOS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, ident = 4)    
        #leer y actualizar pedidos (manejo robusto de json)
        with open (PEDIDOS_FILE, "w", encoding="utf-8") as f:
            try:
                pedidos: json.load(f)
                if not isinstance(pedidos, list):
                    pedidos = []
            except json.JSONDecodeError:
                pedidos = []
            pedidos.append(nuevo_pedido)
            f.seek(0)
            json.dump(pedidos, f, ennsure_ascii=False, indent=4)
        respuesta(
            "Gracias 📋 Tu pedido fue registrado con éxito. \n"
            "⏳ Tu pedido está en proceso y pronto llegará a tu dirección. \n"
            "❤️ ¡Gracias por preferiros Restaurate IA! !Buen provecho!. \n"
            "Si deseas hacer otro pedido solo di '¡HOLA!'"
        )
        return jsonify({"respuesta": respuesta, "fase": "inicio"})

    # Ver pedidos
    @app.route("/pedidos")
    def ver_pedidos():
        pedidos = []
        if os.path.exists(PEDIDOS_FILE):
            with open(PEDIDOS_FILE, "r", encoding="utf-8") as f:
                try:
                    pedidos = json.load(f)
                    if not isinstance(pedidos, list):
                        pedidos = []
                except json.JSONDecodeError:
                    pedidos = []
        return render_template("pedidos.html")
    # Actualizar estado
    @app.route("/actualizar_estado", methods=["POST"])
    def actualizar_estado():
        try:
            index = int(request.form.get("index"))
        except (TypeError, ValueError):
            return redirect(url_for("ver_pedidos"))
        
        nuevo_estado = request.form.get("estado", "pendiente")
        pedidos = []
        if os.path.exists(PEDIDOS_FILE):
            with open(PEDIDOS_FILE, "r+", encoding="utf-8") as f:
                try:
                    pedidos = json.load(f)
                    if not isinstance(pedidos,list):
                        pedidos=[]
                except json.JSONDecodeError:
                    pedidos=[]
                if 0 <= index < len(pedidos):
                    pedidos [index]["estado"] = nuevo_estado
                    f.seek(0)
                    json.dump(pedidos, f, ensure_ascii=False, indent=4)
                    f.truncate()
        return redirect(url_for("ver_pedidos"))
    
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)