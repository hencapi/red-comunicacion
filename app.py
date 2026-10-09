import flet as ft
import psycopg2
import hashlib
import time
import os
import base64
from datetime import datetime

# CONFIGURACIÓN DE SUPABASE EN LA NUBE (Con tu contraseña integrada)
SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "postgresql://postgres.eblyborfcqaeuogacjig:1358Hencapi.@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
)

USUARIO_ADMIN = "camilo acevedo"
SALT_KEY = "OT_SECURE_SALT_2026"
HASH_PIN_ALMACENADO = "d0d138b569c729a2bf5ae3261906f5cfa7375db436ebbd0f51d48885c5c188df"

sesion_iniciada = False

DIR_SCRIPT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()

def obtener_ruta_fondo():
    nombres = [
        "planta_neon.png",
        "planta_neon_opt.png",
        "Code_Generated_Image.jpg",
        "WhatsApp Image 2026-10-07 at 8.40.05 PM.jpeg",
        "WhatsApp Image 2026-10-07 at 8.40.05 PM.jpg"
    ]
    carpetas = [DIR_SCRIPT, os.getcwd()]
    for c in carpetas:
        for n in nombres:
            ruta = os.path.join(c, n)
            if os.path.exists(ruta) and os.path.isfile(ruta):
                return os.path.abspath(ruta)
    for c in carpetas:
        try:
            for f in os.listdir(c):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    return os.path.abspath(os.path.join(c, f))
        except Exception:
            pass
    return "planta_neon.png"

def conn():
    return psycopg2.connect(SUPABASE_URL)

def hash_pin(pin_texto):
    return hashlib.sha256((SALT_KEY + pin_texto.strip()).encode()).hexdigest()

def init_db():
    try:
        c = conn()
        cur = c.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS auditoria_seguridad ("
            "id SERIAL PRIMARY KEY, "
            "fecha TEXT, evento TEXT, detalle TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS areas ("
            "id SERIAL PRIMARY KEY, "
            "nombre TEXT NOT NULL, "
            "descripcion TEXT, "
            "pos_x REAL DEFAULT 40.0, "
            "pos_y REAL DEFAULT 50.0)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS dispositivos ("
            "id SERIAL PRIMARY KEY, "
            "area_id INTEGER, "
            "tag TEXT, tipo TEXT, modelo TEXT, ip TEXT, "
            "tipo_conexion TEXT, tarjeta_local TEXT, tarjeta_destino TEXT, "
            "maquina_unidad TEXT, tablero_tag TEXT, "
            "pos_x REAL DEFAULT 42.0, "
            "pos_y REAL DEFAULT 52.0, "
            "FOREIGN KEY (area_id) REFERENCES areas (id))"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS enlaces ("
            "id SERIAL PRIMARY KEY, "
            "dispositivo_origen_id INTEGER, "
            "protocolo TEXT, medio TEXT, "
            "dispositivo_destino TEXT, sistema_destino TEXT, "
            "FOREIGN KEY (dispositivo_origen_id) REFERENCES dispositivos (id))"
        )
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Aviso de base de datos en inicio: {e}")

def get_areas():
    try:
        c = conn()
        cur = c.cursor()
        cur.execute("SELECT id, nombre, descripcion, pos_x, pos_y FROM areas")
        res = cur.fetchall()
        c.close()
        return res
    except Exception:
        return []

def get_machines_in_area_strict(aid):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute(
            "SELECT DISTINCT maquina_unidad FROM dispositivos "
            "WHERE area_id = %s AND maquina_unidad IS NOT NULL AND maquina_unidad != '' "
            "AND tag IS NOT NULL AND tag != '' AND tag != 'Equipo_Sin_Tag' AND tag != 'Dispositivo_S/T'",
            (aid,)
        )
        rows = cur.fetchall()
        maquinas = [r[0] for r in rows]
        c.close()
        return maquinas
    except Exception:
        return []

def get_devices_in_area(aid):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute(
            "SELECT id, tag, tipo, modelo, ip, tipo_conexion, "
            "tarjeta_local, tarjeta_destino, maquina_unidad, tablero_tag, pos_x, pos_y "
            "FROM dispositivos WHERE area_id = %s",
            (aid,)
        )
        res = cur.fetchall()
        c.close()
        return res
    except Exception:
        return []

def get_devices_by_machine(aid, machine_name):
    try:
        c = conn()
        cur = c.cursor()
        if machine_name == "Equipos Generales / Sin Máquina":
            cur.execute(
                "SELECT id, tag, tipo, modelo, ip, tipo_conexion, "
                "tarjeta_local, tarjeta_destino, maquina_unidad, tablero_tag, pos_x, pos_y "
                "FROM dispositivos "
                "WHERE area_id = %s AND (maquina_unidad IS NULL OR maquina_unidad = '')",
                (aid,)
            )
        else:
            cur.execute(
                "SELECT id, tag, tipo, modelo, ip, tipo_conexion, "
                "tarjeta_local, tarjeta_destino, maquina_unidad, tablero_tag, pos_x, pos_y "
                "FROM dispositivos "
                "WHERE area_id = %s AND maquina_unidad = %s",
                (aid, machine_name)
            )
        res = cur.fetchall()
        c.close()
        return res
    except Exception:
        return []

def get_device_by_id(did):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute(
            "SELECT id, tag, tipo, modelo, ip, tipo_conexion, "
            "tarjeta_local, tarjeta_destino, maquina_unidad, tablero_tag, area_id, pos_x, pos_y "
            "FROM dispositivos WHERE id = %s",
            (did,)
        )
        row = cur.fetchone()
        c.close()
        return row
    except Exception:
        return None

def get_routes(did):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute(
            "SELECT protocolo, medio, dispositivo_destino, sistema_destino "
            "FROM enlaces WHERE dispositivo_origen_id = %s",
            (did,)
        )
        res = cur.fetchall()
        c.close()
        return res
    except Exception:
        return []

def search_all(q):
    try:
        c = conn()
        cur = c.cursor()
        term = f"%{q}%"
        cur.execute(
            "SELECT d.id, d.tag, d.tipo, d.modelo, d.ip, "
            "d.tipo_conexion, d.tarjeta_local, d.tarjeta_destino, "
            "d.maquina_unidad, d.tablero_tag, a.nombre, d.area_id, a.pos_x, a.pos_y, d.pos_x, d.pos_y "
            "FROM dispositivos d JOIN areas a ON d.area_id = a.id "
            "WHERE d.ip LIKE %s OR d.tag LIKE %s OR d.modelo LIKE %s "
            "OR d.tipo_conexion LIKE %s OR d.maquina_unidad LIKE %s "
            "OR d.tablero_tag LIKE %s OR a.nombre LIKE %s",
            (term, term, term, term, term, term, term)
        )
        res = cur.fetchall()
        c.close()
        return res
    except Exception:
        return []

def add_area(nom, desc, px=40.0, py=50.0):
    try:
        c = conn()
        cur = c.cursor()
        nombre_final = nom.strip() if nom and nom.strip() else "Zona Sin Nombre"
        cur.execute(
            "INSERT INTO areas (nombre, descripcion, pos_x, pos_y) VALUES (%s, %s, %s, %s)",
            (nombre_final, desc.strip() if desc else "", px, py)
        )
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al agregar área: {e}")

def update_area(aid, nom, desc, px=None, py=None):
    try:
        c = conn()
        cur = c.cursor()
        nombre_final = nom.strip() if nom and nom.strip() else "Zona Sin Nombre"
        if px is not None and py is not None:
            cur.execute(
                "UPDATE areas SET nombre = %s, descripcion = %s, pos_x = %s, pos_y = %s WHERE id = %s",
                (nombre_final, desc.strip() if desc else "", px, py, aid)
            )
        else:
            cur.execute(
                "UPDATE areas SET nombre = %s, descripcion = %s WHERE id = %s",
                (nombre_final, desc.strip() if desc else "", aid)
            )
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al actualizar área: {e}")

def update_device_pos(did, px, py):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute("UPDATE dispositivos SET pos_x = %s, pos_y = %s WHERE id = %s", (px, py, did))
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al actualizar posición: {e}")

def delete_area(aid):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute(
            "DELETE FROM enlaces WHERE dispositivo_origen_id IN "
            "(SELECT id FROM dispositivos WHERE area_id = %s)",
            (aid,)
        )
        cur.execute("DELETE FROM dispositivos WHERE area_id = %s", (aid,))
        cur.execute("DELETE FROM areas WHERE id = %s", (aid,))
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al eliminar área: {e}")

def delete_machine(aid, machine_name):
    try:
        c = conn()
        cur = c.cursor()
        if machine_name == "Equipos Generales / Sin Máquina":
            cur.execute(
                "DELETE FROM enlaces WHERE dispositivo_origen_id IN "
                "(SELECT id FROM dispositivos WHERE area_id = %s AND (maquina_unidad IS NULL OR maquina_unidad = ''))",
                (aid,)
            )
            cur.execute(
                "DELETE FROM dispositivos WHERE area_id = %s AND (maquina_unidad IS NULL OR maquina_unidad = '')",
                (aid,)
            )
        else:
            cur.execute(
                "DELETE FROM enlaces WHERE dispositivo_origen_id IN "
                "(SELECT id FROM dispositivos WHERE area_id = %s AND maquina_unidad = %s)",
                (aid, machine_name)
            )
            cur.execute(
                "DELETE FROM dispositivos WHERE area_id = %s AND maquina_unidad = %s",
                (aid, machine_name)
            )
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al eliminar máquina: {e}")

def delete_device(did):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute("DELETE FROM enlaces WHERE dispositivo_origen_id = %s", (did,))
        cur.execute("DELETE FROM dispositivos WHERE id = %s", (did,))
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al eliminar dispositivo: {e}")

def add_device(aid, tag, tipo, mod, ip, t_con, t_loc, t_dst, maq, tab, px=42.0, py=52.0):
    try:
        c = conn()
        cur = c.cursor()
        tag_final = tag.strip() if tag and tag.strip() else "Dispositivo_S/T"
        cur.execute(
            "INSERT INTO dispositivos "
            "(area_id, tag, tipo, modelo, ip, tipo_conexion, "
            "tarjeta_local, tarjeta_destino, maquina_unidad, tablero_tag, pos_x, pos_y) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                aid,
                tag_final,
                tipo if tipo else "PLC",
                mod.strip() if mod else "",
                ip.strip() if ip else "",
                t_con.strip() if t_con else "",
                t_loc.strip() if t_loc else "",
                t_dst.strip() if t_dst else "",
                maq.strip() if maq else "",
                tab.strip() if tab else "",
                px,
                py,
            )
        )
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al agregar dispositivo: {e}")

def update_device(did, tag, tipo, mod, ip, t_con, t_loc, t_dst, maq, tab):
    try:
        c = conn()
        cur = c.cursor()
        tag_final = tag.strip() if tag and tag.strip() else "Dispositivo_S/T"
        cur.execute(
            "UPDATE dispositivos SET "
            "tag = %s, tipo = %s, modelo = %s, ip = %s, tipo_conexion = %s, "
            "tarjeta_local = %s, tarjeta_destino = %s, maquina_unidad = %s, tablero_tag = %s "
            "WHERE id = %s",
            (
                tag_final,
                tipo if tipo else "PLC",
                mod.strip() if mod else "",
                ip.strip() if ip else "",
                t_con.strip() if t_con else "",
                t_loc.strip() if t_loc else "",
                t_dst.strip() if t_dst else "",
                maq.strip() if maq else "",
                tab.strip() if tab else "",
                did,
            )
        )
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al actualizar dispositivo: {e}")

def add_route(did, proto, med, dst, sys):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute(
            "INSERT INTO enlaces "
            "(dispositivo_origen_id, protocolo, medio, "
            "dispositivo_destino, sistema_destino) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                did,
                proto.strip() if proto else "Protocolo_N/A",
                med.strip() if med else "",
                dst.strip() if dst else "Destino_N/A",
                sys.strip() if sys else "",
            )
        )
        cur.execute("DELETE FROM dispositivos WHERE tag IS NULL OR tag = '' OR tag = 'Equipo_Sin_Tag' OR tag = 'Dispositivo_S/T'")
        c.commit()
        c.close()
    except Exception as e:
        print(f"Error al agregar enlace: {e}")

def btn(txt, on_click, bg=ft.Colors.TEAL_700, ic=None):
    row_items = []
    if ic:
        row_items.append(
            ft.Icon(ic, color=ft.Colors.WHITE, size=15)
        )
    row_items.append(
        ft.Text(txt, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=12)
    )
    return ft.Container(
        content=ft.Row(row_items, spacing=5, tight=True),
        bgcolor=bg,
        border_radius=5,
        padding=8,
        on_click=on_click,
        ink=True,
    )

def agregar_equipo_rapido(aid, anom, tipo_eq, tag_prefix):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM dispositivos WHERE area_id = %s AND maquina_unidad = %s", (aid, tipo_eq))
        cnt = cur.fetchone()[0] + 1
        c.close()
        
        tag_val = f"{tag_prefix}-{cnt:02d}"
        add_device(aid, tag_val, "PLC", "Industrial OT", "192.168.1." + str(50 + cnt), "Profinet", "P1", "P2", tipo_eq, "Tablero Principal", 45.0 + (cnt * 3.0), 52.0)
    except Exception as e:
        print(f"Error en equipo rápido: {e}")

def main(page: ft.Page):
    try:
        init_db()
    except Exception as ex:
        print(f"Aviso de base de datos en UI: {ex}")

    page.title = "Mapa de Red Industrial OT"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.BLACK
    page.padding = 8

    menu_panel = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=6)
    markers_layer = ft.Stack(expand=True)
    
    elemento_seleccionado = {"tipo": None, "id": None, "nombre": ""}
    area_activa_id = {"id": None}
    modo_mover_area = {"activo": False}
    modo_marcar_plano = {"activo": False}

    def obtener_deltas_drag(e):
        if hasattr(e, 'delta_x') and e.delta_x is not None:
            return float(e.delta_x), float(getattr(e, 'delta_y', 0.0))
        if hasattr(e, 'data') and e.data:
            try:
                import json
                d = json.loads(e.data)
                if isinstance(d, dict):
                    dx = d.get('dx', d.get('delta_x', 0.0))
                    dy = d.get('dy', d.get('delta_y', 0.0))
                    return float(dx or 0.0), float(dy or 0.0)
            except Exception:
                pass
        return 0.0, 0.0

    def seleccionar_o_explorar_area(aid, anom, px, py):
        if modo_mover_area["activo"]:
            elemento_seleccionado.update({"tipo": "area", "id": aid, "nombre": anom})
            enfocar_en_esquema(float(px or 40.0), float(py or 50.0), aid)
            view_area_machines(aid, anom)
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Modo Mover: Zona '{anom}' seleccionada. Usa el D-Pad para ubicarla.", size=11, color=ft.Colors.WHITE),
                duration=2200,
                bgcolor="#161b22",
            )
            page.snack_bar.open = True
            page.update()
        else:
            enfocar_en_esquema(float(px or 40.0), float(py or 50.0), aid)
            view_area_machines(aid, anom)

    def actualizar_pines_plano():
        markers_layer.controls.clear()
        areas_lista = get_areas()
        
        controles_areas = []
        controles_dispositivos = []

        zoom_actual = contenedor_zoom_plano.scale
        factor_escala = max(0.5, min(1.2, 1.0 / (zoom_actual ** 0.5)))

        for a_id, nom, desc, px, py in areas_lista:
            pos_x = float(px if px is not None else 40.0)
            pos_y = float(py if py is not None else 50.0)
            
            es_activa = (area_activa_id["id"] == a_id)

            pin_box = ft.Container(
                left=pos_x * 4.6,
                top=pos_y * 7.2,
            )

            def al_arrastrar_pin(e, box=pin_box):
                if not sesion_iniciada:
                    return
                try:
                    dx, dy = obtener_deltas_drag(e)
                    if dx != 0.0 or dy != 0.0:
                        box.left = max(5, min(440, (box.left or 0) + dx))
                        box.top = max(5, min(700, (box.top or 0) + dy))
                        page.update()
                except Exception:
                    pass

            def al_soltar_pin(e, box=pin_box, aid=a_id, an=nom, d=desc):
                if not sesion_iniciada:
                    return
                try:
                    nx = round((box.left or 0) / 4.6, 1)
                    ny = round((box.top or 0) / 7.2, 1)
                    update_area(aid, an, d, px=nx, py=ny)
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Ubicación de '{an}' guardada ({nx}%, {ny}%)", size=11, color=ft.Colors.WHITE),
                        duration=1600,
                        bgcolor="#161b22",
                    )
                    page.snack_bar.open = True
                    page.update()
                except Exception:
                    pass

            if area_activa_id["id"] is None:
                tam_pin = int(22 * factor_escala)
                tooltip_txt = f"Zona: {nom} (Clic para explorar)"
                contenido_marcador_area = ft.Column(
                    controls=[
                        ft.Icon(
                            ft.Icons.LOCATION_ON,
                            color=ft.Colors.AMBER,
                            size=tam_pin,
                            tooltip=tooltip_txt,
                        ),
                        ft.Container(
                            content=ft.Text(
                                nom,
                                size=max(7, int(10 * factor_escala)),
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.AMBER,
                                no_wrap=True,
                            ),
                            bgcolor=ft.Colors.with_opacity(0.85, "#0b0e14"),
                            border_radius=4,
                            padding=3,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                    tight=True,
                )

                pin_box.content = ft.GestureDetector(
                    on_pan_update=al_arrastrar_pin if sesion_iniciada else None,
                    on_pan_end=al_soltar_pin if sesion_iniciada else None,
                    on_tap=lambda _, aid=a_id, anom=nom, x=pos_x, y=pos_y: seleccionar_o_explorar_area(aid, anom, x, y),
                    content=contenido_marcador_area,
                )
                controles_areas.append(pin_box)

            if es_activa:
                dispositivos_area = get_devices_in_area(a_id)
                for d_id, d_tag, d_tipo, d_mod, d_ip, d_con, d_tloc, d_tdst, d_maq, d_tab, d_px, d_py in dispositivos_area:
                    if not d_tag or d_tag.strip() in ("", "Equipo_Sin_Tag", "Dispositivo_S/T"):
                        continue
                    dx = float(d_px if d_px is not None else pos_x + 3.0)
                    dy = float(d_py if d_py is not None else pos_y + 3.0)

                    icon_ref = ft.Icons.SETTINGS_INPUT_COMPONENT
                    color_ref = ft.Colors.GREEN
                    m_lower = (d_maq or "").lower()

                    if "motor" in m_lower:
                        icon_ref = ft.Icons.SETTINGS_POWER
                        color_ref = ft.Colors.YELLOW
                    elif "compresor" in m_lower and "turbo" not in m_lower:
                        icon_ref = ft.Icons.COMPRESS
                        color_ref = ft.Colors.ORANGE
                    elif "turbo generador" in m_lower or "tgen" in m_lower or "turbina" in m_lower:
                        icon_ref = ft.Icons.WIND_POWER
                        color_ref = ft.Colors.CYAN
                    elif "turbo compresor" in m_lower or "tcomp" in m_lower:
                        icon_ref = ft.Icons.AIR
                        color_ref = ft.Colors.LIGHT_BLUE
                    elif "gabinete" in m_lower or "tablero" in m_lower or "ucp" in m_lower:
                        icon_ref = ft.Icons.DASHBOARD
                        color_ref = ft.Colors.AMBER
                    else:
                        icon_ref = ft.Icons.MEMORY
                        color_ref = ft.Colors.GREEN

                    disp_box = ft.Container(
                        left=dx * 4.6,
                        top=dy * 7.2,
                    )

                    def al_arrastrar_disp(e, box=disp_box):
                        if not sesion_iniciada:
                            return
                        try:
                            dx_d, dy_d = obtener_deltas_drag(e)
                            if dx_d != 0.0 or dy_d != 0.0:
                                box.left = max(5, min(440, (box.left or 0) + dx_d))
                                box.top = max(5, min(700, (box.top or 0) + dy_d))
                                page.update()
                        except Exception:
                            pass

                    def al_soltar_disp(e, box=disp_box, did=d_id, dtag=d_tag):
                        if not sesion_iniciada:
                            return
                        try:
                            nx = round((box.left or 0) / 4.6, 1)
                            ny = round((box.top or 0) / 7.2, 1)
                            update_device_pos(did, nx, ny)
                            page.snack_bar = ft.SnackBar(
                                ft.Text(f"Ubicación de '{dtag}' guardada ({nx}%, {ny}%)", size=11, color=ft.Colors.WHITE),
                                duration=1500,
                                bgcolor="#161b22",
                            )
                            page.snack_bar.open = True
                            page.update()
                        except Exception:
                            pass

                    tam_icono = int(22 * factor_escala)
                    tam_fuente = max(7, int(9 * factor_escala))

                    disp_content = ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(icon_ref, color=color_ref, size=tam_icono),
                                bgcolor=ft.Colors.with_opacity(0.85, "#0b0e14"),
                                border_radius=10,
                                padding=4,
                                tooltip=f"{d_maq}: {d_tag}",
                            ),
                            ft.Container(
                                content=ft.Text(
                                    d_tag if d_tag else "Equipo",
                                    size=tam_fuente,
                                    weight=ft.FontWeight.BOLD,
                                    color=color_ref,
                                    no_wrap=True,
                                ),
                                bgcolor=ft.Colors.with_opacity(0.85, "#0b0e14"),
                                border_radius=3,
                                padding=3,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                        tight=True,
                    )

                    def al_tocar_dispositivo(did, aid_val, an, m, dt):
                        if modo_mover_area["activo"]:
                            elemento_seleccionado.update({"tipo": "dispositivo", "id": did, "nombre": f"{m}: {dt}"})
                            page.snack_bar = ft.SnackBar(
                                ft.Text(f"Modo Mover: '{m}: {dt}' seleccionado. Usa el D-Pad.", size=11, color=ft.Colors.WHITE),
                                duration=2200,
                                bgcolor="#161b22",
                            )
                            page.snack_bar.open = True
                            page.update()
                            view_area_machines(aid_val, an)
                        else:
                            elemento_seleccionado.update({"tipo": "dispositivo", "id": did, "nombre": f"{m}: {dt}"})
                            view_device(did, aid_val, an, m)

                    disp_box.content = ft.GestureDetector(
                        on_pan_update=al_arrastrar_disp if sesion_iniciada else None,
                        on_pan_end=al_soltar_disp if sesion_iniciada else None,
                        on_tap=lambda _, did=d_id, aid_val=a_id, an=nom, m=d_maq, dt=d_tag: al_tocar_dispositivo(did, aid_val, an, m, dt),
                        content=disp_content,
                    )

                    controles_dispositivos.append(disp_box)

        markers_layer.controls.extend(controles_areas)
        markers_layer.controls.extend(controles_dispositivos)
        page.update()

    contenedor_zoom_plano = ft.Container(
        scale=1.0,
        offset=ft.Offset(0, 0),
        animate_scale=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
        expand=True,
    )

    def enfocar_en_esquema(px, py, aid=None):
        if aid is not None:
            area_activa_id["id"] = aid
            actualizar_pines_plano()
        
        zoom_nivel = 2.2
        desplazamiento_x = (0.5 - (px / 100.0)) * 0.70
        desplazamiento_y = (0.5 - (py / 100.0)) * 0.70
        
        contenedor_zoom_plano.scale = zoom_nivel
        contenedor_zoom_plano.offset = ft.Offset(desplazamiento_x, desplazamiento_y)
        btn_reset_zoom.visible = True
        actualizar_pines_plano()
        page.update()

    def restablecer_esquema():
        contenedor_zoom_plano.scale = 1.0
        contenedor_zoom_plano.offset = ft.Offset(0, 0)
        btn_reset_zoom.visible = False
        area_activa_id["id"] = None
        actualizar_pines_plano()
        page.update()

    def hacer_zoom_in(e):
        contenedor_zoom_plano.scale = min(3.5, contenedor_zoom_plano.scale + 0.3)
        btn_reset_zoom.visible = True
        actualizar_pines_plano()
        page.update()

    def hacer_zoom_out(e):
        contenedor_zoom_plano.scale = max(0.8, contenedor_zoom_plano.scale - 0.3)
        if contenedor_zoom_plano.scale <= 1.0:
            btn_reset_zoom.visible = False
            contenedor_zoom_plano.offset = ft.Offset(0, 0)
        actualizar_pines_plano()
        page.update()

    def desplazar_pan(dx, dy):
        curr_offset = contenedor_zoom_plano.offset
        nuevo_x = (curr_offset.x if curr_offset else 0.0) + dx
        nuevo_y = (curr_offset.y if curr_offset else 0.0) + dy
        contenedor_zoom_plano.offset = ft.Offset(nuevo_x, nuevo_y)
        btn_reset_zoom.visible = True
        page.update()

    btn_reset_zoom = ft.IconButton(
        icon=ft.Icons.ZOOM_OUT_MAP,
        tooltip="Restablecer Vista Completa",
        icon_color=ft.Colors.AMBER,
        icon_size=18,
        visible=False,
        on_click=lambda _: restablecer_esquema(),
    )

    controles_navegacion_plano = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_UP, tooltip="Mover Arriba", icon_color=ft.Colors.CYAN, icon_size=16, on_click=lambda _: desplazar_pan(0.0, 0.12)),
            ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_DOWN, tooltip="Mover Abajo", icon_color=ft.Colors.CYAN, icon_size=16, on_click=lambda _: desplazar_pan(0.0, -0.12)),
            ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_LEFT, tooltip="Mover Izquierda", icon_color=ft.Colors.CYAN, icon_size=16, on_click=lambda _: desplazar_pan(0.12, 0.0)),
            ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_RIGHT, tooltip="Mover Derecha", icon_color=ft.Colors.CYAN, icon_size=16, on_click=lambda _: desplazar_pan(-0.12, 0.0)),
            ft.VerticalDivider(width=4, color=ft.Colors.GREY_800),
            ft.IconButton(icon=ft.Icons.ZOOM_IN, tooltip="Acercar Zoom (+)", icon_color=ft.Colors.CYAN, icon_size=16, on_click=hacer_zoom_in),
            ft.IconButton(icon=ft.Icons.ZOOM_OUT, tooltip="Alejar Zoom (-)", icon_color=ft.Colors.CYAN, icon_size=16, on_click=hacer_zoom_out),
            btn_reset_zoom,
        ],
        spacing=2,
        tight=True,
    )

    panel_flotante_navegacion = ft.Container(
        content=controles_navegacion_plano,
        bgcolor=ft.Colors.with_opacity(0.88, "#0b0e14"),
        border_radius=8,
        padding=4,
    )

    def alternar_modo_marcar(e):
        if not sesion_iniciada:
            view_login()
            return
        modo_marcar_plano["activo"] = not modo_marcar_plano["activo"]
        btn_marcar_plano.icon_color = ft.Colors.CYAN if modo_marcar_plano["activo"] else ft.Colors.GREY
        page.update()

    def alternar_modo_mover(e):
        if not sesion_iniciada:
            view_login()
            return
        modo_mover_area["activo"] = not modo_mover_area["activo"]
        btn_modo_mover.icon_color = ft.Colors.AMBER if modo_mover_area["activo"] else ft.Colors.GREY
        estado_txt = "ACTIVADO (Menú D-Pad desplegado)" if modo_mover_area["activo"] else "BLOQUEADO / DESACTIVADO"
        page.snack_bar = ft.SnackBar(
            ft.Text(f"Modo Mover Elementos: {estado_txt}", size=11, color=ft.Colors.WHITE),
            duration=2200,
            bgcolor="#161b22",
        )
        page.snack_bar.open = True
        page.update()
        if area_activa_id["id"] is not None:
            for aid, nom, _, _, _ in get_areas():
                if aid == area_activa_id["id"]:
                    view_area_machines(aid, nom)
                    break

    btn_modo_mover = ft.IconButton(
        icon=ft.Icons.OPEN_WITH,
        tooltip="Bloquear/Desbloquear menús de movimiento D-Pad",
        icon_color=ft.Colors.GREY,
        icon_size=20,
        on_click=alternar_modo_mover,
    )

    btn_marcar_plano = ft.IconButton(
        icon=ft.Icons.ADD_LOCATION_ALT,
        tooltip="Tocar en el plano para ubicar nueva zona",
        icon_color=ft.Colors.GREY,
        icon_size=20,
        on_click=alternar_modo_marcar,
    )

    def ejecutar_con_permiso(accion, volver_accion):
        global sesion_iniciada
        if sesion_iniciada:
            accion()
        else:
            view_login(accion_post=accion, volver_accion=volver_accion)

    def view_login(accion_post=None, volver_accion=None):
        global sesion_iniciada
        menu_panel.controls.clear()
        retorno = volver_accion if volver_accion else view_home

        if sesion_iniciada:
            def cerrar_sesion(e):
                global sesion_iniciada
                sesion_iniciada = False
                view_home()

            menu_panel.controls.extend([
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_size=18,
                            on_click=lambda _: retorno(),
                        ),
                        ft.Text("Perfil de Usuario", size=15, weight=ft.FontWeight.BOLD),
                    ]
                ),
                ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=20),
                                        ft.Text("Camilo Acevedo", size=14, weight=ft.FontWeight.BOLD),
                                    ]
                                ),
                                ft.Text("Rol: Administrador de Red y Control Industrial", color=ft.Colors.GREEN, size=11),
                                ft.Divider(height=2, color=ft.Colors.GREY),
                                btn("Cerrar Sesión", cerrar_sesion, bg=ft.Colors.RED_800, ic=ft.Icons.LOCK),
                                btn("Volver al Panel", lambda _: retorno(), bg=ft.Colors.GREY_800),
                            ],
                            spacing=5,
                        ),
                    )
                ),
            ])
            page.update()
            return

        txt_user = ft.TextField(label="Usuario", hint_text="Ingresa tu usuario", autofocus=True, dense=True)
        txt_pin = ft.TextField(label="Contraseña", password=True, can_reveal_password=False, keyboard_type=ft.KeyboardType.NUMBER, hint_text="••••", dense=True)
        msg_error = ft.Text("", color=ft.Colors.RED_400, size=11)

        def login_submit(e):
            global sesion_iniciada
            u_ok = txt_user.value and txt_user.value.strip().lower() == USUARIO_ADMIN
            p_hash = hash_pin(txt_pin.value) if txt_pin.value else ""
            p_ok = (p_hash == HASH_PIN_ALMACENADO)

            if u_ok and p_ok:
                sesion_iniciada = True
                if accion_post:
                    accion_post()
                else:
                    view_home()
            else:
                msg_error.value = "Credenciales incorrectas."
                page.update()

        menu_panel.controls.extend([
            ft.Row(
                controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=18, on_click=lambda _: retorno()),
                    ft.Text("Acceso de Administrador", size=15, weight=ft.FontWeight.BOLD),
                ]
            ),
            ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Column(
                        controls=[
                            txt_user,
                            txt_pin,
                            msg_error,
                            btn("Iniciar Sesión", login_submit, bg=ft.Colors.AMBER_700, ic=ft.Icons.LOGIN),
                            btn("Cancelar", lambda _: retorno(), bg=ft.Colors.GREY_800),
                        ],
                        spacing=5,
                    ),
                )
            ),
        ])
        page.update()

    def confirmar_eliminar(titulo, mensaje, ejecutar_eliminar, volver_accion):
        menu_panel.controls.clear()
        menu_panel.controls.extend([
            ft.Row(
                controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=18, on_click=lambda _: volver_accion()),
                    ft.Text("Confirmar Eliminación", size=14, weight=ft.FontWeight.BOLD),
                ]
            ),
            ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.WARNING, color=ft.Colors.RED_400, size=20),
                                    ft.Text(titulo, weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.RED_300),
                                ]
                            ),
                            ft.Text(mensaje, size=11, color=ft.Colors.GREY_300),
                            btn("Eliminar Definitivamente", lambda _: ejecutar_eliminar(), bg=ft.Colors.RED_800, ic=ft.Icons.DELETE_FOREVER),
                            btn("Cancelar", lambda _: volver_accion(), bg=ft.Colors.GREY_800),
                        ],
                        spacing=5,
                    ),
                )
            ),
        ])
        page.update()

    def view_device(did, aid, anom, maq):
        global sesion_iniciada
        d_info = get_device_by_id(did)
        if not d_info:
            view_machine_boards(aid, anom, maq)
            return
        _, tag, tipo, mod, ip, t_con, t_loc, t_dst, maq_db, tab, _, _, _ = d_info

        menu_panel.controls.clear()
        routes = get_routes(did)
        r_col = ft.Column(spacing=3)
        if routes:
            for proto, med, dst, sys in routes:
                r_col.controls.append(
                    ft.Container(
                        bgcolor=ft.Colors.with_opacity(0.85, "#161b22"),
                        border_radius=5,
                        padding=6,
                        content=ft.Column(
                            controls=[
                                ft.Row(controls=[ft.Icon(ft.Icons.SETTINGS_ETHERNET, color=ft.Colors.TEAL, size=14), ft.Text(f"Protocolo: {proto}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=11)]),
                                ft.Text(f"• Medio: {med if med else 'No especificado'}", size=10, color=ft.Colors.GREY_300),
                                ft.Text(f"• Conecta a: {dst if dst else 'No especificado'}", size=10, color=ft.Colors.AMBER),
                                ft.Text(f"• Sistema: {sys if sys else 'No especificado'}", size=10, color=ft.Colors.LIGHT_BLUE),
                            ],
                            spacing=1,
                        ),
                    )
                )
        else:
            r_col.controls.append(ft.Text("Sin enlaces adicionales.", italic=True, color=ft.Colors.GREY_500, size=10))

        row_header_controls = [
            ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=18, on_click=lambda _: view_machine_boards(aid, anom, maq)),
            ft.Text(tag if tag else "Dispositivo", size=16, weight=ft.FontWeight.BOLD, expand=True),
            ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, tooltip="Editar Equipo", icon_color=ft.Colors.AMBER, on_click=lambda _: ejecutar_con_permiso(lambda: form_device(aid, anom, did, maq), lambda: view_device(did, aid, anom, maq))),
        ]
        if sesion_iniciada:
            row_header_controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Eliminar Equipo", icon_color=ft.Colors.RED_400, icon_size=18, on_click=lambda _: confirmar_eliminar(f"¿Eliminar {tag}?", f"Se eliminará el equipo '{tag}'.", lambda: (delete_device(did), view_machine_boards(aid, anom, maq)), lambda: view_device(did, aid, anom, maq))))

        row_header_controls.append(ft.IconButton(icon=ft.Icons.ADD_LINK, tooltip="Agregar Enlace", icon_color=ft.Colors.TEAL, icon_size=18, on_click=lambda _: ejecutar_con_permiso(lambda: form_route(did, aid, anom, maq), lambda: view_device(did, aid, anom, maq))))

        menu_panel.controls.extend([
            ft.Row(controls=row_header_controls),
            ft.Card(
                content=ft.Container(
                    padding=8,
                    content=ft.Column(
                        controls=[
                            ft.Row(controls=[ft.Icon(ft.Icons.PRECISION_MANUFACTURING, color=ft.Colors.AMBER, size=16), ft.Text(f"Máquina: {maq_db if maq_db else 'General'}", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.AMBER)]),
                            ft.Row(controls=[ft.Icon(ft.Icons.DASHBOARD, color=ft.Colors.YELLOW, size=14), ft.Text(f"Tablero: {tab if tab else 'General'}", weight=ft.FontWeight.BOLD, size=11, color=ft.Colors.YELLOW)]),
                            ft.Divider(height=1, color=ft.Colors.GREY_800),
                            ft.Row(controls=[ft.Icon(ft.Icons.MEMORY, color=ft.Colors.BLUE_400, size=14), ft.Text(f"Tipo: {tipo} ({mod if mod else 'S/M'})", weight=ft.FontWeight.BOLD, size=11)]),
                            ft.Row(controls=[ft.Icon(ft.Icons.ROUTER, color=ft.Colors.GREEN, size=14), ft.Text(f"IP: {ip if ip else 'No asignada'}", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN, size=12)]),
                            ft.Text(f"• Red: {t_con if t_con else 'Pendiente'}", size=11, color=ft.Colors.ORANGE),
                            ft.Text(f"• Tarjeta Local: {t_loc if t_loc else 'Pendiente'}", size=10, color=ft.Colors.GREY_300),
                            ft.Text(f"• Tarjeta Destino: {t_dst if t_dst else 'Pendiente'}", size=10, color=ft.Colors.AMBER),
                        ],
                        spacing=2,
                    ),
                )
            ),
            ft.Text("Rutas y Enlaces de Comunicación:", size=12, weight=ft.FontWeight.BOLD),
            r_col,
        ])
        page.update()

    def view_machine_boards(aid, anom, maq):
        global sesion_iniciada
        menu_panel.controls.clear()
        devs = get_devices_by_machine(aid, maq)

        tableros_dict = {}
        for row in devs:
            did, tag, tipo, mod, ip, t_con, t_loc, t_dst, maq_u, tab, _, _ = row
            t_nombre = tab if tab and tab.strip() else "Tablero General / Local"
            if t_nombre not in tableros_dict:
                tableros_dict[t_nombre] = []
            tableros_dict[t_nombre].append(row)

        b_col = ft.Column(spacing=4)
        for t_nombre, items in tableros_dict.items():
            items_col = ft.Column(spacing=2)
            for item in items:
                d_id, d_tag, d_tipo, d_mod, d_ip, d_con, _, _, _, _, _, _ = item
                ic = ft.Icons.MEMORY if d_tipo == "PLC" else ft.Icons.DEVELOPER_BOARD
                col = ft.Colors.CYAN if d_tipo == "PLC" else ft.Colors.ORANGE

                row_eq_controls = [
                    ft.Icon(ic, color=col, size=16),
                    ft.Column(
                        controls=[
                            ft.Text(f"{d_tag} ({d_tipo})", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=11),
                            ft.Text(f"IP: {d_ip if d_ip else 'S/IP'}", size=9, color=ft.Colors.GREY_300),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                ]
                if sesion_iniciada:
                    row_eq_controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400, icon_size=16, on_click=lambda _, i=d_id, t=d_tag: confirmar_eliminar(f"¿Eliminar {t}?", f"Se eliminará el equipo '{t}'.", lambda: (delete_device(i), view_machine_boards(aid, anom, maq)), lambda: view_machine_boards(aid, anom, maq))))
                row_eq_controls.append(ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_color=ft.Colors.GREY_400, icon_size=16, on_click=lambda _, i=d_id: view_device(i, aid, anom, maq)))

                items_col.controls.append(
                    ft.Container(bgcolor=ft.Colors.with_opacity(0.70, "#161b22"), border_radius=4, padding=4, content=ft.Row(controls=row_eq_controls))
                )

            b_col.controls.append(
                ft.Card(
                    elevation=1,
                    content=ft.Container(
                        padding=6,
                        content=ft.Column(
                            controls=[
                                ft.Row(controls=[ft.Icon(ft.Icons.DASHBOARD, color=ft.Colors.AMBER, size=14), ft.Text(f"Tablero: {t_nombre}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER)], spacing=5),
                                ft.Divider(height=1, color=ft.Colors.GREY_800),
                                items_col,
                            ],
                            spacing=3,
                        ),
                    ),
                )
            )

        menu_panel.controls.extend([
            ft.Row(
                controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=18, on_click=lambda _: view_area_machines(aid, anom)),
                    ft.Column(controls=[ft.Text(maq, size=15, weight=ft.FontWeight.BOLD), ft.Text(f"Tableros en {anom}", size=10, color=ft.Colors.GREY_400)], spacing=1, expand=True),
                    ft.IconButton(icon=ft.Icons.ADD_BOX, tooltip="Agregar Equipo", icon_color=ft.Colors.CYAN, icon_size=20, on_click=lambda _: ejecutar_con_permiso(lambda: form_device(aid, anom, default_maq=maq), lambda: view_machine_boards(aid, anom, maq))),
                ]
            ),
            b_col,
        ])
        page.update()

    def view_area_machines(aid, anom):
        global sesion_iniciada
        area_activa_id["id"] = aid
        actualizar_pines_plano()

        areas_lista = get_areas()
        for a_id, nom, desc, px, py in areas_lista:
            if a_id == aid:
                enfocar_en_esquema(float(px or 40.0), float(py or 50.0), a_id)
                break

        menu_panel.controls.clear()
        maquinas = get_machines_in_area_strict(aid)
        m_col = ft.Column(spacing=3)

        if maquinas:
            for maq in maquinas:
                trailing_controls = []
                if sesion_iniciada:
                    trailing_controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400, icon_size=16, on_click=lambda _, m=maq: confirmar_eliminar(f"¿Eliminar {m}?", f"Se eliminará la máquina '{m}'.", lambda: (delete_machine(aid, m), view_area_machines(aid, anom)), lambda: view_area_machines(aid, anom))))
                trailing_controls.append(ft.IconButton(icon=ft.Icons.ARROW_FORWARD_IOS, icon_size=12, on_click=lambda _, m=maq: view_machine_boards(aid, anom, m)))

                m_col.controls.append(
                    ft.Card(elevation=1, content=ft.ListTile(dense=True, leading=ft.Icon(ft.Icons.PRECISION_MANUFACTURING, color=ft.Colors.ORANGE, size=18), title=ft.Text(maq, weight=ft.FontWeight.BOLD, size=12), subtitle=ft.Text(f"Unidad en {anom}", size=9), trailing=ft.Row(controls=trailing_controls, width=60 if sesion_iniciada else 30, spacing=0), on_click=lambda _, m=maq: view_machine_boards(aid, anom, m)))
                )
        else:
            m_col.controls.append(ft.Text(f"No hay máquinas en {anom}.", color=ft.Colors.GREY_500, size=11))

        def eliminar_seleccionado_seguro(aid_val, anom_val):
            if elemento_seleccionado["tipo"] == "dispositivo" and elemento_seleccionado["id"] is not None:
                did = elemento_seleccionado["id"]
                d_info = get_device_by_id(did)
                d_tag = d_info[1] if d_info else "Equipo"
                delete_device(did)
                elemento_seleccionado.update({"tipo": None, "id": None, "nombre": ""})
                actualizar_pines_plano()
                view_area_machines(aid_val, anom_val)
                page.snack_bar = ft.SnackBar(ft.Text(f"Elemento '{d_tag}' eliminado correctamente del plano.", size=11, color=ft.Colors.WHITE), bgcolor="#161b22")
                page.snack_bar.open = True
                page.update()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ Primero debes seleccionar/tocar un icono o equipo en el plano para poder borrarlo de forma segura.", size=11, color=ft.Colors.WHITE), bgcolor="#3d2211")
                page.snack_bar.open = True
                page.update()

        nombre_sel_txt = elemento_seleccionado["nombre"] if elemento_seleccionado["nombre"] else "Ninguno seleccionado"

        btn_eliminar_seleccionado = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.DELETE_OUTLINE, size=15, color=ft.Colors.RED), ft.Text(f"Eliminar: {nombre_sel_txt[:22]}", size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], spacing=4, tight=True),
            bgcolor=ft.Colors.with_opacity(0.8, "#3d1111"), padding=6, border_radius=6,
            on_click=lambda _: eliminar_seleccionado_seguro(aid, anom),
            tooltip="Selecciona un equipo en el plano y haz clic aquí para borrar únicamente ese elemento",
        )

        admin_icons_card = ft.Container()
        if sesion_iniciada:
            admin_icons_card = ft.Card(
                elevation=3,
                content=ft.Container(
                    padding=10,
                    bgcolor=ft.Colors.with_opacity(0.92, "#0d1117"),
                    border_radius=8,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=16, color=ft.Colors.CYAN),
                                    ft.Text("Biblioteca de Iconos OT (Haz clic para agregar al plano)", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN),
                                ],
                                spacing=6,
                                tight=True,
                            ),
                            ft.Divider(height=4, color=ft.Colors.GREY_800),
                            ft.Row(
                                controls=[
                                    ft.GestureDetector(
                                        on_tap=lambda _: (agregar_equipo_rapido(aid, anom, "Motor", "MOTOR"), view_area_machines(aid, anom)),
                                        content=ft.Container(
                                            content=ft.Row([ft.Icon(ft.Icons.SETTINGS_POWER, size=14, color=ft.Colors.YELLOW), ft.Text("Motor", size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], spacing=2, tight=True),
                                            bgcolor=ft.Colors.with_opacity(0.8, "#21262d"), padding=4, border_radius=6,
                                            tooltip="Agregar Motor",
                                        ),
                                    ),
                                    ft.GestureDetector(
                                        on_tap=lambda _: (agregar_equipo_rapido(aid, anom, "Compresor", "COMP"), view_area_machines(aid, anom)),
                                        content=ft.Container(
                                            content=ft.Row([ft.Icon(ft.Icons.COMPRESS, size=14, color=ft.Colors.ORANGE), ft.Text("Compresor", size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], spacing=2, tight=True),
                                            bgcolor=ft.Colors.with_opacity(0.8, "#21262d"), padding=4, border_radius=6,
                                            tooltip="Agregar Compresor",
                                        ),
                                    ),
                                    ft.GestureDetector(
                                        on_tap=lambda _: (agregar_equipo_rapido(aid, anom, "Turbo Generador", "TGEN"), view_area_machines(aid, anom)),
                                        content=ft.Container(
                                            content=ft.Row([ft.Icon(ft.Icons.WIND_POWER, size=14, color=ft.Colors.CYAN), ft.Text("Turbo Gen", size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], spacing=2, tight=True),
                                            bgcolor=ft.Colors.with_opacity(0.8, "#21262d"), padding=4, border_radius=6,
                                            tooltip="Agregar Turbo Generador",
                                        ),
                                    ),
                                    ft.GestureDetector(
                                        on_tap=lambda _: (agregar_equipo_rapido(aid, anom, "Turbo Compresor", "TCOMP"), view_area_machines(aid, anom)),
                                        content=ft.Container(
                                            content=ft.Row([ft.Icon(ft.Icons.AIR, size=14, color=ft.Colors.LIGHT_BLUE), ft.Text("Turbo Comp", size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], spacing=2, tight=True),
                                            bgcolor=ft.Colors.with_opacity(0.8, "#21262d"), padding=4, border_radius=6,
                                            tooltip="Agregar Turbo Compresor",
                                        ),
                                    ),
                                    ft.GestureDetector(
                                        on_tap=lambda _: (agregar_equipo_rapido(aid, anom, "Gabinete / Tablero", "UCP"), view_area_machines(aid, anom)),
                                        content=ft.Container(
                                            content=ft.Row([ft.Icon(ft.Icons.DASHBOARD, size=14, color=ft.Colors.AMBER), ft.Text("Tablero", size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], spacing=2, tight=True),
                                            bgcolor=ft.Colors.with_opacity(0.8, "#21262d"), padding=4, border_radius=6,
                                            tooltip="Agregar Gabinete / Tablero de Control",
                                        ),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                tight=True,
                            ),
                            ft.Divider(height=4, color=ft.Colors.GREY_800),
                            ft.Row(
                                controls=[btn_eliminar_seleccionado],
                                alignment=ft.MainAxisAlignment.CENTER,
                                tight=True,
                            ),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                ),
            )

        dpad_card = ft.Container()
        if sesion_iniciada and modo_mover_area["activo"]:
            def mover_elemento_dpad(dx, dy):
                if elemento_seleccionado["tipo"] == "dispositivo" and elemento_seleccionado["id"] is not None:
                    did = elemento_seleccionado["id"]
                    d_info = get_device_by_id(did)
                    if d_info:
                        _, _, _, _, _, _, _, _, _, _, _, px_d, py_d = d_info
                        nx = max(2.0, min(98.0, float(px_d or 42.0) + dx))
                        ny = max(2.0, min(98.0, float(py_d or 52.0) + dy))
                        update_device_pos(did, nx, ny)
                        actualizar_pines_plano()
                else:
                    areas_l = get_areas()
                    for ai, nom_a, desc_a, px_a, py_a in areas_l:
                        if ai == aid:
                            nx = max(2.0, min(98.0, float(px_a or 40.0) + dx))
                            ny = max(2.0, min(98.0, float(py_a or 50.0) + dy))
                            update_area(ai, nom_a, desc_a, nx, ny)
                            actualizar_pines_plano()
                            break

            lbl_seleccion = ft.Text(
                f"Control de Movimiento: {'Área ' + anom if not elemento_seleccionado['nombre'] else elemento_seleccionado['nombre']}",
                size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN
            )

            dpad_card = ft.Card(
                elevation=3,
                content=ft.Container(
                    padding=10,
                    bgcolor=ft.Colors.with_opacity(0.85, "#0b0e14"),
                    content=ft.Column(
                        controls=[
                            lbl_seleccion,
                            ft.Row(
                                controls=[
                                    ft.Container(width=34),
                                    ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_UP, icon_size=18, tooltip="Subir", on_click=lambda _: mover_elemento_dpad(0.0, -1.5), bgcolor=ft.Colors.GREY_800),
                                    ft.Container(width=34),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND, spacing=2, tight=True,
                            ),
                            ft.Row(
                                controls=[
                                    ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_LEFT, icon_size=18, tooltip="Izquierda", on_click=lambda _: mover_elemento_dpad(-1.5, 0.0), bgcolor=ft.Colors.GREY_800),
                                    ft.Icon(ft.Icons.NEAR_ME, color=ft.Colors.CYAN, size=16),
                                    ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_RIGHT, icon_size=18, tooltip="Derecha", on_click=lambda _: mover_elemento_dpad(1.5, 0.0), bgcolor=ft.Colors.GREY_800),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND, spacing=8, tight=True,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Container(width=34),
                                    ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_DOWN, icon_size=18, tooltip="Bajar", on_click=lambda _: mover_elemento_dpad(0.0, 1.5), bgcolor=ft.Colors.GREY_800),
                                    ft.Container(width=34),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND, spacing=2, tight=True,
                            ),
                            ft.Text("Botones de posición activa.", size=8, color=ft.Colors.GREY_400, italic=True),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, tight=True,
                    ),
                ),
            )

        menu_panel.controls.extend([
            ft.Row(
                controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=18, on_click=lambda _: view_home()),
                    ft.Column(controls=[ft.Text(anom, size=15, weight=ft.FontWeight.BOLD), ft.Text("Unidades de Trabajo", size=10, color=ft.Colors.GREY_400)], spacing=1, expand=True),
                    ft.IconButton(icon=ft.Icons.ADD_BOX, tooltip="Agregar Máquina", icon_color=ft.Colors.CYAN, icon_size=20, on_click=lambda _: ejecutar_con_permiso(lambda: form_device(aid, anom), lambda: view_area_machines(aid, anom))),
                ]
            ),
            admin_icons_card,
            dpad_card,
            m_col,
        ])
        page.update()

    def view_home():
        global sesion_iniciada
        area_activa_id["id"] = None
        actualizar_pines_plano()

        menu_panel.controls.clear()
        areas = get_areas()
        a_col = ft.Column(spacing=3)

        for aid, nom, desc, px, py in areas:
            trailing_controls = []
            if sesion_iniciada:
                trailing_controls.append(ft.IconButton(icon=ft.Icons.EDIT_LOCATION_ALT, icon_color=ft.Colors.AMBER, icon_size=16, tooltip="Mover y Gestionar Elementos", on_click=lambda _, i=aid, n=nom, x=px, y=py: (enfocar_en_esquema(float(x or 40.0), float(y or 50.0), i), view_area_machines(i, n))))
                trailing_controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED, icon_size=16, tooltip="Eliminar", on_click=lambda _, i=aid, n=nom: confirmar_eliminar(f"¿Eliminar {nom}?", f"Se eliminará el área.", lambda: (delete_area(i), view_home()), lambda: view_home())))

            trailing_controls.append(ft.IconButton(icon=ft.Icons.ARROW_FORWARD_IOS, icon_size=12, on_click=lambda _, i=aid, n=nom, x=px, y=py: (enfocar_en_esquema(float(x or 40.0), float(y or 50.0), i), view_area_machines(i, n))))

            a_col.controls.append(
                ft.Card(elevation=1, content=ft.ListTile(dense=True, leading=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.AMBER, size=18), title=ft.Text(nom, weight=ft.FontWeight.BOLD, size=12), subtitle=ft.Text(desc if desc else "Zona de trabajo", size=9), trailing=ft.Row(controls=trailing_controls, width=80 if sesion_iniciada else 30, spacing=0), on_click=lambda _, i=aid, n=nom, x=px, y=py: seleccionar_o_explorar_area(i, n, x, y)))
            )

        def on_search(e):
            val = e.control.value.strip()
            if not val:
                restablecer_esquema()
                view_home()
                return
            res = search_all(val)
            a_col.controls.clear()
            if res:
                primera = res[0]
                enfocar_en_esquema(float(primera[12] or 40.0), float(primera[13] or 50.0), primera[11])
                for row in res:
                    did, tag, tipo, mod, ip, t_con, t_loc, t_dst, maq, tab, anom, aid, px_s, py_s = row
                    a_col.controls.append(
                        ft.Card(elevation=1, content=ft.ListTile(dense=True, leading=ft.Icon(ft.Icons.SEARCH, color=ft.Colors.GREEN, size=16), title=ft.Text(f"{tag if tag else 'Equipo'} ({ip if ip else 'S/IP'})", weight=ft.FontWeight.BOLD, size=11), subtitle=ft.Text(f"Máq: {maq} | Tab: {tab}", size=9), on_click=lambda _, i=did, a=aid, an=anom, m=maq, x=px_s, y=py_s: (enfocar_en_esquema(float(x or 40.0), float(y or 50.0), a), view_device(i, a, an, m))))
                    )
            else:
                a_col.controls.append(ft.Text("No se encontró ningún equipo.", color=ft.Colors.RED_300, size=10))
            page.update()

        txt_search = ft.TextField(hint_text="Buscar IP, Tag, Tablero o Máquina...", prefix_icon=ft.Icons.SEARCH, border_radius=6, dense=True, on_change=on_search)

        color_perfil = ft.Colors.GREEN if sesion_iniciada else ft.Colors.AMBER
        tooltip_perfil = "Sesión Activa: Camilo Acevedo" if sesion_iniciada else "Iniciar Sesión"

        home_row_controls = [
            ft.Text("Áreas de Planta", size=16, weight=ft.FontWeight.BOLD, expand=True),
        ]
        if sesion_iniciada:
            home_row_controls.extend([
                btn_modo_mover,
                ft.IconButton(
                    icon=ft.Icons.ADD_LOCATION_ALT,
                    tooltip="Registrar Nueva Zona",
                    icon_color=ft.Colors.AMBER,
                    icon_size=20,
                    on_click=lambda _: ejecutar_con_permiso(lambda: form_area(), lambda: view_home()),
                )
            ])
        home_row_controls.append(
            ft.IconButton(
                icon=ft.Icons.ACCOUNT_CIRCLE,
                tooltip=tooltip_perfil,
                icon_color=color_perfil,
                icon_size=20,
                on_click=lambda _: view_login(),
            )
        )

        menu_panel.controls.extend([
            ft.Row(controls=home_row_controls),
            txt_search,
            ft.Divider(height=1, color=ft.Colors.TRANSPARENT),
            a_col,
        ])
        page.update()

    def form_area(aid=None, init_nom="", init_desc="", init_px=40.0, init_py=50.0):
        menu_panel.controls.clear()
        f_nom = ft.TextField(label="Nombre de Zona (ej: Compresión)", value=init_nom, dense=True)
        f_desc = ft.TextField(label="Descripción (ej: Skid 01)", value=init_desc, dense=True)
        f_px = ft.Slider(min=5, max=95, divisions=90, label="{value}%", value=init_px)
        f_py = ft.Slider(min=5, max=95, divisions=90, label="{value}%", value=init_py)

        def actualizar_pin_en_vivo(e):
            enfocar_en_esquema(f_px.value, f_py.value, aid)

        f_px.on_change = actualizar_pin_en_vivo
        f_py.on_change = actualizar_pin_en_vivo

        def save_a(e):
            if aid:
                update_area(aid, f_nom.value, f_desc.value, f_px.value, f_py.value)
            else:
                add_area(f_nom.value, f_desc.value, f_px.value, f_py.value)
            actualizar_pines_plano()
            view_home()

        titulo = "Editar Posición de Zona" if aid else "Registrar Zona en el Plano"
        menu_panel.controls.extend([
            ft.Row(controls=[ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=18, on_click=lambda _: view_home()), ft.Text(titulo, size=15, weight=ft.FontWeight.BOLD)]),
            f_nom, f_desc,
            ft.Text("Posición X (Horizontal en el plano):", size=10, color=ft.Colors.GREY_400), f_px,
            ft.Text("Posición Y (Vertical en el plano):", size=10, color=ft.Colors.GREY_400), f_py,
            btn("Guardar Zona y Ubicación", save_a, bg=ft.Colors.AMBER_700, ic=ft.Icons.SAVE),
            btn("Cancelar", lambda _: view_home(), bg=ft.Colors.GREY_800),
        ])
        page.update()

    def form_device(aid, anom, did=None, default_maq=""):
        menu_panel.controls.clear()
        d_existente = get_device_by_id(did) if did else None
        init_tag = d_existente[1] if d_existente and d_existente[1] else ""
        init_tipo = d_existente[2] if d_existente and d_existente[2] else "PLC"
        init_mod = d_existente[3] if d_existente and d_existente[3] else ""
        init_ip = d_existente[4] if d_existente and d_existente[4] else ""
        init_tcon = d_existente[5] if d_existente and d_existente[5] else ""
        init_tloc = d_existente[6] if d_existente and d_existente[6] else ""
        init_tdst = d_existente[7] if d_existente and d_existente[7] else ""
        init_maq = d_existente[8] if d_existente and d_existente[8] else (default_maq if default_maq else "")
        init_tab = d_existente[9] if d_existente and d_existente[9] else ""

        m_opts = ["Turbina", "Motogenerador", "Compresor", "Bomba", "Skid / Paquete de Proceso", "Subestación / MCC", "Tablero General de Control"]
        dd_m_opts = [ft.dropdown.Option(mo) if hasattr(ft, "dropdown") and hasattr(ft.dropdown, "Option") else ft.Option(mo) for mo in m_opts]
        f_maq_tipo = ft.Dropdown(label="Tipo de Unidad / Máquina", options=dd_m_opts, value="Turbina", dense=True)
        f_maq_tag = ft.TextField(label="Tag de Unidad (ej: Turbina TG-01)", value=init_maq, dense=True)
        f_tab_tag = ft.TextField(label="Tag del Tablero (ej: UCP-01)", value=init_tab, dense=True)
        f_tag = ft.TextField(label="Tag del Equipo (ej: PLC-TG01)", value=init_tag, dense=True)

        opts = ["PLC", "HMI", "Variador (VFD)", "Switch Industrial", "Conversor / Gateway", "Transmisor", "Módulo Remoto / RIO"]
        dd_opts = [ft.dropdown.Option(o) if hasattr(ft, "dropdown") and hasattr(ft.dropdown, "Option") else ft.Option(o) for o in opts]
        f_tipo = ft.Dropdown(label="Tipo de Dispositivo", options=dd_opts, value=init_tipo if init_tipo in opts else "PLC", dense=True)
        f_mod = ft.TextField(label="Modelo", value=init_mod, dense=True)
        f_ip = ft.TextField(label="IP", value=init_ip, dense=True)
        f_tcon = ft.TextField(label="Conexión (ej: Profinet)", value=init_tcon, dense=True)
        f_tloc = ft.TextField(label="Puerto Local", value=init_tloc, dense=True)
        f_tdst = ft.TextField(label="Puerto Destino", value=init_tdst, dense=True)

        def save_d(e):
            maq_val = f_maq_tag.value.strip() if f_maq_tag.value and f_maq_tag.value.strip() else f_maq_tipo.value
            tab_val = f_tab_tag.value.strip() if f_tab_tag.value and f_tab_tag.value.strip() else "Tablero General"
            tag_val = f_tag.value.strip() if f_tag.value and f_tag.value.strip() else "Equipo_Sin_Tag"

            if did:
                update_device(did, tag_val, f_tipo.value, f_mod.value, f_ip.value, f_tcon.value, f_tloc.value, f_tdst.value, maq_val, tab_val)
                view_device(did, aid, anom, maq_val)
            else:
                add_device(aid, tag_val, f_tipo.value, f_mod.value, f_ip.value, f_tcon.value, f_tloc.value, f_tdst.value, maq_val, tab_val)
                view_machine_boards(aid, anom, maq_val)

        titulo_form = f"Editar {init_tag}" if did else f"Nuevo Equipo en {anom}"
        def volver_fn(e=None):
            if did: view_device(did, aid, anom, init_maq)
            elif default_maq: view_machine_boards(aid, anom, default_maq)
            else: view_area_machines(aid, anom)

        menu_panel.controls.extend([
            ft.Row(controls=[ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=18, on_click=volver_fn), ft.Text(titulo_form, size=15, weight=ft.FontWeight.BOLD)]),
            f_maq_tipo, f_maq_tag, f_tab_tag, f_tag, f_tipo, f_mod, f_ip, f_tcon, f_tloc, f_tdst,
            btn("Guardar Información", save_d, bg=ft.Colors.TEAL_700, ic=ft.Icons.SAVE),
            btn("Cancelar", volver_fn, bg=ft.Colors.GREY_800),
        ])
        page.update()

    def form_route(did, aid, anom, maq):
        menu_panel.controls.clear()
        f_proto = ft.TextField(label="Protocolo", dense=True)
        f_med = ft.TextField(label="Medio", dense=True)
        f_dst = ft.TextField(label="Conecta a", dense=True)
        f_sys = ft.TextField(label="Destino", dense=True)

        def save_r(e):
            add_route(did, f_proto.value, f_med.value, f_dst.value, f_sys.value)
            view_device(did, aid, anom, maq)

        menu_panel.controls.extend([
            ft.Row(controls=[ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=18, on_click=lambda _: view_device(did, aid, anom, maq)), ft.Text("Nuevo Enlace de Red", size=15, weight=ft.FontWeight.BOLD)]),
            f_proto, f_med, f_dst, f_sys,
            btn("Guardar Enlace", save_r, bg=ft.Colors.TEAL_700, ic=ft.Icons.SAVE),
            btn("Cancelar", lambda _: view_device(did, aid, anom, maq), bg=ft.Colors.GREY_800),
        ])
        page.update()

    ruta_fondo = obtener_ruta_fondo()
    imagen_esquema = ft.Image(src=ruta_fondo, fit="contain", opacity=0.92, expand=True)

    plano_con_pines = ft.Stack(controls=[imagen_esquema, markers_layer], expand=True)
    contenedor_zoom_plano.content = plano_con_pines

    panel_derecho_esquema = ft.Container(
        content=ft.Stack(controls=[contenedor_zoom_plano, ft.Container(top=10, right=10, content=panel_flotante_navegacion)], expand=True),
        expand=True, bgcolor="#05070a", border_radius=8, padding=6,
    )

    panel_izquierdo_menu = ft.Container(width=360, content=menu_panel, padding=6)
    layout_principal = ft.Row(controls=[panel_izquierdo_menu, ft.VerticalDivider(width=1, color="#21262d"), panel_derecho_esquema], expand=True, spacing=6)

    view_home()
    page.add(layout_principal)

if __name__ == "__main__":
    directorio_base = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
    port_num = int(os.environ.get("PORT", 8550))
    
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER, 
        port=port_num, 
        assets_dir=directorio_base,
        host="0.0.0.0"
    )