const form = document.getElementById("formLogin");
const mensaje = document.getElementById("mensaje");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const datos = {
    usuario: document.getElementById("usuario").value.trim(),
    clave: document.getElementById("clave").value.trim(),
  };
  try {
    const r = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    });
    const res = await r.json();
    if (res.ok) {
      window.location.href = "/usuarios";
    } else {
      mensaje.textContent = res.msg;
      mensaje.className = "msg error";
    }
  } catch (err) {
    mensaje.textContent = "No se pudo conectar con el servidor.";
    mensaje.className = "msg error";
  }
});