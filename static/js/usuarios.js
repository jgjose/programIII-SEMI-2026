const $ = id => document.getElementById(id);
const URL_CRUD = "/crud_usuarios_usss7625";   

async function enviar(datos) {
  const r = await fetch(URL_CRUD, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(datos)
  });
  return r.json();
}

function limpiar() {
  $("frmUsuarios").reset();
  $("idUsuario").value = "";
  $("notaClave").textContent = "";
  $("clave").required = true;
}


$("frmUsuarios").addEventListener("submit", async e => {
  e.preventDefault();
  const id = $("idUsuario").value;
  const d = await enviar({
    accion: id ? "modificar" : "nuevo",
    idUsuario: id,
    usuario: $("usuario").value,
    clave: $("clave").value,
    nombre: $("nombre").value,
    direccion: $("direccion").value,
    telefono: $("telefono").value
  });
  alert(d.msg);
  if (d.ok) { limpiar(); buscar(); }
});


async function buscar() {
  const d = await enviar({accion: "buscar", valor: $("txtBuscar").value});
  const tb = $("tbody");
  tb.innerHTML = "";
  (d.datos || []).forEach(u => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${u.idUsuario}</td><td>${u.usuario}</td><td>${u.nombre}</td>
      <td>${u.direccion}</td><td>${u.telefono}</td>
      <td><button class="btn btn-sm btn-warning me-1">Editar</button>
          <button class="btn btn-sm btn-danger">Eliminar</button></td>`;
    const [bEditar, bEliminar] = tr.querySelectorAll("button");
    bEditar.onclick = () => editar(u);
    bEliminar.onclick = () => eliminar(u);
    tb.appendChild(tr);
  });
}
$("txtBuscar").addEventListener("keyup", buscar);


function editar(u) {
  $("idUsuario").value = u.idUsuario;
  $("usuario").value = u.usuario;
  $("clave").value = "";
  $("clave").required = false;
  $("notaClave").textContent = "(vacío = no cambiar)";
  $("nombre").value = u.nombre;
  $("direccion").value = u.direccion;
  $("telefono").value = u.telefono;
  window.scrollTo(0, 0);
}


async function eliminar(u) {
  if (!confirm(`¿Eliminar al usuario ${u.usuario}?`)) return;
  const d = await enviar({accion: "eliminar", idUsuario: u.idUsuario});
  alert(d.msg);
  buscar();
}

$("btnLimpiar").addEventListener("click", limpiar);
limpiar();
buscar();
