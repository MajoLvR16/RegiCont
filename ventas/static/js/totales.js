(function () {
  'use strict';
  var cont = document.getElementById('totales');
  if (!cont) { return; }
  var url = cont.getAttribute('data-url-datos');
  var espera = (parseInt(cont.getAttribute('data-refresco'), 10) || 7) * 1000;
  var cuerpo = document.querySelector('#tabla-totales tbody');
  var pie = document.querySelector('#tabla-totales tfoot');
  var ultima = (document.getElementById('actualizado').textContent.match(/\d{2}:\d{2}:\d{2}/) || [''])[0];

  function celda(fila, texto, clase, fuerte) {
    var td = document.createElement('td');
    if (clase) { td.className = clase; }
    if (fuerte) {
      var s = document.createElement('strong');
      s.textContent = texto;
      td.appendChild(s);
    } else {
      td.textContent = texto;
    }
    fila.appendChild(td);
  }

  function pintar(d) {
    var i, f, tr, td;
    while (cuerpo.firstChild) { cuerpo.removeChild(cuerpo.firstChild); }
    if (!d.filas.length) {
      tr = document.createElement('tr');
      td = document.createElement('td');
      td.colSpan = 3;
      td.className = 'texto-gris';
      td.textContent = 'Sin datos para ordenar';
      tr.appendChild(td);
      cuerpo.appendChild(tr);
    }
    for (i = 0; i < d.filas.length; i++) {
      f = d.filas[i];
      tr = document.createElement('tr');
      celda(tr, f.puesto);
      celda(tr, f.numero, '', true);
      celda(tr, f.monto, 'num');
      cuerpo.appendChild(tr);
    }
    document.getElementById('total-recaudado').textContent = d.total;
    document.getElementById('pie-total').textContent = d.total;
    document.getElementById('pie-etiqueta').textContent =
      'Total de la jornada · ' + d.cantidad + (d.cantidad === 1 ? ' número' : ' números');
    pie.hidden = !d.cantidad;
    ultima = d.actualizado;
    document.getElementById('actualizado').textContent = 'Actualizado ' + ultima;
  }

  function siguiente() { setTimeout(consultar, espera); }

  function consultar() {
    if (document.hidden) { siguiente(); return; }
    fetch(url, { credentials: 'same-origin' }).then(function (r) {
      if (r.redirected) { window.location.reload(); return null; }
      if (!r.ok) { throw new Error('estado ' + r.status); }
      return r.json();
    }).then(function (d) {
      if (d) { pintar(d); }
      siguiente();
    }).catch(function () {
      document.getElementById('actualizado').textContent =
        'Sin conexión; última actualización ' + ultima;
      siguiente();
    });
  }

  siguiente();
})();
