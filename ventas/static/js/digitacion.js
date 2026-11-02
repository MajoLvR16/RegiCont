(function () {
  'use strict';
  var form = document.getElementById('form-jugada');
  if (!form) { return; }
  var K = 'regicont.' + form.getAttribute('data-usuario');
  var campos = ['promotor', 'loteria', 'numero', 'valor'];
  var el = {};
  campos.forEach(function (c) { el[c] = document.getElementById(c); });
  var aviso = document.getElementById('aviso-envio');
  var estado = document.getElementById('estado');
  var enviando = false;
  var temporizador = null;

  function leer(k) {
    try { var t = localStorage.getItem(K + k); return t ? JSON.parse(t) : null; } catch (e) { return null; }
  }
  function escribir(k, v) {
    try { localStorage.setItem(K + k, JSON.stringify(v)); } catch (e) { /* sin almacenamiento */ }
  }
  function borrar(k) {
    try { localStorage.removeItem(K + k); } catch (e) { /* sin almacenamiento */ }
  }

  var codigos = [];
  var opciones = document.querySelectorAll('#lista-promotores option');
  for (var i = 0; i < opciones.length; i++) { codigos.push(opciones[i].value); }

  function soloDigitos(t) { return String(t).replace(/[^0-9]/g, ''); }

  function marcar(c, msg) {
    var caja = el[c].parentNode;
    if (msg) { caja.classList.add('campo--error'); } else { caja.classList.remove('campo--error'); }
    document.getElementById('error-' + c).textContent = msg || '';
  }

  function error(c) {
    var v = el[c].value.trim();
    if (c === 'promotor') { return codigos.indexOf(v) < 0 ? 'Código de promotor no existe' : ''; }
    if (c === 'loteria') { return v === '' ? 'Seleccione una lotería activa' : ''; }
    if (c === 'numero') { return /^[0-9]{3,4}$/.test(v) ? '' : 'El número debe tener 3 o 4 cifras'; }
    var d = soloDigitos(v);
    if (d === '') { return 'Digite un valor válido'; }
    return parseInt(d, 10) < 500 ? 'El valor mínimo es $500' : '';
  }

  function validar(c) { var m = error(c); marcar(c, m); return !m; }

  function validarTodo() {
    var primero = null;
    campos.forEach(function (c) { if (!validar(c) && !primero) { primero = c; } });
    if (primero) { el[primero].focus(); }
    return !primero;
  }

  function mostrarAviso(texto, conBoton) {
    document.getElementById('aviso-texto').textContent = texto;
    document.getElementById('reintentar').style.display = conBoton ? '' : 'none';
    aviso.hidden = false;
  }

  function uuid() {
    var b = new Uint8Array(16), j;
    if (window.crypto && window.crypto.getRandomValues) {
      window.crypto.getRandomValues(b);
    } else {
      for (j = 0; j < 16; j++) { b[j] = Math.floor(Math.random() * 256); }
    }
    b[6] = (b[6] & 15) | 64;
    b[8] = (b[8] & 63) | 128;
    var h = [];
    for (j = 0; j < 16; j++) { h.push((b[j] + 256).toString(16).slice(1)); }
    return h.slice(0, 4).join('') + '-' + h.slice(4, 6).join('') + '-' + h.slice(6, 8).join('') +
      '-' + h.slice(8, 10).join('') + '-' + h.slice(10).join('');
  }

  function refrescarTabla() {
    return fetch(form.getAttribute('data-url-hoy'), { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var tb = document.querySelector('#tabla-jugadas tbody');
        while (tb.firstChild) { tb.removeChild(tb.firstChild); }
        d.jugadas.forEach(function (j) {
          var tr = document.createElement('tr');
          [j.hora, j.numero, j.loteria, j.valor, j.promotor].forEach(function (t, n) {
            var td = document.createElement('td');
            if (n === 1) { var s = document.createElement('strong'); s.textContent = t; td.appendChild(s); }
            else { td.textContent = t; }
            if (n === 3) { td.className = 'num'; }
            tr.appendChild(td);
          });
          tb.appendChild(tr);
        });
        if (!d.jugadas.length) {
          var f = document.createElement('tr'), c = document.createElement('td');
          c.colSpan = 5; c.textContent = 'Aún no hay jugadas hoy';
          f.appendChild(c); tb.appendChild(f);
        }
      })
      .catch(function () { /* la tabla se actualizará en la próxima jugada */ });
  }

  function exito() {
    borrar('.pendiente'); borrar('.borrador');
    el.numero.value = ''; el.valor.value = '';
    aviso.hidden = true;
    estado.hidden = false;
    clearTimeout(temporizador);
    temporizador = setTimeout(function () { estado.hidden = true; }, 3000);
    el.numero.focus();
    refrescarTabla();
  }

  var MSG_RED = 'No se pudo guardar la jugada. Revise la conexión y reintente; los datos siguen en pantalla.';

  function guardar() {
    if (enviando) { return; }
    if (!validarTodo()) { return; }
    var datos = {
      promotor: el.promotor.value.trim(), loteria: el.loteria.value,
      numero: el.numero.value.trim(), valor: soloDigitos(el.valor.value)
    };
    var p = leer('.pendiente');
    var igual = p && p.payload && p.payload.promotor === datos.promotor && p.payload.loteria === datos.loteria &&
      p.payload.numero === datos.numero && p.payload.valor === datos.valor;
    datos.token_envio = igual ? p.payload.token_envio : uuid();
    escribir('.pendiente', { payload: datos });
    enviando = true;
    fetch(form.getAttribute('data-url-registrar'), {
      method: 'POST', credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json', 'Accept': 'application/json',
        'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value
      },
      body: JSON.stringify(datos)
    }).then(function (r) {
      var tipo = r.headers.get('content-type') || '';
      if (r.redirected || r.status === 403) {
        mostrarAviso('Su sesión terminó. Vuelva a ingresar; la jugada quedó guardada en este equipo.', false);
        return;
      }
      if (tipo.indexOf('json') < 0) {
        mostrarAviso(MSG_RED, true);
        return;
      }
      return r.json().then(function (d) {
        if (r.status === 201) { exito(); return; }
        if (r.status === 400) {
          borrar('.pendiente');
          var primero = null, otros = [];
          for (var k in (d.errores || {})) {
            if (el[k]) { marcar(k, d.errores[k]); if (!primero) { primero = k; } } else { otros.push(d.errores[k]); }
          }
          if (otros.length) { mostrarAviso(otros.join(' '), false); }
          if (primero) { el[primero].focus(); }
          return;
        }
        mostrarAviso(MSG_RED, true);
      });
    }).catch(function () {
      mostrarAviso(MSG_RED, true);
    }).then(function () { enviando = false; });
  }

  // Enter avanza de campo; el último guarda.
  function enter(c, siguiente) {
    el[c].addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.keyCode !== 13) { return; }
      e.preventDefault();
      if (c === 'valor') { guardar(); return; }
      if (validar(c)) { el[siguiente].focus(); }
    });
  }
  enter('promotor', 'loteria'); enter('loteria', 'numero'); enter('numero', 'valor'); enter('valor');

  campos.forEach(function (c) {
    el[c].addEventListener('input', function () { marcar(c, ''); });
  });
  function guardarSeleccion() { escribir('.seleccion', { promotor: el.promotor.value, loteria: el.loteria.value }); }
  function guardarBorrador() { escribir('.borrador', { numero: el.numero.value, valor: el.valor.value }); }
  ['input', 'change'].forEach(function (ev) {
    el.promotor.addEventListener(ev, guardarSeleccion);
    el.loteria.addEventListener(ev, guardarSeleccion);
  });
  el.numero.addEventListener('input', guardarBorrador);
  el.valor.addEventListener('input', guardarBorrador);

  var rapidos = document.querySelectorAll('.valor-rapido');
  for (var r = 0; r < rapidos.length; r++) {
    rapidos[r].addEventListener('click', function () {
      el.valor.value = this.getAttribute('data-valor');
      marcar('valor', '');
      guardarBorrador();
      el.valor.focus();
    });
  }

  form.addEventListener('submit', function (e) { e.preventDefault(); guardar(); });
  document.getElementById('reintentar').addEventListener('click', guardar);

  // Restaurar al cargar
  var sel = leer('.seleccion'), bor = leer('.borrador'), pen = leer('.pendiente');
  if (sel) {
    if (sel.promotor) { el.promotor.value = sel.promotor; }
    if (sel.loteria && el.loteria.querySelector('option[value="' + sel.loteria + '"]')) { el.loteria.value = sel.loteria; }
  }
  if (bor) { el.numero.value = bor.numero || ''; el.valor.value = bor.valor || ''; }
  if (pen && pen.payload) {
    el.promotor.value = pen.payload.promotor; el.numero.value = pen.payload.numero; el.valor.value = pen.payload.valor;
    if (el.loteria.querySelector('option[value="' + pen.payload.loteria + '"]')) { el.loteria.value = pen.payload.loteria; }
    mostrarAviso('Hay una jugada sin confirmar por el servidor. Revísela y pulse Reintentar.', true);
  }
  (el.promotor.value ? el.numero : el.promotor).focus();
})();
