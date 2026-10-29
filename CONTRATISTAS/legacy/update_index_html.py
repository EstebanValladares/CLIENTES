import os

index_path = 'vue/index.html'
with open(index_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Header action buttons
header_target = '''        <button @click="cargarProveedores" 
                class="p-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-slate-300 hover:text-white transition cursor-pointer" 
                title="Actualizar Proveedores">
          <i class="fa-solid fa-rotate"></i>
        </button>
      </div>'''

header_contratistas = '''        <button @click="cargarProveedores" 
                class="p-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-slate-300 hover:text-white transition cursor-pointer" 
                title="Actualizar Proveedores">
          <i class="fa-solid fa-rotate"></i>
        </button>
      </div>

      <!-- BOTONES DE ACCIÓN PARA LA VISTA CONTRATISTAS -->
      <div v-else-if="vistaActiva === 'CONTRATISTAS'" class="flex items-center gap-2.5 w-full lg:w-auto flex-wrap">
        <button @click="iniciarProcesamientoContratistas" 
                :disabled="ejecutandoContratistas || colaContratistas.length === 0"
                class="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold flex items-center gap-2 shadow-lg shadow-emerald-600/25 transition cursor-pointer">
          <i v-if="ejecutandoContratistas" class="fa-solid fa-circle-notch fa-spin"></i>
          <i v-else class="fa-solid fa-play"></i>
          <span>{{ ejecutandoContratistas ? 'Procesando en Aryve...' : 'Iniciar Proceso (' + colaContratistas.length + ')' }}</span>
        </button>

        <button @click="detenerProcesamientoContratistas" 
                :disabled="!ejecutandoContratistas"
                class="bg-rose-600 hover:bg-rose-500 disabled:bg-slate-800 disabled:text-slate-600 text-white px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold flex items-center gap-2 shadow-lg shadow-rose-600/25 transition cursor-pointer">
          <i class="fa-solid fa-stop"></i>
          <span>Detener</span>
        </button>

        <button @click="cargarContratistas(true)" 
                class="p-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-slate-300 hover:text-white transition cursor-pointer" 
                title="Actualizar DBA (Enkontrol)">
          <i class="fa-solid fa-rotate" :class="{'fa-spin': cargandoContratistas}"></i>
        </button>
      </div>'''

if header_target in html and 'vistaActiva === \'CONTRATISTAS\'' not in html:
    html = html.replace(header_target, header_contratistas)
    print('1. Header actions agregados')

# 2. Navigation Tab
nav_target = '''        <span v-else class="ml-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-white/20 text-white">
          {{ proveedoresRegistrados.length }}
        </span>
      </button>
    </nav>'''

nav_contratistas = '''        <span v-else class="ml-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-white/20 text-white">
          {{ proveedoresRegistrados.length }}
        </span>
      </button>

      <button @click="cambiarVista('CONTRATISTAS')" 
              class="px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2.5 transition cursor-pointer"
              :class="vistaActiva === 'CONTRATISTAS' 
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30' 
                : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700/60'">
        <i class="fa-solid fa-id-badge"></i>
        <span>CONTRATISTAS</span>
        <span v-if="colaContratistas.length > 0" class="ml-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-400/20 text-amber-300 border border-amber-400/30">
          {{ colaContratistas.length }} en fila
        </span>
        <span v-else class="ml-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-white/20 text-white">
          {{ contratistasDB.length }} en DBA
        </span>
      </button>
    </nav>'''

if nav_target in html and 'cambiarVista(\'CONTRATISTAS\')' not in html:
    html = html.replace(nav_target, nav_contratistas)
    print('2. Pestaña de navegación agregada')

# 3. Vista Principal de Contratistas
view_target = '''        </div>

      </div>

    </div>

    <!-- ======================================================== -->
    <!-- MODAL 1: ALTA DE USUARIO (CREDENCIAL DIGITAL EJECUTIVA)  -->'''

view_contratistas = '''        </div>

      </div>

    </div>

    <!-- ======================================================== -->
    <!-- VISTA 4: CONTRATISTAS (DBA ENKONTROL VS EN FILA + RPA)   -->
    <!-- ======================================================== -->
    <div v-show="vistaActiva === 'CONTRATISTAS'" class="flex flex-col flex-1">
      
      <!-- SUB-HEADER DE CONTRATISTAS -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6">
        <div>
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-id-badge text-indigo-400"></i>
            <span>Módulo de Contratistas • Sincronización DBA & Aryve</span>
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">
            Compara en tiempo real los registros de DBA (<code class="text-indigo-300 font-mono">DBA.SU_CONTRATISTAS</code>) contra <code class="text-indigo-300 font-mono">contratista_mapeado.json</code>, encola pendientes y automatiza sus fotos en Aryve.
          </p>
        </div>

        <div class="flex items-center gap-2 flex-wrap">
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-slate-800 border border-slate-700 text-slate-300">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            DBA Conectado (EK_ADM01_11)
          </span>
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
            <i class="fa-solid fa-layer-group text-xs"></i>
            {{ contratistasDB.length }} en BD
          </span>
        </div>
      </div>

      <!-- GRID DE LAS 2 TABLAS (CONTRATISTAS VS EN FILA) -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        
        <!-- ==================================================== -->
        <!-- TABLA IZQUIERDA: CONTRATISTAS (DBA ENKONTROL)        -->
        <!-- ==================================================== -->
        <div class="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          
          <div>
            <!-- Header de la Tarjeta Izquierda -->
            <div class="flex items-center justify-between pb-3 mb-3 border-b border-slate-700/80 flex-wrap gap-2">
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                  <i class="fa-solid fa-hard-hat text-sm"></i>
                </div>
                <div>
                  <h3 class="text-sm font-bold text-white tracking-wide uppercase">Contratistas (DBA)</h3>
                  <p class="text-[11px] text-slate-400">{{ contratistasFiltrados.length }} mostrados de {{ contratistasDB.length }}</p>
                </div>
              </div>

              <!-- Acciones Rápidas -->
              <div class="flex items-center gap-2">
                <button @click="seleccionarTodosSinMapear"
                        class="text-xs bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 px-3 py-1.5 rounded-lg transition font-medium flex items-center gap-1.5 cursor-pointer"
                        title="Seleccionar todos los que no tienen foto o no están mapeados">
                  <i class="fa-solid fa-check-double text-[11px]"></i>
                  <span>Marcar Pendientes</span>
                </button>

                <button @click="cargarContratistas(true)"
                        class="p-2 bg-slate-900 hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-300 hover:text-white transition cursor-pointer"
                        title="Refrescar DBA">
                  <i class="fa-solid fa-rotate text-xs" :class="{'fa-spin': cargandoContratistas}"></i>
                </button>
              </div>
            </div>

            <!-- Filtros de Búsqueda y Estatus -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mb-3">
              <div class="sm:col-span-2 relative">
                <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-slate-500 text-xs"></i>
                <input type="text"
                       v-model="busquedaContratistas"
                       placeholder="Buscar por Clave, Nombre, RFC..."
                       class="w-full bg-slate-900 border border-slate-700 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-sans">
              </div>

              <div>
                <select v-model="filtroEstatusContratistas"
                        class="w-full bg-slate-900 border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer">
                  <option value="TODOS">Todos ({{ contratistasDB.length }})</option>
                  <option value="SIN_MAPEADO">Sin Mapear</option>
                  <option value="SIN_FOTO">Sin Foto</option>
                  <option value="COMPLETO">Con Foto</option>
                </select>
              </div>
            </div>

            <!-- Contenedor con Scroll Doble (Horizontal y Vertical) -->
            <div class="overflow-x-auto overflow-y-auto max-h-[460px] custom-scrollbar border border-slate-700/80 rounded-xl bg-slate-950">
              <table class="w-full text-left text-xs text-slate-300 whitespace-nowrap">
                <thead class="bg-slate-900/90 text-slate-400 sticky top-0 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold z-10">
                  <tr>
                    <th class="py-2.5 px-3 text-center w-10">
                      <span title="Seleccionar">Sel</span>
                    </th>
                    <th class="py-2.5 px-3">Clave</th>
                    <th class="py-2.5 px-3">Nombre / Razón Social</th>
                    <th class="py-2.5 px-3">RFC</th>
                    <th class="py-2.5 px-3">Estatus</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60 font-sans">
                  <tr v-for="c in contratistasFiltrados" :key="'c-dba-' + c.numpro"
                      class="hover:bg-slate-900/60 transition cursor-pointer"
                      :class="{'bg-indigo-950/20': estaEnFila(c.numpro)}"
                      @click="toggleContratistaFila(c)">
                    
                    <!-- Checkbox de Selección -->
                    <td class="py-2.5 px-3 text-center" @click.stop>
                      <input type="checkbox"
                             :checked="estaEnFila(c.numpro)"
                             @change="toggleContratistaFila(c)"
                             class="w-4 h-4 rounded border-slate-600 text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                    </td>

                    <!-- Clave (numpro) -->
                    <td class="py-2.5 px-3 font-mono font-bold text-slate-200">
                      {{ c.numpro }}
                    </td>

                    <!-- Nombre -->
                    <td class="py-2.5 px-3 font-medium text-slate-100 max-w-xs truncate" :title="c.nombre">
                      {{ c.nombre }}
                    </td>

                    <!-- RFC -->
                    <td class="py-2.5 px-3 font-mono text-slate-400">
                      {{ c.rfc || '-' }}
                    </td>

                    <!-- Estatus / Comparación con JSON -->
                    <td class="py-2.5 px-3">
                      <span v-if="!c.en_json"
                            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        <i class="fa-solid fa-circle-exclamation text-[9px]"></i>
                        Sin Mapear
                      </span>
                      <span v-else-if="!c.tiene_foto"
                            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                        <i class="fa-solid fa-image text-[9px]"></i>
                        Sin Foto
                      </span>
                      <span v-else
                            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <i class="fa-solid fa-check text-[9px]"></i>
                        Con Foto
                      </span>
                    </td>

                  </tr>

                  <tr v-if="contratistasFiltrados.length === 0">
                    <td colspan="5" class="py-8 text-center text-slate-500 text-xs">
                      <i class="fa-solid fa-inbox text-xl block mb-2 opacity-50"></i>
                      No se encontraron contratistas con los filtros especificados.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

          </div>

          <div class="pt-3 text-[11px] text-slate-500 flex justify-between items-center">
            <span>Haz clic en cualquier fila o marca su casilla para agregarla a <strong>EN FILA</strong>.</span>
            <span class="font-mono">{{ contratistasDB.length }} registros cargados</span>
          </div>

        </div>


        <!-- ==================================================== -->
        <!-- TABLA DERECHA: EN FILA (SELECCIONADOS)               -->
        <!-- ==================================================== -->
        <div class="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          
          <div>
            <!-- Header de la Tarjeta Derecha -->
            <div class="flex items-center justify-between pb-3 mb-3 border-b border-slate-700/80 flex-wrap gap-2">
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <i class="fa-solid fa-list-check text-sm"></i>
                </div>
                <div>
                  <h3 class="text-sm font-bold text-white tracking-wide uppercase">En Fila</h3>
                  <p class="text-[11px] text-slate-400">Contratistas seleccionados listos para procesar</p>
                </div>
              </div>

              <!-- Acciones de Cola -->
              <div class="flex items-center gap-2">
                <span class="px-2.5 py-1 rounded-full text-xs font-extrabold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
                  {{ colaContratistas.length }} en fila
                </span>

                <button v-if="colaContratistas.length > 0"
                        @click="vaciarFila"
                        class="text-xs bg-slate-900 hover:bg-rose-500/20 border border-slate-700 hover:border-rose-500/30 text-slate-400 hover:text-rose-400 px-3 py-1.5 rounded-lg transition font-medium flex items-center gap-1.5 cursor-pointer">
                  <i class="fa-solid fa-trash-can text-[11px]"></i>
                  <span>Vaciar</span>
                </button>
              </div>
            </div>

            <!-- Contenedor con Scroll de la Cola -->
            <div class="overflow-x-auto overflow-y-auto max-h-[460px] custom-scrollbar border border-slate-700/80 rounded-xl bg-slate-950">
              <table class="w-full text-left text-xs text-slate-300 whitespace-nowrap">
                <thead class="bg-slate-900/90 text-slate-400 sticky top-0 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold z-10">
                  <tr>
                    <th class="py-2.5 px-3 w-8 text-center">#</th>
                    <th class="py-2.5 px-3">Clave</th>
                    <th class="py-2.5 px-3">Nombre</th>
                    <th class="py-2.5 px-3 text-center">ID Aryve</th>
                    <th class="py-2.5 px-3 text-center w-12">Acción</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60 font-sans">
                  <tr v-for="(item, idx) in colaContratistas" :key="'fila-' + item.numpro"
                      class="hover:bg-slate-900/50 transition">
                    
                    <td class="py-2.5 px-3 text-center font-mono text-slate-500 text-[11px]">
                      {{ idx + 1 }}
                    </td>

                    <td class="py-2.5 px-3 font-mono font-bold text-slate-200">
                      {{ item.numpro }}
                    </td>

                    <td class="py-2.5 px-3 font-medium text-slate-100 max-w-xs truncate" :title="item.nombre">
                      {{ item.nombre }}
                    </td>

                    <td class="py-2.5 px-3 text-center font-mono text-indigo-400 font-bold">
                      <span v-if="item.id_aryve">#{{ item.id_aryve }}</span>
                      <span v-else class="text-slate-500 text-[11px]">Auto (Clave)</span>
                    </td>

                    <td class="py-2.5 px-3 text-center">
                      <button @click="quitarDeFila(item.numpro)"
                              class="text-slate-500 hover:text-rose-400 transition p-1 cursor-pointer"
                              title="Quitar de la fila">
                        <i class="fa-solid fa-xmark text-sm"></i>
                      </button>
                    </td>

                  </tr>

                  <tr v-if="colaContratistas.length === 0">
                    <td colspan="5" class="py-12 text-center text-slate-500 text-xs">
                      <i class="fa-solid fa-arrow-left text-2xl block mb-2 opacity-40 animate-pulse"></i>
                      <span>No hay contratistas en fila.</span>
                      <p class="text-[11px] text-slate-600 mt-1">Marca las casillas en la tabla de la izquierda para encolar.</p>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

          </div>

          <div class="pt-3 text-[11px] text-slate-500 flex justify-between items-center">
            <span>Al iniciar, el bot procesará esta lista en orden y eliminará los gafetes al terminar.</span>
            <span class="font-mono text-emerald-400 font-bold">{{ colaContratistas.length }} pendientes</span>
          </div>

        </div>

      </div>


      <!-- ==================================================== -->
      <!-- BARRA DE ACCIÓN: BOTONES INICIAR Y DETENER          -->
      <!-- ==================================================== -->
      <div class="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-4 shadow-lg mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-center text-indigo-400 text-lg shadow-inner">
            <i class="fa-solid fa-robot"></i>
          </div>
          <div>
            <h4 class="text-sm font-bold text-white">Centro de Control de Automatización</h4>
            <p class="text-xs text-slate-400">Genera gafetes 762x686 px, los sube al perfil de Aryve y purga el disco.</p>
          </div>
        </div>

        <div class="flex items-center gap-3 w-full sm:w-auto">
          <!-- BOTÓN DETENER -->
          <button @click="detenerProcesamientoContratistas"
                  :disabled="!ejecutandoContratistas"
                  class="flex-1 sm:flex-initial bg-rose-600 hover:bg-rose-500 disabled:bg-slate-800 disabled:text-slate-600 text-white px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-rose-600/20 transition cursor-pointer">
            <i class="fa-solid fa-stop"></i>
            <span>Detener</span>
          </button>

          <!-- BOTÓN INICIAR -->
          <button @click="iniciarProcesamientoContratistas"
                  :disabled="ejecutandoContratistas || colaContratistas.length === 0"
                  class="flex-1 sm:flex-initial bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white px-6 py-2.5 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2.5 shadow-lg shadow-emerald-600/30 transition cursor-pointer">
            <i v-if="ejecutandoContratistas" class="fa-solid fa-circle-notch fa-spin text-sm"></i>
            <i v-else class="fa-solid fa-play text-sm"></i>
            <span>{{ ejecutandoContratistas ? 'Procesando en Aryve...' : 'Iniciar Proceso' }}</span>
          </button>
        </div>

      </div>


      <!-- ==================================================== -->
      <!-- CONSOLA / TERMINAL EN VIVO ABAJO                    -->
      <!-- ==================================================== -->
      <div class="bg-slate-900/90 border border-slate-700/80 rounded-2xl p-5 shadow-2xl flex flex-col">
        
        <div class="flex items-center justify-between pb-3 mb-3 border-b border-slate-800 flex-wrap gap-2">
          <div class="flex items-center gap-3">
            <!-- Puntos luminosos tipo terminal -->
            <div class="flex items-center gap-1.5">
              <span class="w-3 h-3 rounded-full bg-rose-500/80"></span>
              <span class="w-3 h-3 rounded-full bg-amber-500/80"></span>
              <span class="w-3 h-3 rounded-full bg-emerald-500/80"></span>
            </div>
            <h4 class="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <span class="w-2 h-2 rounded-full" :class="ejecutandoContratistas ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'"></span>
              <span>Consola de Ejecución en Vivo • RPA Selenium & Gafetes</span>
            </h4>
          </div>

          <div class="flex items-center gap-3">
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400">
              {{ ejecutandoContratistas ? 'STATUS: EJECUTANDO' : 'STATUS: LISTO' }}
            </span>
            <button @click="limpiarTerminalContratistas"
                    class="text-[11px] text-slate-400 hover:text-white transition flex items-center gap-1 cursor-pointer">
              <i class="fa-solid fa-broom"></i>
              <span>Limpiar</span>
            </button>
          </div>
        </div>

        <pre id="terminal-contratistas" 
             class="h-56 max-h-56 bg-slate-950 border border-slate-800/90 rounded-xl p-4 font-mono text-xs text-emerald-400 overflow-y-auto custom-scrollbar leading-relaxed whitespace-pre-wrap select-text shadow-inner">{{ terminalContratistasContenido }}</pre>

      </div>

    </div>

    <!-- ======================================================== -->
    <!-- MODAL 1: ALTA DE USUARIO (CREDENCIAL DIGITAL EJECUTIVA)  -->'''

if view_target in html and 'vistaActiva === \'CONTRATISTAS\'' not in html:
    html = html.replace(view_target, view_contratistas)
    print('3. Vista Contratistas agregada')

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('vue/index.html actualizado correctamente!')

