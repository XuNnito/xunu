// ==================== VARIABLES EN ESPAÑOL ====================
let idChatActual = null;
let chatsGuardados = {};
let historiaMensajesActual = [];
let procesando = false;

const CLAVE_ALMACENAMIENTO = 'chunusXIA_chats';
const CLAVE_CHAT_ACTIVO = 'chunusXIA_chatActual';

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function () {
    cargarChatsDelAlmacenamiento();
    crearNuevoChat();
    configurarEventos();
    autojustarAltura();
});

// ==================== GESTIÓN DE ALMACENAMIENTO LOCAL ====================
function cargarChatsDelAlmacenamiento() {
    try {
        const datosGuardados = localStorage.getItem(CLAVE_ALMACENAMIENTO);
        if (datosGuardados) {
            chatsGuardados = JSON.parse(datosGuardados);
        }

        const idActivo = localStorage.getItem(CLAVE_CHAT_ACTIVO);
        if (idActivo && chatsGuardados[idActivo]) {
            idChatActual = idActivo;
        }
    } catch (error) {
        console.error('Error al cargar chats:', error);
        chatsGuardados = {};
    }
}

function guardarChatsEnAlmacenamiento() {
    try {
        localStorage.setItem(CLAVE_ALMACENAMIENTO, JSON.stringify(chatsGuardados));
        localStorage.setItem(CLAVE_CHAT_ACTIVO, idChatActual);
    } catch (error) {
        console.error('Error al guardar chats:', error);
    }
}

function guardarChatActual() {
    if (idChatActual && chatsGuardados[idChatActual]) {
        chatsGuardados[idChatActual].historial = historiaMensajesActual;
        chatsGuardados[idChatActual].fechaActualizacion = new Date().toISOString();
        guardarChatsEnAlmacenamiento();
    }
}

// ==================== CREAR/CARGAR CHATS ====================
function crearNuevoChat() {
    const idNuevo = 'chat_' + Date.now();

    chatsGuardados[idNuevo] = {
        id: idNuevo,
        titulo: 'Nuevo Chat',
        historial: [],
        fechaCreacion: new Date().toISOString(),
        fechaActualizacion: new Date().toISOString()
    };

    idChatActual = idNuevo;
    historiaMensajesActual = [];

    guardarChatsEnAlmacenamiento();
    actualizarInterfazChat();
    actualizarListaChats();
}

function cargarChat(idChat) {
    if (!chatsGuardados[idChat]) return;

    // Guardar el chat actual antes de cambiar
    if (idChatActual) {
        guardarChatActual();
    }

    idChatActual = idChat;
    historiaMensajesActual = [...chatsGuardados[idChat].historial];

    guardarChatsEnAlmacenamiento();
    actualizarInterfazChat();
    actualizarListaChats();
}

function actualizarInterfazChat() {
    const chatActual = chatsGuardados[idChatActual];
    if (!chatActual) return;

    // Actualizar título
    document.getElementById('tituloChatActual').textContent = chatActual.titulo;

    // Mostrar/ocultar estado vacío
    const estadoVacio = document.getElementById('estadoVacio');
    if (historiaMensajesActual.length === 0) {
        estadoVacio.style.display = 'flex';
    } else {
        estadoVacio.style.display = 'none';
    }

    // Mostrar mensajes
    renderizarMensajes();
}

// ==================== RENDERIZAR MENSAJES ====================
function renderizarMensajes() {
    const contenedor = document.getElementById('contenedorMensajes');
    contenedor.innerHTML = '';

    historiaMensajesActual.forEach((mensaje, indice) => {
        const divMensaje = document.createElement('div');
        divMensaje.className = `mensaje ${mensaje.rol}`;

        const burbuja = document.createElement('div');
        burbuja.className = 'burbuja-mensaje';
        burbuja.innerHTML = mensaje.contenido;

        divMensaje.appendChild(burbuja);

        // Agregar botones de acción solo para mensajes del bot
        if (mensaje.rol === 'bot') {
            const acciones = document.createElement('div');
            acciones.className = 'acciones-mensaje';

            const btnCopiar = document.createElement('button');
            btnCopiar.className = 'btn-accion';
            btnCopiar.innerHTML = '<i class="fas fa-copy"></i> Copiar';
            btnCopiar.onclick = (e) => {
                e.preventDefault();
                copiarAlPortapapeles(mensaje.contenido);
            };

            acciones.appendChild(btnCopiar);
            divMensaje.appendChild(acciones);
        }

        contenedor.appendChild(divMensaje);
    });

    // Desplazar al final
    contenedor.scrollTop = contenedor.scrollHeight;
}

// ==================== ENVIAR MENSAJE ====================
async function enviarMensaje(evento) {
    evento.preventDefault();

    const campo = document.getElementById('campoMensaje');
    const textoMensaje = campo.value.trim();

    if (!textoMensaje) return;
    if (procesando) return; // evitar envíos simultáneos
    procesando = true;
    const btnEnviar = document.querySelector('.btn-enviar');
    if (btnEnviar) btnEnviar.disabled = true;

    // Limpiar campo
    campo.value = '';
    autojustarAltura();

    // Mostrar mensaje del usuario
    historiaMensajesActual.push({
        rol: 'usuario',
        contenido: textoMensaje,
        timestamp: new Date().toISOString()
    });

    renderizarMensajes();
    guardarChatActual();

    // Actualizar título si es primer mensaje
    if (historiaMensajesActual.length === 1) {
        const chatActual = chatsGuardados[idChatActual];
        chatActual.titulo = textoMensaje.substring(0, 50);
        if (textoMensaje.length > 50) chatActual.titulo += '...';
        guardarChatsEnAlmacenamiento();
        actualizarListaChats();
    }

    // Mostrar indicador de escritura (crear si no existe y añadir)
    // Dentro de enviarMensaje, reemplaza la parte del indicador:

    // Mostrar indicador de escritura con estilo mejorado
    let indicador = document.getElementById('indicadorEscritura');
    if (!indicador) {
        indicador = document.createElement('div');
        indicador.id = 'indicadorEscritura';
        indicador.className = 'indicador-escritura';
        indicador.innerHTML = `
        <div class="onda-loader">
            <span></span><span></span><span></span><span></span><span></span>
        </div>
        <span class="texto-loader">Xunu está pensando...</span>
    `;
    }
    if (!document.getElementById('contenedorMensajes').contains(indicador)) {
        indicador.style.display = 'flex';
        document.getElementById('contenedorMensajes').appendChild(indicador);
    } else {
        indicador.style.display = 'flex';
    }
    document.getElementById('contenedorMensajes').scrollTop = document.getElementById('contenedorMensajes').scrollHeight;

    // Obtener respuesta del bot
    try {
        const respuesta = await obtenerRespuestaDelBot(textoMensaje);

        // Agregar respuesta
        historiaMensajesActual.push({
            rol: 'bot',
            contenido: respuesta,
            timestamp: new Date().toISOString()
        });

        renderizarMensajes();
        guardarChatActual();
        // remover indicador del DOM si existe
        try { if (indicador && indicador.parentNode) indicador.parentNode.removeChild(indicador); } catch (e) { }
        procesando = false;
        if (btnEnviar) btnEnviar.disabled = false;
    } catch (error) {
        console.error('Error:', error);
        historiaMensajesActual.push({
            rol: 'bot',
            contenido: '❌ Error al obtener respuesta. Por favor, intenta de nuevo.',
            timestamp: new Date().toISOString()
        });
        renderizarMensajes();
        guardarChatActual();
        // remover indicador
        try { if (indicador && indicador.parentNode) indicador.parentNode.removeChild(indicador); } catch (e) { }
        procesando = false;
        if (btnEnviar) btnEnviar.disabled = false;
    }
}

// ==================== CONECTAR CON GROQ ====================
async function obtenerRespuestaDelBot(textoUsuario) {
    try {
        // Construir contexto del historial
        const contextHist = historiaMensajesActual.slice(0, -1).map(m => ({
            role: m.rol === 'usuario' ? 'user' : 'assistant',
            content: m.contenido.replace(/<[^>]*>/g, '')  // Remover HTML
        })).slice(-10);  // Últimos 10 mensajes

        const respuesta = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mensaje: textoUsuario,
                email: 'usuario_local',
                session_id: idChatActual,
                contexto: contextHist
            })
        });

        if (!respuesta.ok) {
            throw new Error(`Error HTTP: ${respuesta.status}`);
        }

        const datos = await respuesta.json();

        if (!datos || !datos.success) {
            const msg = (datos && datos.message) ? datos.message : 'Respuesta inválida del servidor';
            throw new Error(msg);
        }

        // Asegurar que usamos el sessionId retornado por el servidor
        if (datos.sessionId && datos.sessionId !== idChatActual) {
            idChatActual = datos.sessionId;
            // si no existe en local, crear estructura mínima
            if (!chatsGuardados[idChatActual]) {
                chatsGuardados[idChatActual] = {
                    id: idChatActual,
                    titulo: 'Chat (sin título)',
                    historial: historiaMensajesActual || [],
                    fechaCreacion: new Date().toISOString(),
                    fechaActualizacion: new Date().toISOString()
                };
            }
            // sincronizar historial local con la sesión (si existe)
            historiaMensajesActual = chatsGuardados[idChatActual].historial || [];
            guardarChatsEnAlmacenamiento();
            actualizarListaChats();
        }

        return datos.bot_response;
    } catch (error) {
        console.error('Error al conectar con Groq:', error);
        throw error;
    }
}

// ==================== ACTUALIZAR LISTA DE CHATS ====================
function actualizarListaChats() {
    const lista = document.getElementById('listaChats');
    lista.innerHTML = '';

    // Ordenar por fecha de actualización (más recientes primero)
    const chatsOrdenados = Object.values(chatsGuardados).sort((a, b) => {
        return new Date(b.fechaActualizacion) - new Date(a.fechaActualizacion);
    });

    chatsOrdenados.forEach(chat => {
        const item = document.createElement('div');
        item.className = `item-chat ${chat.id === idChatActual ? 'activo' : ''}`;
        item.onclick = () => cargarChat(chat.id);

        const nombre = document.createElement('div');
        nombre.className = 'nombre';
        nombre.textContent = chat.titulo;
        item.appendChild(nombre);

        const accion = document.createElement('button');
        accion.className = 'accion';
        accion.innerHTML = '<i class="fas fa-trash"></i>';
        accion.onclick = (e) => {
            e.stopPropagation();
            eliminarChat(chat.id);
        };
        item.appendChild(accion);

        lista.appendChild(item);
    });
}

// ==================== ELIMINAR CHAT ====================
function eliminarChat(idChat) {
    if (confirm('¿Eliminar este chat?')) {
        delete chatsGuardados[idChat];

        if (idChatActual === idChat) {
            // Si eliminamos el chat actual, crear uno nuevo
            crearNuevoChat();
        }

        guardarChatsEnAlmacenamiento();
        actualizarListaChats();
    }
}

// ==================== RENOMBRAR CHAT ====================
function renombrarChatActual() {
    const chatActual = chatsGuardados[idChatActual];
    if (!chatActual) return;

    const nuevoTitulo = prompt('Nuevo nombre del chat:', chatActual.titulo);

    if (nuevoTitulo && nuevoTitulo.trim()) {
        chatActual.titulo = nuevoTitulo.trim();
        guardarChatsEnAlmacenamiento();
        actualizarInterfazChat();
        actualizarListaChats();
    }
}

// ==================== DESCARGAR CHAT ====================
function descargarChat() {
    const chatActual = chatsGuardados[idChatActual];
    if (!chatActual || historiaMensajesActual.length === 0) {
        alert('No hay nada que descargar');
        return;
    }

    let contenido = `Conversación: ${chatActual.titulo}\n`;
    contenido += `Fecha: ${new Date(chatActual.fechaActualizacion).toLocaleString('es-MX')}\n`;
    contenido += `${'='.repeat(50)}\n\n`;

    historiaMensajesActual.forEach(msg => {
        const rol = msg.rol === 'usuario' ? '👤 Tú' : '🤖 Xunu';
        const textoLimpio = msg.contenido.replace(/<[^>]*>/g, '');
        contenido += `${rol}:\n${textoLimpio}\n\n`;
    });

    // Descargar como archivo
    const blob = new Blob([contenido], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = `${chatActual.titulo.replace(/[^a-z0-9]/gi, '_')}.txt`;
    document.body.appendChild(enlace);
    enlace.click();
    document.body.removeChild(enlace);
    window.URL.revokeObjectURL(url);

    cerrarModal();
}

// ==================== LIMPIAR TODO ====================
function confirmarLimpiarTodo() {
    document.getElementById('modalConfirmacion').style.display = 'flex';
}

function limpiarTodoConfirmado() {
    if (confirm('⚠️ Esto eliminará TODO el historial de chats. ¿Estás seguro?')) {
        chatsGuardados = {};
        historiaMensajesActual = [];
        localStorage.removeItem(CLAVE_ALMACENAMIENTO);
        localStorage.removeItem(CLAVE_CHAT_ACTIVO);

        crearNuevoChat();
        cerrarModal();
    }
}

// ==================== UTILIDADES ====================
function mostrarOpciones() {
    document.getElementById('modalOpciones').style.display = 'flex';
}

function cerrarModal() {
    document.getElementById('modalConfirmacion').style.display = 'none';
    document.getElementById('modalOpciones').style.display = 'none';
}

function insertarEjemplo(texto) {
    document.getElementById('campoMensaje').value = texto;
    document.getElementById('campoMensaje').focus();
    autojustarAltura();
}

function copiarAlPortapapeles(texto) {
    const textoLimpio = texto.replace(/<[^>]*>/g, '');

    if (navigator.clipboard) {
        navigator.clipboard.writeText(textoLimpio).then(() => {
            alert('¡Copiado al portapapeles!');
        });
    } else {
        const area = document.createElement('textarea');
        area.value = textoLimpio;
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        document.body.removeChild(area);
        alert('¡Copiado al portapapeles!');
    }
}

function autojustarAltura() {
    const campo = document.getElementById('campoMensaje');
    campo.style.height = 'auto';
    campo.style.height = Math.min(campo.scrollHeight, 150) + 'px';
}

function configurarEventos() {
    const campo = document.getElementById('campoMensaje');

    // Auto-ajustar altura
    campo.addEventListener('input', autojustarAltura);

    // Enter para enviar, Shift+Enter para nueva línea
    campo.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.getElementById('formularioChat').dispatchEvent(new Event('submit'));
        }
    });

    // Cerrar modal al hacer clic fuera
    document.addEventListener('click', (e) => {
        const modal1 = document.getElementById('modalConfirmacion');
        const modal2 = document.getElementById('modalOpciones');

        if (e.target === modal1) cerrarModal();
        if (e.target === modal2) cerrarModal();
    });
}

// Auto-cargar la interfaz al refrescar
window.addEventListener('beforeunload', () => {
    guardarChatActual();
});
