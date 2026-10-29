"""Grafo de conocimiento del ecosistema VELAS (sin dependencias externas).

Se CONSTRUYE SOLO analizando el código (AST) de cada proyecto:

    Nodos : proyecto · archivo · dato (csv/json/txt) · portal (módulo de Aryve) · ui (ID de selector)
    Aristas: contiene · importa · usa_dato · visita · usa_selector · referencia

Para qué sirve:
  * impacto:   "si cambia/falla ESTE componente de Aryve, ¿qué proyectos se rompen?"
  * calientes: componentes que más fallan (memoria acumulada de la telemetría)
  * compartidos: acoplamientos entre proyectos (selectores/datos/módulos usados por varios)

CLI:
    python -m NUCLEO.grafo construir
    python -m NUCLEO.grafo impacto select2-formControl_Grupo-container
    python -m NUCLEO.grafo compartidos
    python -m NUCLEO.grafo calientes
    python -m NUCLEO.grafo mermaid
"""
import ast
import datetime
import json
import os
import re
import sys
from collections import defaultdict

from NUCLEO import config

RAIZ = config.RAIZ
RUTA_GRAFO = os.path.join(config.NUCLEO_DIR, "grafo.json")
RUTA_MERMAID = os.path.join(config.NUCLEO_DIR, "grafo.mmd")
RUTA_FALLOS = os.path.join(config.NUCLEO_DIR, "estado_fallos.json")

IGNORAR_DIRS = {"NUCLEO", "__pycache__", ".git", ".venv", "venv", "node_modules"}
RX_DATO = re.compile(r"^[\w\-. /\\]+\.(csv|json|txt)$", re.IGNORECASE)
RX_ID = re.compile(r"^[A-Za-z][\w\-:.]{2,}$")
RX_URL = re.compile(r"https?://[^\s'\"]+")


# ------------------------------------------------------------------ construcción
def _proyectos():
    out = []
    for nombre in sorted(os.listdir(RAIZ)):
        ruta = os.path.join(RAIZ, nombre)
        if not os.path.isdir(ruta) or nombre.startswith(".") or nombre in IGNORAR_DIRS:
            continue
        if any(f.endswith(".py") for f in os.listdir(ruta)):
            out.append(nombre)
    return out


def _normalizar_portal(url):
    """https://host/Aryve/#/kontrol/usuarios/id?nuevo -> portal:kontrol/usuarios"""
    if "#" in url:
        ruta = url.split("#", 1)[1].lstrip("/")
    else:
        ruta = "(raiz)"
    ruta = ruta.split("?")[0]
    partes = [p for p in ruta.split("/") if p and p.lower() != "id" and not p.isdigit()]
    return "portal:" + ("/".join(partes) or "(raiz)")


class _Visitante(ast.NodeVisitor):
    def __init__(self):
        self.imports, self.cadenas, self.ids_by, self.valores_dict = set(), set(), set(), set()

    def visit_Import(self, n):
        for a in n.names:
            self.imports.add(a.name)

    def visit_ImportFrom(self, n):
        if n.module:
            self.imports.add(n.module)

    def visit_Dict(self, n):
        # En selectores.py las LLAVES son nombres de Python; los VALORES son los IDs del DOM.
        for val in n.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                self.valores_dict.add(val.value)
        self.generic_visit(n)

    def visit_Constant(self, n):
        if isinstance(n.value, str) and 0 < len(n.value) < 400:
            self.cadenas.add(n.value)

    def visit_Call(self, n):
        # find_element(By.ID, "x") / EC.xxx((By.ID, "x"))
        for arg in list(n.args):
            tup = arg.elts if isinstance(arg, ast.Tuple) else n.args
            for i, e in enumerate(tup[:-1]):
                if isinstance(e, ast.Attribute) and e.attr == "ID":
                    sig = tup[i + 1]
                    if isinstance(sig, ast.Constant) and isinstance(sig.value, str):
                        self.ids_by.add(sig.value)
        self.generic_visit(n)


def construir(guardar=True):
    nodos, aristas = {}, set()
    proyectos = _proyectos()

    def nodo(id_, tipo, **extra):
        nodos.setdefault(id_, {"tipo": tipo, **extra})
        return id_

    def arista(a, b, rel):
        aristas.add((a, b, rel))

    modulos_locales = {}  # (proyecto, modulo) -> id archivo
    for p in proyectos:
        nodo(f"proyecto:{p}", "proyecto")
        for f in os.listdir(os.path.join(RAIZ, p)):
            if f.endswith(".py"):
                modulos_locales[(p, f[:-3])] = f"archivo:{p}/{f}"

    for p in proyectos:
        dir_p = os.path.join(RAIZ, p)
        for f in sorted(os.listdir(dir_p)):
            if not f.endswith(".py"):
                continue
            id_arch = nodo(f"archivo:{p}/{f}", "archivo", proyecto=p)
            arista(f"proyecto:{p}", id_arch, "contiene")
            try:
                with open(os.path.join(dir_p, f), "r", encoding="utf-8", errors="replace") as fh:
                    arbol = ast.parse(fh.read())
            except SyntaxError:
                continue
            v = _Visitante()
            v.visit(arbol)

            # imports locales y entre proyectos
            for imp in v.imports:
                raiz_imp = imp.split(".")[0]
                if (p, raiz_imp) in modulos_locales and raiz_imp != f[:-3]:
                    arista(id_arch, modulos_locales[(p, raiz_imp)], "importa")
                elif raiz_imp in proyectos and raiz_imp != p:
                    sub = imp.split(".")[1] if "." in imp else None
                    destino = modulos_locales.get((raiz_imp, sub)) if sub else None
                    arista(id_arch, destino or f"proyecto:{raiz_imp}", "importa")

            for s in v.cadenas:
                # URLs del portal
                for url in RX_URL.findall(s):
                    if "aryve" in url.lower():
                        arista(id_arch, nodo(_normalizar_portal(url), "portal"), "visita")
                # archivos de datos
                if RX_DATO.match(s.strip()) and " " not in s.strip():
                    limpio = s.strip().replace("\\", "/")
                    base = os.path.basename(limpio)
                    dueno = p
                    for otro in proyectos:
                        if f"/{otro}/" in f"/{limpio}" or limpio.startswith(otro + "/"):
                            dueno = otro
                    arista(id_arch, nodo(f"dato:{dueno}/{base}", "dato", proyecto=dueno), "usa_dato")
                # referencias a otras carpetas del ecosistema (existan o no)
                if s in proyectos and s != p:
                    arista(id_arch, f"proyecto:{s}", "referencia")
                elif re.fullmatch(r"[A-Z][A-Z0-9_]{5,}", s) and s not in proyectos and s not in IGNORAR_DIRS \
                        and f != "selectores.py" and "_" in s and not s.startswith(("SELECT", "XPATH")) \
                        and any(k in s for k in ("DATOS", "CONFIG", "JSON", "CREACION", "REVISION", "LLENADO", "CAPTURA")):
                    nodo(f"referencia_rota:{s}", "referencia_rota")
                    arista(id_arch, f"referencia_rota:{s}", "referencia")

            # selectores de UI
            ids = set(v.ids_by)
            if f == "selectores.py":
                ids |= {s for s in v.valores_dict if RX_ID.match(s) and not s.startswith(("//", ".//"))}
            for i in ids:
                arista(id_arch, nodo(f"ui:{i}", "ui"), "usa_selector")

    grafo = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "nodos": nodos,
        "aristas": sorted([{"de": a, "a": b, "rel": r} for a, b, r in aristas],
                          key=lambda e: (e["rel"], e["de"], e["a"])),
    }
    if guardar:
        with open(RUTA_GRAFO, "w", encoding="utf-8") as f:
            json.dump(grafo, f, indent=1, ensure_ascii=False)
        with open(RUTA_MERMAID, "w", encoding="utf-8") as f:
            f.write(a_mermaid(grafo))
    return grafo


# ------------------------------------------------------------------ consultas
def cargar(reconstruir=False):
    if reconstruir or not os.path.exists(RUTA_GRAFO):
        return construir()
    with open(RUTA_GRAFO, "r", encoding="utf-8") as f:
        return json.load(f)


def _proyecto_de(grafo, id_nodo):
    """Proyecto(s) dueños de un archivo, o el propio proyecto."""
    if id_nodo.startswith("proyecto:"):
        return id_nodo.split(":", 1)[1]
    return grafo["nodos"].get(id_nodo, {}).get("proyecto")


def proyectos_que_usan(grafo, id_nodo):
    """Recorre aristas en reversa hasta llegar a proyectos."""
    inversas = defaultdict(set)
    for e in grafo["aristas"]:
        inversas[e["a"]].add(e["de"])
    vistos, pila, resultado = set(), [id_nodo], set()
    while pila:
        actual = pila.pop()
        if actual in vistos:
            continue
        vistos.add(actual)
        pr = _proyecto_de(grafo, actual)
        if pr:
            resultado.add(pr)
        pila.extend(inversas.get(actual, ()))
    return sorted(resultado)


def impacto_de_componentes(componentes, excluir=None):
    grafo = cargar()
    out = []
    for c in componentes:
        candidatos = [c] if ":" in c and c.split(":")[0] in ("ui", "portal", "dato", "archivo") \
            else [f"ui:{c}", f"portal:{c}", f"dato:{c}"]
        for cand in candidatos:
            if cand in grafo["nodos"]:
                proy = [p for p in proyectos_que_usan(grafo, cand) if p != excluir]
                if proy:
                    out.append({"componente": c, "proyectos": proy})
                break
    return out


def compartidos(grafo=None):
    """Nodos usados por 2+ proyectos = puntos de acoplamiento."""
    grafo = grafo or cargar()
    filas = []
    for id_, n in grafo["nodos"].items():
        if n["tipo"] in ("ui", "portal", "dato"):
            ps = proyectos_que_usan(grafo, id_)
            if len(ps) > 1:
                filas.append((id_, ps))
    return sorted(filas, key=lambda x: (-len(x[1]), x[0]))


# ------------------------------------------------------------------ memoria de fallos
def registrar_fallos(proyecto, componentes):
    estado = {}
    if os.path.exists(RUTA_FALLOS):
        try:
            with open(RUTA_FALLOS, "r", encoding="utf-8") as f:
                estado = json.load(f)
        except Exception:
            estado = {}
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    for c in componentes:
        e = estado.setdefault(c, {"fallos": 0, "ultimo": None, "proyectos": {}})
        e["fallos"] += 1
        e["ultimo"] = ahora
        e["proyectos"][proyecto] = e["proyectos"].get(proyecto, 0) + 1
    with open(RUTA_FALLOS, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=1, ensure_ascii=False)


def calientes(top=10):
    if not os.path.exists(RUTA_FALLOS):
        return []
    with open(RUTA_FALLOS, "r", encoding="utf-8") as f:
        estado = json.load(f)
    return sorted(estado.items(), key=lambda kv: -kv[1]["fallos"])[:top]


# ------------------------------------------------------------------ exportación
def _mid(texto):
    return re.sub(r"\W", "_", texto)


def a_mermaid(grafo):
    """Vista de alto nivel: proyectos, módulos del portal, datos y acoplamientos."""
    L = ["flowchart LR"]
    proyectos = [i for i, n in grafo["nodos"].items() if n["tipo"] == "proyecto"]
    for p in proyectos:
        nombre_p = p.split(":", 1)[1]
        L.append(f'  {_mid(p)}["{nombre_p}"]')
    # proyecto -> portal / dato / otro proyecto
    vistos = set()
    for e in grafo["aristas"]:
        if e["rel"] not in ("visita", "usa_dato", "importa", "referencia"):
            continue
        origen = _proyecto_de(grafo, e["de"])
        if not origen:
            continue
        destino = e["a"]
        if destino.startswith("archivo:"):
            destino = f"proyecto:{grafo['nodos'][destino]['proyecto']}"
        if destino == f"proyecto:{origen}":
            continue
        clave = (origen, destino, e["rel"])
        if clave in vistos:
            continue
        vistos.add(clave)
        n = grafo["nodos"].get(destino, {})
        if n.get("tipo") == "portal":
            L.append(f'  {_mid(destino)}(("{destino[7:]}"))')
        elif n.get("tipo") == "dato":
            L.append(f'  {_mid(destino)}[("{destino[5:]}")]')
        elif n.get("tipo") == "referencia_rota":
            L.append(f'  {_mid(destino)}{{{{"⚠ {destino[16:]}"}}}}')
        flecha = "-.->" if e["rel"] == "referencia" else "-->"
        L.append(f"  {_mid('proyecto:' + origen)} {flecha}|{e['rel']}| {_mid(destino)}")
    return "\n".join(dict.fromkeys(L)) + "\n"


# ------------------------------------------------------------------ CLI
def _cli(argv):
    cmd = argv[1] if len(argv) > 1 else "construir"
    if cmd == "construir":
        g = construir()
        tipos = defaultdict(int)
        for n in g["nodos"].values():
            tipos[n["tipo"]] += 1
        print(f"Grafo construido: {dict(tipos)} · {len(g['aristas'])} aristas")
        print(f"  -> {RUTA_GRAFO}\n  -> {RUTA_MERMAID}")
        rotas = [i for i, n in g["nodos"].items() if n["tipo"] == "referencia_rota"]
        for r in rotas:
            quien = [e["de"] for e in g["aristas"] if e["a"] == r]
            print(f"  ⚠ Referencia a carpeta/archivo inexistente: {r[16:]}  (en {', '.join(quien)})")
    elif cmd == "impacto" and len(argv) > 2:
        g = cargar(reconstruir=True)
        obj = argv[2]
        cands = [obj] if ":" in obj else [f"ui:{obj}", f"portal:{obj}", f"dato:{obj}"]
        for c in cands:
            if c in g["nodos"]:
                print(f"Si falla/cambia '{c}' se afectan: {', '.join(proyectos_que_usan(g, c))}")
                return
        print(f"No encontré '{obj}' en el grafo.")
    elif cmd == "compartidos":
        for id_, ps in compartidos(cargar(reconstruir=True)):
            print(f"{len(ps)} proyectos · {id_}: {', '.join(ps)}")
    elif cmd == "calientes":
        filas = calientes()
        if not filas:
            print("Sin fallos registrados todavía.")
        for comp, d in filas:
            print(f"{d['fallos']:>3} fallos · {comp} · proyectos: {d['proyectos']} · último: {d['ultimo']}")
    elif cmd == "mermaid":
        print(a_mermaid(cargar(reconstruir=True)))
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    _cli(sys.argv)
