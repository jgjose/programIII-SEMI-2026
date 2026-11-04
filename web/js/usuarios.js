const $ = (id) => document.getElementById(id);
const campos = ["idUsuario", "usuario", "clave", "nombre", "direccion", "telefono"];

async function api(accion, datos) {
  const r = await fetch("/api/usuarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accion, datos }),
  });
  if (r.status === 401) { window.location.href = "/"; return { ok: false }; }
  return r.json();
}

function mostrar(msg, ok) {
  const m = $("mensaje");
  m.textContent = msg;
  m.className = "msg " + (ok ? "ok" : "error");
}

function limpiar() {
  campos.forEach((c) => ($(c).value = ""));
  $("titulo").textContent = "Registrar usuario";
  $("btnGuardar").textContent = "Guardar";
}

async function buscar() {
  const res = await api("buscar", { termino: $("termino").value });
  const tbody = $("tabla");
  tbody.innerHTML = "";
  if (!res.ok) return mostrar(res.msg || "Error al buscar.", false);
  res.datos.forEach((u) => {
    const tr = document.createElement("tr");
    [u.idUsuario, u.usuario, u.nombre, u.direccion, u.telefono].forEach((v) => {
      const td = document.createElement("td");
      td.textContent = v ?? "";
      tr.appendChild(td);
    });
    const tdAcc = document.createElement("td");
    const bEd = document.createElement("button");
    bEd.textContent = "Editar";
    bEd.onclick = () => editar(u);
    const bEl = document.createElement("button");
    bEl.textContent = "Eliminar";
    bEl.className = "peligro";
    bEl.onclick = () => eliminar(u);
    tdAcc.append(bEd, bEl);
    tr.appendChild(tdAcc);
    tbody.appendChild(tr);
  });
}

function editar(u) {
  campos.forEach((c) => ($(c).value = u[c] ?? ""));
  $("titulo").textContent = "Editar usuario #" + u.idUsuario;
  $("btnGuardar").textContent = "Actualizar";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function eliminar(u) {
  if (!confirm("¿Eliminar al usuario '" + u.usuario + "'?")) return;
  const res = await api("eliminar", { idUsuario: u.idUsuario });
  mostrar(res.msg, res.ok);
  if (res.ok) { limpiar(); buscar(); }
}

$("formUsuario").addEventListener("submit", async (e) => {
  e.preventDefault();
  const datos = {};
  campos.forEach((c) => (datos[c] = $(c).value.trim()));
  const res = await api("guardar", datos);
  mostrar(res.msg, res.ok);
  if (res.ok) { limpiar(); buscar(); }
});

$("btnLimpiar").onclick = limpiar;
$("btnBuscar").onclick = buscar;
$("termino").addEventListener("keydown", (e) => { if (e.key === "Enter") buscar(); });
$("btnSalir").onclick = async () => {
  await fetch("/api/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  window.location.href = "/";
};

buscar();