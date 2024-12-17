# Sernatur Scraper

Este script permite extraer información de guías turísticos desde el sitio web de Sernatur (Servicio Nacional de Turismo de Chile).

## Descripción

El scraper extrae la siguiente información de cada guía:
- Información personal:
  - Nombre
  - Email
  - Teléfono
- Ubicación:
  - Comuna
  - Localidad
  - Región
- Registro:
  - Tipo (General/Especializado)
  - Estado
  - Especialidades (en formato JSON)

## Estructura del Proyecto

```
.
├── data/
│   └── csv/          # Archivos CSV con los resultados
├── logs/             # Logs de ejecución
├── requirements.txt  # Dependencias del proyecto
├── README.md        # Este archivo
└── sernatur_scraper.py  # Script principal
```

## Requisitos

- Python 3.6+
- Dependencias listadas en `requirements.txt`:
  - requests
  - beautifulsoup4

## Instalación

1. Clonar el repositorio o descargar los archivos
2. Crear un entorno virtual (opcional pero recomendado):
   ```bash
   python -m venv env
   source env/bin/activate  # En Unix/macOS
   # o
   .\env\Scripts\activate  # En Windows
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

Para ejecutar el scraper con la configuración por defecto:
```bash
python sernatur_scraper.py
```

### Configuración

Los principales parámetros que se pueden ajustar en `main()`:

- `tipo_servicio`: ID del tipo de servicio (16 = Guías de turismo)
- `region`: ID de la región (13 = Región Metropolitana)
- `sleep_time`: Tiempo de espera entre requests (default: 1.0 segundos)
- `max_results`: Número máximo de resultados a obtener

### Resultados

Los resultados se guardan en dos formatos:
1. CSV en `data/csv/` con timestamp
2. Logs detallados en `logs/`

El archivo CSV contiene las siguientes columnas:
- name
- email
- phone
- comuna
- localidad
- region
- registration_type
- specialties (en formato JSON)
- status
- detail_url

## Consideraciones

- El script incluye delays entre requests para no sobrecargar el servidor
- Los números de teléfono se formatean automáticamente
- Las especialidades se guardan como array JSON para mejor procesamiento
- Se mantienen logs detallados de la ejecución

## Mantenimiento

Para modificar el comportamiento del scraper:

1. Ajustar parámetros en `main()` para diferentes cantidades de resultados
2. Modificar `sleep_time` según necesidades (mantener > 1 segundo recomendado)
3. Cambiar nivel de logging en `logging.basicConfig()` si se necesita más detalle

## Contribuciones

Si encuentras algún problema o tienes sugerencias de mejora, por favor:
1. Revisa los problemas existentes
2. Crea un nuevo issue describiendo el problema/mejora
3. Envía un pull request si tienes una solución

