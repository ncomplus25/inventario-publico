# Inventario Público (Flask + Chart.js)

Este paquete te permite publicar tu app Flask para que otros usuarios puedan visualizar y descargar la data por delegación.

## Estructura
- `app_public.py`: Servidor Flask listo para producción.
- `index.html`: (tu archivo actual) — **usa rutas relativas** (`/subir`, `/delegaciones`, etc.).
- `requirements.txt`: Dependencias.
- `Dockerfile`: Para desplegar en contenedores (Cloud Run, Render, Railway, etc.).
- `Procfile`: Alternativa simple para Render/Heroku.

## Cambios clave vs tu app local
- Soporta CORS configurable con `ALLOWED_ORIGINS`.
- Límite de tamaño para archivos (`MAX_FILE_MB`, por defecto 20 MB).
- **Token de admin** para subir/actualizar el Excel (`ADMIN_TOKEN`). Los endpoints públicos solo leen.
- Rutas usan el mismo esquema de tu app. Asegúrate de que `index.html` use rutas **relativas** (p. ej. `fetch('/delegaciones')`) para que funcione con tu dominio.

### Seguridad mínima recomendada
- Define `ADMIN_TOKEN` como un string largo e impredecible.
- Restringe CORS con `ALLOWED_ORIGINS=https://tu-dominio.com`.
- Usa HTTPS en producción.
- Revisa el Excel de entrada (tamaño, columnas esperadas).

---

## Despliegue en Google Cloud Run (recomendado y barato)
1. Instala y autentica gcloud.
2. En la carpeta del proyecto, ejecuta:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/inventario-publico
   ```
3. Despliega:
   ```bash
   gcloud run deploy inventario-publico      --image gcr.io/PROJECT_ID/inventario-publico      --platform managed      --region us-central1      --allow-unauthenticated      --set-env-vars "ALLOWED_ORIGINS=https://TU-DOMINIO.com,ADMIN_TOKEN=pon_aqui_tu_token,MAX_FILE_MB=20"
   ```
4. Visita la URL que te da Cloud Run.

### Cargar el Excel (solo admin)
Envía el archivo con un `Bearer` token:
```bash
curl -X POST "$URL/subir"   -H "Authorization: Bearer TU_TOKEN"   -F "archivo=@inventario.xlsx"
```

---

## Despliegue en Render (usando Docker)
1. Crea un nuevo servicio web en Render, selecciona tu repo y el Dockerfile.
2. Variables de entorno:
   - `ALLOWED_ORIGINS` (p. ej. `https://tu-dominio.com`)
   - `ADMIN_TOKEN`
   - `PORT` = `8080` (Render usa esta variable)
3. Build Command: *(Render detecta el Dockerfile)*
4. Start Command: *(no necesario; lo toma del Dockerfile)*

---

## Notas para index.html
- Reemplaza `http://127.0.0.1:5000/...` por rutas relativas: `/subir`, `/delegaciones`, `/estado?delegacion=...`, etc.
- Para descargar: `window.location.href = '/descargar?delegacion=' + delegacion;`

## Datos por defecto
- Si pones un archivo en `data/inventario.xlsx` dentro de la imagen o volumen, el servidor lo cargará al iniciar.
- También puedes definir `DEFAULT_DATA_PATH=/ruta/a/tu.xlsx`.

---

## Multi-usuario
- La app expone datos en lectura para todos. Solo quien tenga el `ADMIN_TOKEN` puede actualizar el dataset común.
- Si necesitas datasets separados por usuario, conviene usar autenticación real y un almacenamiento (S3/GCS) por usuario.